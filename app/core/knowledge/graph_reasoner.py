"""
图谱推理器

基于知识图谱进行推理，包括路径查询、社区发现、关系推断等
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import networkx as nx
from collections import defaultdict, deque

from app.utils.logger import get_logger

logger = get_logger(__name__)


class GraphReasoner:
    """
    图谱推理器
    
    基于图谱进行推理:
    - 路径查询（A到B的路径）
    - 社区发现（相关实体聚类）
    - 关系推断（隐含关系发现）
    - 知识补全（缺失关系预测）
    """
    
    def __init__(self):
        """
        初始化图谱推理器
        """
        self.max_path_length = 5
        self.min_community_size = 2
        self.inference_threshold = 0.6
        
        logger.info("图谱推理器初始化完成")
    
    def find_path(
        self,
        graph: nx.DiGraph,
        start_entity: str,
        end_entity: str,
        max_length: Optional[int] = None,
        relation_types: Optional[List[str]] = None
    ) -> List[List[str]]:
        """
        查找两个实体间的路径
        
        Args:
            graph: 知识图谱
            start_entity: 起始实体
            end_entity: 目标实体
            max_length: 最大路径长度
            relation_types: 关系类型过滤
            
        Returns:
            List[List[str]]: 路径列表
        """
        try:
            if start_entity not in graph or end_entity not in graph:
                logger.warning(f"实体不存在: {start_entity} -> {end_entity}")
                return []
            
            max_len = max_length or self.max_path_length
            
            # 使用NetworkX查找所有简单路径
            try:
                paths = list(nx.all_simple_paths(
                    graph,
                    start_entity,
                    end_entity,
                    cutoff=max_len
                ))
                
                # 关系类型过滤
                if relation_types:
                    filtered_paths = []
                    for path in paths:
                        if self._path_matches_relation_types(graph, path, relation_types):
                            filtered_paths.append(path)
                    paths = filtered_paths
                
                logger.debug(f"找到 {len(paths)} 条路径: {start_entity} -> {end_entity}")
                return paths
                
            except nx.NetworkXNoPath:
                logger.debug(f"没有找到路径: {start_entity} -> {end_entity}")
                return []
                
        except Exception as e:
            logger.error(f"查找路径失败: {e}")
            return []
    
    def _path_matches_relation_types(
        self,
        graph: nx.DiGraph,
        path: List[str],
        relation_types: List[str]
    ) -> bool:
        """
        检查路径是否匹配指定的关系类型
        """
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data:
                relation_type = edge_data.get("relation_type", "")
                if relation_type not in relation_types:
                    return False
        return True
    
    def find_related_entities(
        self,
        graph: nx.DiGraph,
        entity: str,
        depth: int = 2,
        relation_types: Optional[List[str]] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        查找相关实体
        
        Args:
            graph: 知识图谱
            entity: 中心实体
            depth: 搜索深度
            relation_types: 关系类型过滤
            max_results: 最大结果数
            
        Returns:
            List[Dict[str, Any]]: 相关实体列表
        """
        try:
            if entity not in graph:
                logger.warning(f"实体不存在: {entity}")
                return []
            
            related_entities = []
            visited = {entity}
            current_level = {entity}
            
            for level in range(depth):
                next_level = set()
                
                for current_entity in current_level:
                    # 获取邻居
                    neighbors = list(graph.neighbors(current_entity))
                    
                    for neighbor in neighbors:
                        if neighbor not in visited:
                            edge_data = graph.get_edge_data(current_entity, neighbor)
                            if edge_data:
                                relation_type = edge_data.get("relation_type", "unknown")
                                strength = edge_data.get("strength", 0.5)
                                
                                # 关系类型过滤
                                if relation_types and relation_type not in relation_types:
                                    continue
                                
                                # 获取实体信息
                                neighbor_data = graph.nodes[neighbor]
                                
                                related_entities.append({
                                    "entity_name": neighbor,
                                    "entity_type": neighbor_data.get("entity_type", "unknown"),
                                    "relation_type": relation_type,
                                    "strength": strength,
                                    "distance": level + 1,
                                    "properties": neighbor_data.get("properties", {})
                                })
                                
                                next_level.add(neighbor)
                                visited.add(neighbor)
                
                current_level = next_level
            
            # 按强度和距离排序
            related_entities.sort(
                key=lambda x: (x["strength"], -x["distance"]),
                reverse=True
            )
            
            return related_entities[:max_results]
            
        except Exception as e:
            logger.error(f"查找相关实体失败: {e}")
            return []
    
    def find_communities(
        self,
        graph: nx.DiGraph,
        min_size: Optional[int] = None,
        algorithm: str = "greedy"
    ) -> List[List[str]]:
        """
        发现实体社区（聚类）
        
        Args:
            graph: 知识图谱
            min_size: 最小社区大小
            algorithm: 社区发现算法
            
        Returns:
            List[List[str]]: 社区列表
        """
        try:
            min_comm_size = min_size or self.min_community_size
            
            # 转换为无向图进行社区发现
            undirected_graph = graph.to_undirected()
            
            if algorithm == "greedy":
                # 使用贪心模块度最大化
                communities = nx.community.greedy_modularity_communities(undirected_graph)
            elif algorithm == "label_propagation":
                # 使用标签传播
                communities = nx.community.label_propagation_communities(undirected_graph)
            else:
                # 默认使用贪心算法
                communities = nx.community.greedy_modularity_communities(undirected_graph)
            
            # 过滤小社区
            filtered_communities = [
                list(community) for community in communities
                if len(community) >= min_comm_size
            ]
            
            logger.info(f"发现 {len(filtered_communities)} 个社区")
            return filtered_communities
            
        except Exception as e:
            logger.error(f"社区发现失败: {e}")
            return []
    
    def infer_missing_relations(
        self,
        graph: nx.DiGraph,
        entity: str,
        max_inferences: int = 10
    ) -> List[Dict[str, Any]]:
        """
        推断缺失的关系
        
        Args:
            graph: 知识图谱
            entity: 目标实体
            max_inferences: 最大推断数量
            
        Returns:
            List[Dict[str, Any]]: 推断的关系列表
        """
        try:
            if entity not in graph:
                return []
            
            inferences = []
            
            # 获取实体的直接邻居
            neighbors = list(graph.neighbors(entity))
            
            # 基于共同邻居推断关系
            for neighbor in neighbors:
                neighbor_neighbors = list(graph.neighbors(neighbor))
                
                for potential_target in neighbor_neighbors:
                    if potential_target != entity and potential_target not in neighbors:
                        # 检查是否已存在关系
                        if not graph.has_edge(entity, potential_target):
                            # 推断关系
                            inference = self._infer_relation(
                                graph, entity, neighbor, potential_target
                            )
                            if inference:
                                inferences.append(inference)
            
            # 按置信度排序
            inferences.sort(key=lambda x: x["confidence"], reverse=True)
            
            return inferences[:max_inferences]
            
        except Exception as e:
            logger.error(f"推断缺失关系失败: {e}")
            return []
    
    def _infer_relation(
        self,
        graph: nx.DiGraph,
        source: str,
        intermediate: str,
        target: str
    ) -> Optional[Dict[str, Any]]:
        """
        推断两个实体间的关系
        """
        try:
            # 获取中间关系
            edge1_data = graph.get_edge_data(source, intermediate)
            edge2_data = graph.get_edge_data(intermediate, target)
            
            if not edge1_data or not edge2_data:
                return None
            
            relation1 = edge1_data.get("relation_type", "")
            relation2 = edge2_data.get("relation_type", "")
            strength1 = edge1_data.get("strength", 0.5)
            strength2 = edge2_data.get("strength", 0.5)
            
            # 关系传递规则
            inferred_relation = self._get_transitive_relation(relation1, relation2)
            if not inferred_relation:
                return None
            
            # 计算置信度
            confidence = (strength1 + strength2) / 2 * 0.8  # 传递关系置信度降低
            
            if confidence < self.inference_threshold:
                return None
            
            return {
                "from_entity": source,
                "to_entity": target,
                "relation_type": inferred_relation,
                "confidence": confidence,
                "inference_path": [source, intermediate, target],
                "reasoning": f"通过 {relation1} 和 {relation2} 推断"
            }
            
        except Exception as e:
            logger.error(f"推断关系失败: {e}")
            return None
    
    def _get_transitive_relation(self, relation1: str, relation2: str) -> Optional[str]:
        """
        获取传递关系
        """
        # 定义关系传递规则
        transitive_rules = {
            ("likes", "similar_to"): "likes",
            ("uses", "part_of"): "uses",
            ("works_with", "belongs_to"): "works_with",
            ("learns", "teaches"): "related_to",
            ("depends_on", "part_of"): "depends_on",
            ("improves", "causes"): "improves",
            ("reduces", "causes"): "reduces"
        }
        
        return transitive_rules.get((relation1, relation2))
    
    def find_central_entities(
        self,
        graph: nx.DiGraph,
        top_k: int = 10,
        metric: str = "betweenness"
    ) -> List[Dict[str, Any]]:
        """
        查找中心实体
        
        Args:
            graph: 知识图谱
            top_k: 返回数量
            metric: 中心性度量方法
            
        Returns:
            List[Dict[str, Any]]: 中心实体列表
        """
        try:
            if metric == "betweenness":
                centrality = nx.betweenness_centrality(graph)
            elif metric == "closeness":
                centrality = nx.closeness_centrality(graph)
            elif metric == "eigenvector":
                centrality = nx.eigenvector_centrality(graph, max_iter=1000)
            elif metric == "degree":
                centrality = dict(graph.degree())
            else:
                centrality = nx.betweenness_centrality(graph)
            
            # 排序并返回Top-K
            sorted_entities = sorted(
                centrality.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            central_entities = []
            for entity, score in sorted_entities[:top_k]:
                entity_data = graph.nodes[entity]
                central_entities.append({
                    "entity_name": entity,
                    "entity_type": entity_data.get("entity_type", "unknown"),
                    "centrality_score": score,
                    "properties": entity_data.get("properties", {})
                })
            
            return central_entities
            
        except Exception as e:
            logger.error(f"查找中心实体失败: {e}")
            return []
    
    def analyze_graph_structure(
        self,
        graph: nx.DiGraph
    ) -> Dict[str, Any]:
        """
        分析图谱结构
        
        Args:
            graph: 知识图谱
            
        Returns:
            Dict[str, Any]: 结构分析结果
        """
        try:
            # 基本统计
            num_nodes = graph.number_of_nodes()
            num_edges = graph.number_of_edges()
            
            # 连通性分析
            is_connected = nx.is_weakly_connected(graph)
            num_components = nx.number_weakly_connected_components(graph)
            
            # 密度
            density = nx.density(graph)
            
            # 度分布
            degrees = dict(graph.degree())
            degree_values = list(degrees.values())
            avg_degree = sum(degree_values) / len(degree_values) if degree_values else 0
            
            # 聚类系数
            clustering = nx.average_clustering(graph.to_undirected())
            
            # 路径长度（如果图连通）
            avg_path_length = None
            if is_connected and num_nodes > 1:
                try:
                    avg_path_length = nx.average_shortest_path_length(graph)
                except:
                    pass
            
            # 关系类型分布
            relation_types = defaultdict(int)
            for edge in graph.edges(data=True):
                relation_type = edge[2].get("relation_type", "unknown")
                relation_types[relation_type] += 1
            
            # 实体类型分布
            entity_types = defaultdict(int)
            for node in graph.nodes(data=True):
                entity_type = node[1].get("entity_type", "unknown")
                entity_types[entity_type] += 1
            
            return {
                "basic_stats": {
                    "num_nodes": num_nodes,
                    "num_edges": num_edges,
                    "density": density,
                    "is_connected": is_connected,
                    "num_components": num_components
                },
                "centrality_stats": {
                    "average_degree": avg_degree,
                    "clustering_coefficient": clustering,
                    "average_path_length": avg_path_length
                },
                "distributions": {
                    "relation_types": dict(relation_types),
                    "entity_types": dict(entity_types)
                }
            }
            
        except Exception as e:
            logger.error(f"分析图谱结构失败: {e}")
            return {
                "basic_stats": {},
                "centrality_stats": {},
                "distributions": {},
                "error": str(e)
            }
    
    def find_shortest_paths(
        self,
        graph: nx.DiGraph,
        source: str,
        targets: List[str]
    ) -> Dict[str, List[str]]:
        """
        查找从源实体到多个目标实体的最短路径
        
        Args:
            graph: 知识图谱
            source: 源实体
            targets: 目标实体列表
            
        Returns:
            Dict[str, List[str]]: 路径字典
        """
        try:
            if source not in graph:
                return {}
            
            paths = {}
            
            for target in targets:
                if target in graph:
                    try:
                        path = nx.shortest_path(graph, source, target)
                        paths[target] = path
                    except nx.NetworkXNoPath:
                        paths[target] = []
                else:
                    paths[target] = []
            
            return paths
            
        except Exception as e:
            logger.error(f"查找最短路径失败: {e}")
            return {}
    
    def find_cycles(
        self,
        graph: nx.DiGraph,
        max_cycle_length: int = 5
    ) -> List[List[str]]:
        """
        查找图中的环
        
        Args:
            graph: 知识图谱
            max_cycle_length: 最大环长度
            
        Returns:
            List[List[str]]: 环列表
        """
        try:
            # 转换为无向图查找简单环
            undirected_graph = graph.to_undirected()
            cycles = list(nx.simple_cycles(graph))
            
            # 过滤长度
            filtered_cycles = [
                cycle for cycle in cycles
                if len(cycle) <= max_cycle_length
            ]
            
            return filtered_cycles
            
        except Exception as e:
            logger.error(f"查找环失败: {e}")
            return []
    
    def suggest_relations(
        self,
        graph: nx.DiGraph,
        entity: str,
        based_on: str = "similarity"
    ) -> List[Dict[str, Any]]:
        """
        建议可能的关系
        
        Args:
            graph: 知识图谱
            entity: 目标实体
            based_on: 建议依据
            
        Returns:
            List[Dict[str, Any]]: 建议的关系列表
        """
        try:
            if entity not in graph:
                return []
            
            suggestions = []
            
            if based_on == "similarity":
                # 基于相似实体建议关系
                suggestions = self._suggest_by_similarity(graph, entity)
            elif based_on == "co_occurrence":
                # 基于共现建议关系
                suggestions = self._suggest_by_co_occurrence(graph, entity)
            elif based_on == "centrality":
                # 基于中心性建议关系
                suggestions = self._suggest_by_centrality(graph, entity)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"建议关系失败: {e}")
            return []
    
    def _suggest_by_similarity(
        self,
        graph: nx.DiGraph,
        entity: str
    ) -> List[Dict[str, Any]]:
        """
        基于相似性建议关系
        """
        suggestions = []
        entity_data = graph.nodes[entity]
        entity_type = entity_data.get("entity_type", "unknown")
        
        # 查找相同类型的实体
        for node in graph.nodes(data=True):
            if node[0] != entity and node[1].get("entity_type") == entity_type:
                if not graph.has_edge(entity, node[0]) and not graph.has_edge(node[0], entity):
                    suggestions.append({
                        "target_entity": node[0],
                        "suggested_relation": "similar_to",
                        "confidence": 0.6,
                        "reason": f"相同类型: {entity_type}"
                    })
        
        return suggestions[:5]  # 返回前5个建议
    
    def _suggest_by_co_occurrence(
        self,
        graph: nx.DiGraph,
        entity: str
    ) -> List[Dict[str, Any]]:
        """
        基于共现建议关系
        """
        suggestions = []
        
        # 获取实体的邻居
        neighbors = list(graph.neighbors(entity))
        
        # 查找邻居的邻居
        for neighbor in neighbors:
            neighbor_neighbors = list(graph.neighbors(neighbor))
            for target in neighbor_neighbors:
                if target != entity and target not in neighbors:
                    if not graph.has_edge(entity, target) and not graph.has_edge(target, entity):
                        suggestions.append({
                            "target_entity": target,
                            "suggested_relation": "related_to",
                            "confidence": 0.5,
                            "reason": f"通过共同邻居: {neighbor}"
                        })
        
        return suggestions[:5]
    
    def _suggest_by_centrality(
        self,
        graph: nx.DiGraph,
        entity: str
    ) -> List[Dict[str, Any]]:
        """
        基于中心性建议关系
        """
        suggestions = []
        
        # 获取中心实体
        central_entities = self.find_central_entities(graph, top_k=10)
        
        for central_entity in central_entities:
            target = central_entity["entity_name"]
            if target != entity and not graph.has_edge(entity, target) and not graph.has_edge(target, entity):
                suggestions.append({
                    "target_entity": target,
                    "suggested_relation": "related_to",
                    "confidence": 0.4,
                    "reason": f"中心实体: {central_entity['centrality_score']:.3f}"
                })
        
        return suggestions[:5]
