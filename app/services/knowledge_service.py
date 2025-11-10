"""
知识服务层

提供知识图谱相关的业务逻辑和API接口
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.dao.knowledge_dao import KnowledgeDAO
from app.dao.memory_dao import MemoryDAO
from app.core.knowledge.knowledge_graph_manager import KnowledgeGraphManager
from app.core.knowledge.memory_upgrader import MemoryUpgrader
from app.core.knowledge.graph_reasoner import GraphReasoner
from app.core.knowledge.entity_extractor import EntityExtractor
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeService:
    """
    知识服务层
    
    提供知识图谱相关的业务逻辑:
    - 知识图谱构建和管理
    - 记忆升级为知识
    - 知识查询和推理
    - 与Agent系统的集成
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        knowledge_dao: KnowledgeDAO,
        memory_dao: MemoryDAO
    ):
        """
        初始化知识服务
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            knowledge_dao: 知识数据访问对象
            memory_dao: 记忆数据访问对象
        """
        self.db = db
        self.llm = llm
        self.knowledge_dao = knowledge_dao
        self.memory_dao = memory_dao
        
        # 初始化核心组件
        self.kg_manager = KnowledgeGraphManager(db, llm, knowledge_dao)
        self.memory_upgrader = MemoryUpgrader(
            db, llm, memory_dao, knowledge_dao, self.kg_manager
        )
        self.graph_reasoner = GraphReasoner()
        self.entity_extractor = EntityExtractor(llm)
        
        logger.info("知识服务初始化完成")
    
    async def build_user_knowledge_graph(
        self,
        user_id: int,
        conversation_id: Optional[int] = None,
        importance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        构建用户知识图谱
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID（可选，如果指定则只处理该会话的记忆）
            importance_threshold: 重要性阈值
            
        Returns:
            Dict[str, Any]: 构建结果
        """
        try:
            # 获取记忆
            if conversation_id:
                memories = self.memory_dao.get_by_conversation(conversation_id)
            else:
                memories = self.memory_dao.get_by_user(user_id)
            
            if not memories:
                return {
                    "success": False,
                    "message": "没有找到记忆数据",
                    "entities_created": 0,
                    "relations_created": 0
                }
            
            # 升级记忆为知识
            upgrade_result = await self.memory_upgrader.upgrade_memories_to_knowledge(
                memories=memories,
                user_id=user_id,
                importance_threshold=importance_threshold
            )
            
            # 获取知识图谱统计
            kg_stats = await self.kg_manager.get_entity_statistics(user_id)
            
            result = {
                "success": True,
                "message": "知识图谱构建完成",
                "upgrade_result": upgrade_result,
                "knowledge_graph_stats": kg_stats,
                "processed_memories": len(memories)
            }
            
            logger.info(f"用户 {user_id} 知识图谱构建完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"构建用户知识图谱失败: {e}")
            return {
                "success": False,
                "message": f"构建失败: {str(e)}",
                "error": str(e)
            }
    
    async def get_relevant_knowledge(
        self,
        user_id: int,
        query: str,
        max_entities: int = 5,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        获取相关知识
        
        Args:
            user_id: 用户ID
            query: 查询内容
            max_entities: 最大实体数量
            depth: 搜索深度
            
        Returns:
            Dict[str, Any]: 相关知识
        """
        try:
            # 从查询中提取关键实体
            entities = await self.entity_extractor.extract_entities(
                text=query,
                max_entities=max_entities
            )
            
            if not entities:
                return {
                    "success": False,
                    "message": "无法从查询中提取实体",
                    "knowledge": {}
                }
            
            # 查询每个实体的知识子图
            knowledge = {}
            for entity in entities:
                entity_name = entity["name"]
                
                # 查询实体子图
                subgraph_result = await self.kg_manager.query_graph(
                    user_id=user_id,
                    entity_name=entity_name,
                    depth=depth
                )
                
                if subgraph_result.get("nodes"):
                    knowledge[entity_name] = {
                        "entity_info": entity,
                        "subgraph": subgraph_result,
                        "related_entities": await self.kg_manager.find_related_entities(
                            user_id=user_id,
                            entity_name=entity_name,
                            max_results=10
                        )
                    }
            
            return {
                "success": True,
                "message": "成功获取相关知识",
                "knowledge": knowledge,
                "extracted_entities": entities
            }
            
        except Exception as e:
            logger.error(f"获取相关知识失败: {e}")
            return {
                "success": False,
                "message": f"获取失败: {str(e)}",
                "error": str(e)
            }
    
    async def search_knowledge(
        self,
        user_id: int,
        query: str,
        search_type: str = "entity",
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        搜索知识
        
        Args:
            user_id: 用户ID
            query: 搜索查询
            search_type: 搜索类型 ("entity", "relation", "all")
            max_results: 最大结果数
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            results = {
                "entities": [],
                "relations": [],
                "paths": []
            }
            
            if search_type in ["entity", "all"]:
                # 搜索实体
                entities = await self.kg_manager.search_entities(
                    user_id=user_id,
                    query=query,
                    max_results=max_results
                )
                results["entities"] = entities
            
            if search_type in ["relation", "all"]:
                # 搜索关系（通过实体搜索间接实现）
                entities = await self.kg_manager.search_entities(
                    user_id=user_id,
                    query=query,
                    max_results=max_results
                )
                
                # 获取这些实体的关系
                for entity in entities:
                    entity_name = entity["entity_name"]
                    related = await self.kg_manager.find_related_entities(
                        user_id=user_id,
                        entity_name=entity_name,
                        max_results=5
                    )
                    results["relations"].extend(related)
            
            if search_type == "all" and len(results["entities"]) >= 2:
                # 查找实体间的路径
                entity_names = [e["entity_name"] for e in results["entities"][:3]]
                for i in range(len(entity_names)):
                    for j in range(i + 1, len(entity_names)):
                        paths = self.graph_reasoner.find_path(
                            self.kg_manager.graph,
                            entity_names[i],
                            entity_names[j],
                            max_length=3
                        )
                        if paths:
                            results["paths"].append({
                                "from": entity_names[i],
                                "to": entity_names[j],
                                "paths": paths
                            })
            
            return {
                "success": True,
                "message": "搜索完成",
                "results": results,
                "query": query,
                "search_type": search_type
            }
            
        except Exception as e:
            logger.error(f"搜索知识失败: {e}")
            return {
                "success": False,
                "message": f"搜索失败: {str(e)}",
                "error": str(e)
            }
    
    async def get_knowledge_insights(
        self,
        user_id: int,
        insight_type: str = "overview"
    ) -> Dict[str, Any]:
        """
        获取知识洞察
        
        Args:
            user_id: 用户ID
            insight_type: 洞察类型 ("overview", "patterns", "recommendations")
            
        Returns:
            Dict[str, Any]: 洞察结果
        """
        try:
            insights = {}
            
            if insight_type in ["overview", "patterns"]:
                # 获取图谱统计
                kg_stats = await self.kg_manager.get_entity_statistics(user_id)
                insights["statistics"] = kg_stats
                
                # 获取图谱结构分析
                structure_analysis = self.graph_reasoner.analyze_graph_structure(
                    self.kg_manager.graph
                )
                insights["structure"] = structure_analysis
            
            if insight_type in ["patterns", "recommendations"]:
                # 发现社区
                communities = self.graph_reasoner.find_communities(
                    self.kg_manager.graph,
                    min_size=3
                )
                insights["communities"] = communities
                
                # 查找中心实体
                central_entities = self.graph_reasoner.find_central_entities(
                    self.kg_manager.graph,
                    top_k=5
                )
                insights["central_entities"] = central_entities
            
            if insight_type == "recommendations":
                # 获取升级候选
                upgrade_candidates = await self.memory_upgrader.get_upgrade_candidates(
                    user_id=user_id,
                    limit=10
                )
                insights["upgrade_candidates"] = upgrade_candidates
                
                # 获取升级统计
                upgrade_stats = await self.memory_upgrader.get_upgrade_statistics(user_id)
                insights["upgrade_statistics"] = upgrade_stats
            
            return {
                "success": True,
                "message": "洞察生成完成",
                "insights": insights,
                "insight_type": insight_type
            }
            
        except Exception as e:
            logger.error(f"获取知识洞察失败: {e}")
            return {
                "success": False,
                "message": f"洞察生成失败: {str(e)}",
                "error": str(e)
            }
    
    async def upgrade_memories(
        self,
        user_id: int,
        memory_ids: Optional[List[int]] = None,
        conversation_id: Optional[int] = None,
        importance_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        升级记忆为知识
        
        Args:
            user_id: 用户ID
            memory_ids: 指定记忆ID列表（可选）
            conversation_id: 会话ID（可选）
            importance_threshold: 重要性阈值
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            if memory_ids:
                # 批量升级指定记忆
                result = await self.memory_upgrader.batch_upgrade_memories(
                    memory_ids=memory_ids,
                    user_id=user_id,
                    force_upgrade=False
                )
            elif conversation_id:
                # 升级会话记忆
                result = await self.memory_upgrader.upgrade_conversation_memories(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    importance_threshold=importance_threshold
                )
            else:
                # 升级用户所有记忆
                result = await self.memory_upgrader.upgrade_user_memories(
                    user_id=user_id,
                    importance_threshold=importance_threshold
                )
            
            return {
                "success": True,
                "message": "记忆升级完成",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"升级记忆失败: {e}")
            return {
                "success": False,
                "message": f"升级失败: {str(e)}",
                "error": str(e)
            }
    
    async def get_knowledge_graph_visualization(
        self,
        user_id: int,
        center_entity: Optional[str] = None,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        获取知识图谱可视化数据
        
        Args:
            user_id: 用户ID
            center_entity: 中心实体（可选）
            depth: 深度
            max_nodes: 最大节点数
            
        Returns:
            Dict[str, Any]: 可视化数据
        """
        try:
            # 获取图数据
            graph_data = await self.kg_manager.get_graph_visualization_data(
                user_id=user_id,
                center_entity=center_entity,
                depth=depth
            )
            
            # 如果节点数过多，进行采样
            if len(graph_data.get("nodes", [])) > max_nodes:
                graph_data = self._sample_graph_data(graph_data, max_nodes)
            
            # 添加布局信息
            layout_data = self._calculate_layout(graph_data)
            
            return {
                "success": True,
                "message": "可视化数据生成完成",
                "graph_data": graph_data,
                "layout": layout_data,
                "center_entity": center_entity,
                "depth": depth
            }
            
        except Exception as e:
            logger.error(f"获取可视化数据失败: {e}")
            return {
                "success": False,
                "message": f"可视化数据生成失败: {str(e)}",
                "error": str(e)
            }
    
    def _sample_graph_data(self, graph_data: Dict[str, Any], max_nodes: int) -> Dict[str, Any]:
        """
        对图数据进行采样，减少节点数量
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if len(nodes) <= max_nodes:
            return graph_data
        
        # 选择中心度最高的节点
        node_names = [node["name"] for node in nodes]
        node_degrees = {}
        
        for edge in edges:
            from_node = edge["from"]
            to_node = edge["to"]
            node_degrees[from_node] = node_degrees.get(from_node, 0) + 1
            node_degrees[to_node] = node_degrees.get(to_node, 0) + 1
        
        # 按度排序
        sorted_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)
        selected_nodes = set([node[0] for node in sorted_nodes[:max_nodes]])
        
        # 过滤节点和边
        filtered_nodes = [node for node in nodes if node["name"] in selected_nodes]
        filtered_edges = [
            edge for edge in edges
            if edge["from"] in selected_nodes and edge["to"] in selected_nodes
        ]
        
        return {
            "nodes": filtered_nodes,
            "edges": filtered_edges,
            "node_count": len(filtered_nodes),
            "edge_count": len(filtered_edges)
        }
    
    def _calculate_layout(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算图布局
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        # 简单的圆形布局
        import math
        
        layout = {}
        center_x, center_y = 0, 0
        radius = 200
        
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            layout[node["name"]] = {
                "x": x,
                "y": y,
                "type": node.get("type", "unknown")
            }
        
        return layout
    
    async def get_entity_details(
        self,
        user_id: int,
        entity_name: str
    ) -> Dict[str, Any]:
        """
        获取实体详细信息
        
        Args:
            user_id: 用户ID
            entity_name: 实体名称
            
        Returns:
            Dict[str, Any]: 实体详细信息
        """
        try:
            # 查询实体子图
            subgraph = await self.kg_manager.query_graph(
                user_id=user_id,
                entity_name=entity_name,
                depth=2
            )
            
            # 获取相关实体
            related_entities = await self.kg_manager.find_related_entities(
                user_id=user_id,
                entity_name=entity_name,
                max_results=20
            )
            
            # 获取推理建议
            suggestions = self.graph_reasoner.suggest_relations(
                self.kg_manager.graph,
                entity_name,
                based_on="similarity"
            )
            
            return {
                "success": True,
                "message": "实体详情获取完成",
                "entity_name": entity_name,
                "subgraph": subgraph,
                "related_entities": related_entities,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"获取实体详情失败: {e}")
            return {
                "success": False,
                "message": f"获取失败: {str(e)}",
                "error": str(e)
            }
    
    async def cleanup_knowledge_graph(
        self,
        user_id: int,
        cleanup_type: str = "orphaned"
    ) -> Dict[str, Any]:
        """
        清理知识图谱
        
        Args:
            user_id: 用户ID
            cleanup_type: 清理类型 ("orphaned", "low_quality", "duplicates")
            
        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            if cleanup_type == "orphaned":
                # 清理孤立实体
                result = await self.kg_manager.cleanup_orphaned_entities(user_id)
            else:
                result = {
                    "cleaned_entities": 0,
                    "message": f"不支持的清理类型: {cleanup_type}"
                }
            
            return {
                "success": True,
                "message": "知识图谱清理完成",
                "cleanup_result": result,
                "cleanup_type": cleanup_type
            }
            
        except Exception as e:
            logger.error(f"清理知识图谱失败: {e}")
            return {
                "success": False,
                "message": f"清理失败: {str(e)}",
                "error": str(e)
            }
    
    async def get_knowledge_summary(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        获取知识图谱摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 知识摘要
        """
        try:
            # 获取统计信息
            kg_stats = await self.kg_manager.get_entity_statistics(user_id)
            upgrade_stats = await self.memory_upgrader.get_upgrade_statistics(user_id)
            
            # 获取结构分析
            structure_analysis = self.graph_reasoner.analyze_graph_structure(
                self.kg_manager.graph
            )
            
            # 获取中心实体
            central_entities = self.graph_reasoner.find_central_entities(
                self.kg_manager.graph,
                top_k=5
            )
            
            return {
                "success": True,
                "message": "知识摘要生成完成",
                "summary": {
                    "knowledge_graph": kg_stats,
                    "memory_upgrade": upgrade_stats,
                    "structure": structure_analysis,
                    "central_entities": central_entities
                }
            }
            
        except Exception as e:
            logger.error(f"获取知识摘要失败: {e}")
            return {
                "success": False,
                "message": f"摘要生成失败: {str(e)}",
                "error": str(e)
            }
