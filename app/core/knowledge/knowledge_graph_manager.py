"""
知识图谱管理器

负责知识图谱的构建、维护、查询和推理
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime

import networkx as nx
from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.dao.knowledge_dao import KnowledgeDAO
from app.models.knowledge import KnowledgeGraph, KnowledgeRelation
from app.models.memory import MemoryStore
from .entity_extractor import EntityExtractor
from .relation_extractor import RelationExtractor
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraphManager:
    """
    知识图谱管理器
    
    功能:
    - 图谱的构建和维护
    - 实体和关系的CRUD
    - 图谱查询和推理
    - 可视化支持
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        knowledge_dao: KnowledgeDAO
    ):
        """
        初始化知识图谱管理器
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            knowledge_dao: 知识数据访问对象
        """
        self.db = db
        self.llm = llm
        self.knowledge_dao = knowledge_dao
        self.entity_extractor = EntityExtractor(llm)
        self.relation_extractor = RelationExtractor(llm)
        
        # NetworkX图结构
        self.graph = nx.DiGraph()
        
        logger.info("知识图谱管理器初始化完成")
    
    async def build_from_memories(
        self,
        memories: List[MemoryStore],
        user_id: int
    ) -> Dict[str, Any]:
        """
        从记忆构建知识图谱
        
        Args:
            memories: 记忆列表
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 构建结果统计
        """
        try:
            entities_created = 0
            relations_created = 0
            processed_memories = 0
            
            logger.info(f"开始从 {len(memories)} 个记忆构建知识图谱")
            
            for memory in memories:
                try:
                    # 提取实体
                    entities = await self.entity_extractor.extract_entities_from_memory(
                        memory_content=memory.content,
                        memory_type=memory.memory_type,
                        context={"memory_id": memory.id, "conversation_id": memory.conversation_id}
                    )
                    
                    if not entities:
                        continue
                    
                    # 保存实体到数据库
                    saved_entities = []
                    for entity_data in entities:
                        entity = await self._create_or_update_entity(
                            user_id=user_id,
                            entity_type=entity_data["type"],
                            entity_name=entity_data["name"],
                            properties=entity_data.get("properties", {}),
                            memory_id=memory.id
                        )
                        if entity:
                            saved_entities.append(entity)
                            entities_created += 1
                    
                    # 提取关系
                    if len(saved_entities) >= 2:
                        relations = await self.relation_extractor.extract_relations_from_memory(
                            memory_content=memory.content,
                            entities=entities,
                            memory_type=memory.memory_type,
                            context={"memory_id": memory.id, "conversation_id": memory.conversation_id}
                        )
                        
                        # 保存关系到数据库
                        for relation_data in relations:
                            relation = await self._create_relation(
                                user_id=user_id,
                                from_entity_name=relation_data["from_entity"],
                                to_entity_name=relation_data["to_entity"],
                                relation_type=relation_data["relation_type"],
                                strength=relation_data["strength"],
                                properties=relation_data.get("properties", {}),
                                memory_id=memory.id
                            )
                            if relation:
                                relations_created += 1
                    
                    processed_memories += 1
                    
                except Exception as e:
                    logger.error(f"处理记忆 {memory.id} 时出错: {e}")
                    continue
            
            # 更新图结构
            await self._update_graph_structure(user_id)
            
            result = {
                "entities_created": entities_created,
                "relations_created": relations_created,
                "processed_memories": processed_memories,
                "total_memories": len(memories)
            }
            
            logger.info(f"知识图谱构建完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            return {
                "entities_created": 0,
                "relations_created": 0,
                "processed_memories": 0,
                "total_memories": len(memories),
                "error": str(e)
            }
    
    async def _create_or_update_entity(
        self,
        user_id: int,
        entity_type: str,
        entity_name: str,
        properties: Dict[str, Any],
        memory_id: int
    ) -> Optional[KnowledgeGraph]:
        """
        创建或更新实体
        """
        try:
            # 检查实体是否已存在
            existing_entity = self.knowledge_dao.get_entity_by_name(
                user_id=user_id,
                entity_name=entity_name
            )
            
            if existing_entity:
                # 更新现有实体
                existing_entity.entity_type = entity_type
                existing_entity.properties = {
                    **existing_entity.properties,
                    **properties
                }
                existing_entity.updated_at = datetime.now()
                
                self.knowledge_dao.update(existing_entity)
                logger.debug(f"更新实体: {entity_name}")
                return existing_entity
            else:
                # 创建新实体
                new_entity = KnowledgeGraph(
                    user_id=user_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    properties=properties,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                saved_entity = self.knowledge_dao.create(new_entity)
                logger.debug(f"创建新实体: {entity_name}")
                return saved_entity
                
        except Exception as e:
            logger.error(f"创建/更新实体失败 {entity_name}: {e}")
            return None
    
    async def _create_relation(
        self,
        user_id: int,
        from_entity_name: str,
        to_entity_name: str,
        relation_type: str,
        strength: float,
        properties: Dict[str, Any],
        memory_id: int
    ) -> Optional[KnowledgeRelation]:
        """
        创建关系
        """
        try:
            # 获取实体ID
            from_entity = self.knowledge_dao.get_entity_by_name(user_id, from_entity_name)
            to_entity = self.knowledge_dao.get_entity_by_name(user_id, to_entity_name)
            
            if not from_entity or not to_entity:
                logger.warning(f"无法找到实体: {from_entity_name} -> {to_entity_name}")
                return None
            
            # 检查关系是否已存在
            existing_relation = self.knowledge_dao.get_relation_by_entities(
                user_id=user_id,
                from_entity_id=from_entity.id,
                to_entity_id=to_entity.id,
                relation_type=relation_type
            )
            
            if existing_relation:
                # 更新现有关系强度
                existing_relation.strength = max(existing_relation.strength, strength)
                existing_relation.properties = {
                    **existing_relation.properties,
                    **properties
                }
                existing_relation.updated_at = datetime.now()
                
                self.knowledge_dao.update(existing_relation)
                logger.debug(f"更新关系: {from_entity_name} -> {to_entity_name}")
                return existing_relation
            else:
                # 创建新关系
                new_relation = KnowledgeRelation(
                    user_id=user_id,
                    from_entity_id=from_entity.id,
                    to_entity_id=to_entity.id,
                    relation_type=relation_type,
                    strength=strength,
                    properties=properties,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                saved_relation = self.knowledge_dao.create(new_relation)
                logger.debug(f"创建新关系: {from_entity_name} -> {to_entity_name}")
                return saved_relation
                
        except Exception as e:
            logger.error(f"创建关系失败 {from_entity_name} -> {to_entity_name}: {e}")
            return None
    
    async def _update_graph_structure(self, user_id: int):
        """
        更新图结构
        """
        try:
            # 清空现有图
            self.graph.clear()
            
            # 获取用户的所有实体和关系
            entities = self.knowledge_dao.get_entities_by_user(user_id)
            relations = self.knowledge_dao.get_relations_by_user(user_id)
            
            # 添加节点
            for entity in entities:
                self.graph.add_node(
                    entity.entity_name,
                    entity_type=entity.entity_type,
                    properties=entity.properties,
                    entity_id=entity.id
                )
            
            # 添加边
            for relation in relations:
                from_entity = self.knowledge_dao.get_entity_by_id(relation.from_entity_id)
                to_entity = self.knowledge_dao.get_entity_by_id(relation.to_entity_id)
                
                if from_entity and to_entity:
                    self.graph.add_edge(
                        from_entity.entity_name,
                        to_entity.entity_name,
                        relation_type=relation.relation_type,
                        strength=relation.strength,
                        properties=relation.properties,
                        relation_id=relation.id
                    )
            
            logger.info(f"图结构更新完成: {self.graph.number_of_nodes()} 个节点, {self.graph.number_of_edges()} 条边")
            
        except Exception as e:
            logger.error(f"更新图结构失败: {e}")
    
    async def query_graph(
        self,
        user_id: int,
        entity_name: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        查询知识图谱
        
        Args:
            user_id: 用户ID
            entity_name: 中心实体名称
            depth: 查询深度
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            # 确保图结构是最新的
            await self._update_graph_structure(user_id)
            
            if entity_name not in self.graph:
                return {
                    "center_entity": entity_name,
                    "nodes": [],
                    "edges": [],
                    "depth": depth,
                    "error": f"实体 {entity_name} 不存在"
                }
            
            # 获取子图
            subgraph = self._get_subgraph(entity_name, depth)
            
            # 构建结果
            nodes = []
            for node in subgraph.nodes(data=True):
                nodes.append({
                    "name": node[0],
                    "type": node[1].get("entity_type", "unknown"),
                    "properties": node[1].get("properties", {})
                })
            
            edges = []
            for edge in subgraph.edges(data=True):
                edges.append({
                    "from": edge[0],
                    "to": edge[1],
                    "relation_type": edge[2].get("relation_type", "unknown"),
                    "strength": edge[2].get("strength", 0.5),
                    "properties": edge[2].get("properties", {})
                })
            
            return {
                "center_entity": entity_name,
                "nodes": nodes,
                "edges": edges,
                "depth": depth,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
            
        except Exception as e:
            logger.error(f"查询知识图谱失败: {e}")
            return {
                "center_entity": entity_name,
                "nodes": [],
                "edges": [],
                "depth": depth,
                "error": str(e)
            }
    
    def _get_subgraph(self, center_entity: str, depth: int) -> nx.DiGraph:
        """
        获取以指定实体为中心的子图
        """
        if center_entity not in self.graph:
            return nx.DiGraph()
        
        # 使用BFS获取指定深度的子图
        visited = set()
        current_level = {center_entity}
        all_nodes = {center_entity}
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                if node not in visited:
                    visited.add(node)
                    # 添加所有邻居
                    neighbors = list(self.graph.successors(node)) + list(self.graph.predecessors(node))
                    next_level.update(neighbors)
                    all_nodes.update(neighbors)
            current_level = next_level
        
        # 创建子图
        subgraph = self.graph.subgraph(all_nodes).copy()
        return subgraph
    
    async def get_entity_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        获取实体统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            entities = self.knowledge_dao.get_entities_by_user(user_id)
            relations = self.knowledge_dao.get_relations_by_user(user_id)
            
            # 实体类型分布
            type_distribution = {}
            for entity in entities:
                entity_type = entity.entity_type
                type_distribution[entity_type] = type_distribution.get(entity_type, 0) + 1
            
            # 关系类型分布
            relation_type_distribution = {}
            for relation in relations:
                relation_type = relation.relation_type
                relation_type_distribution[relation_type] = relation_type_distribution.get(relation_type, 0) + 1
            
            # 实体连接度
            entity_connectivity = {}
            for relation in relations:
                from_entity = self.knowledge_dao.get_entity_by_id(relation.from_entity_id)
                to_entity = self.knowledge_dao.get_entity_by_id(relation.to_entity_id)
                
                if from_entity:
                    entity_connectivity[from_entity.entity_name] = entity_connectivity.get(from_entity.entity_name, 0) + 1
                if to_entity:
                    entity_connectivity[to_entity.entity_name] = entity_connectivity.get(to_entity.entity_name, 0) + 1
            
            # 找出最连接的实体
            most_connected = sorted(
                entity_connectivity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "entity_type_distribution": type_distribution,
                "relation_type_distribution": relation_type_distribution,
                "most_connected_entities": most_connected,
                "average_connectivity": sum(entity_connectivity.values()) / len(entity_connectivity) if entity_connectivity else 0
            }
            
        except Exception as e:
            logger.error(f"获取实体统计信息失败: {e}")
            return {
                "total_entities": 0,
                "total_relations": 0,
                "entity_type_distribution": {},
                "relation_type_distribution": {},
                "most_connected_entities": [],
                "average_connectivity": 0,
                "error": str(e)
            }
    
    async def find_related_entities(
        self,
        user_id: int,
        entity_name: str,
        relation_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        查找相关实体
        
        Args:
            user_id: 用户ID
            entity_name: 实体名称
            relation_types: 关系类型过滤
            max_results: 最大结果数
            
        Returns:
            List[Dict[str, Any]]: 相关实体列表
        """
        try:
            await self._update_graph_structure(user_id)
            
            if entity_name not in self.graph:
                return []
            
            related_entities = []
            
            # 获取直接相关的实体
            for neighbor in self.graph.neighbors(entity_name):
                edge_data = self.graph.get_edge_data(entity_name, neighbor)
                if edge_data:
                    relation_type = edge_data.get("relation_type", "unknown")
                    strength = edge_data.get("strength", 0.5)
                    
                    # 关系类型过滤
                    if relation_types and relation_type not in relation_types:
                        continue
                    
                    # 获取实体信息
                    neighbor_data = self.graph.nodes[neighbor]
                    
                    related_entities.append({
                        "entity_name": neighbor,
                        "entity_type": neighbor_data.get("entity_type", "unknown"),
                        "relation_type": relation_type,
                        "strength": strength,
                        "properties": neighbor_data.get("properties", {})
                    })
            
            # 按强度排序
            related_entities.sort(key=lambda x: x["strength"], reverse=True)
            
            return related_entities[:max_results]
            
        except Exception as e:
            logger.error(f"查找相关实体失败: {e}")
            return []
    
    async def search_entities(
        self,
        user_id: int,
        query: str,
        entity_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索实体
        
        Args:
            user_id: 用户ID
            query: 搜索查询
            entity_types: 实体类型过滤
            max_results: 最大结果数
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        try:
            entities = self.knowledge_dao.search_entities(
                user_id=user_id,
                query=query,
                entity_types=entity_types,
                limit=max_results
            )
            
            results = []
            for entity in entities:
                results.append({
                    "entity_name": entity.entity_name,
                    "entity_type": entity.entity_type,
                    "properties": entity.properties,
                    "created_at": entity.created_at.isoformat() if entity.created_at else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"搜索实体失败: {e}")
            return []
    
    async def get_graph_visualization_data(
        self,
        user_id: int,
        center_entity: Optional[str] = None,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        获取图可视化数据
        
        Args:
            user_id: 用户ID
            center_entity: 中心实体（可选）
            depth: 深度
            
        Returns:
            Dict[str, Any]: 可视化数据
        """
        try:
            if center_entity:
                # 获取以指定实体为中心的子图
                result = await self.query_graph(user_id, center_entity, depth)
                return result
            else:
                # 获取整个图
                await self._update_graph_structure(user_id)
                
                nodes = []
                for node in self.graph.nodes(data=True):
                    nodes.append({
                        "name": node[0],
                        "type": node[1].get("entity_type", "unknown"),
                        "properties": node[1].get("properties", {})
                    })
                
                edges = []
                for edge in self.graph.edges(data=True):
                    edges.append({
                        "from": edge[0],
                        "to": edge[1],
                        "relation_type": edge[2].get("relation_type", "unknown"),
                        "strength": edge[2].get("strength", 0.5),
                        "properties": edge[2].get("properties", {})
                    })
                
                return {
                    "nodes": nodes,
                    "edges": edges,
                    "node_count": len(nodes),
                    "edge_count": len(edges)
                }
                
        except Exception as e:
            logger.error(f"获取图可视化数据失败: {e}")
            return {
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
                "error": str(e)
            }
    
    async def cleanup_orphaned_entities(self, user_id: int) -> Dict[str, Any]:
        """
        清理孤立实体（没有关系的实体）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            await self._update_graph_structure(user_id)
            
            # 找出孤立节点
            isolated_nodes = list(nx.isolates(self.graph))
            
            if not isolated_nodes:
                return {
                    "cleaned_entities": 0,
                    "message": "没有发现孤立实体"
                }
            
            # 删除孤立实体
            cleaned_count = 0
            for node_name in isolated_nodes:
                entity = self.knowledge_dao.get_entity_by_name(user_id, node_name)
                if entity:
                    self.knowledge_dao.delete(entity)
                    cleaned_count += 1
            
            # 重新更新图结构
            await self._update_graph_structure(user_id)
            
            return {
                "cleaned_entities": cleaned_count,
                "message": f"清理了 {cleaned_count} 个孤立实体"
            }
            
        except Exception as e:
            logger.error(f"清理孤立实体失败: {e}")
            return {
                "cleaned_entities": 0,
                "error": str(e)
            }
