"""
关系提取器

从文本中提取实体间关系，包括关系类型识别、属性提取和强度计算
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RelationExtractor:
    """
    关系提取器
    
    从文本中提取实体间关系:
    - 识别关系类型
    - 提取关系属性
    - 计算关系强度
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化关系提取器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self.relation_types = [
            "likes",           # 喜欢
            "dislikes",        # 不喜欢
            "uses",            # 使用
            "works_with",      # 与...工作
            "learns",          # 学习
            "teaches",         # 教授
            "owns",            # 拥有
            "belongs_to",      # 属于
            "located_in",      # 位于
            "related_to",      # 与...相关
            "causes",          # 导致
            "prevents",        # 阻止
            "improves",        # 改善
            "reduces",         # 减少
            "depends_on",      # 依赖于
            "conflicts_with",  # 与...冲突
            "similar_to",      # 类似于
            "different_from",  # 不同于
            "part_of",         # 是...的一部分
            "contains"         # 包含
        ]
        logger.info("关系提取器初始化完成")
    
    async def extract_relations(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        max_relations: int = 10
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取实体间关系
        
        Args:
            text: 输入文本
            entities: 已提取的实体列表
            max_relations: 最大提取关系数量
            
        Returns:
            List[Dict[str, Any]]: 提取的关系列表
        """
        try:
            if not text or not entities or len(entities) < 2:
                return []
            
            # 使用LLM提取关系
            relations = await self._extract_with_llm(
                text=text,
                entities=entities,
                max_relations=max_relations
            )
            
            # 后处理和验证
            validated_relations = self._validate_relations(relations, entities)
            
            logger.debug(f"从文本中提取到 {len(validated_relations)} 个关系")
            return validated_relations
            
        except Exception as e:
            logger.error(f"关系提取失败: {e}")
            return []
    
    async def _extract_with_llm(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        max_relations: int
    ) -> List[Dict[str, Any]]:
        """
        使用LLM提取关系
        """
        # 构建实体信息
        entity_info = []
        for entity in entities:
            entity_info.append(f"- {entity['name']} ({entity['type']})")
        
        prompt = f"""
请从以下文本中提取实体间的关系，返回JSON格式：

文本: {text}

实体列表:
{chr(10).join(entity_info)}

关系类型: {', '.join(self.relation_types)}

要求:
1. 提取最多 {max_relations} 个关系
2. 每个关系必须包含源实体、目标实体、关系类型和强度
3. 关系强度范围0-1，表示关系的确定性
4. 只提取文本中明确表达的关系
5. 实体名称必须与提供的实体列表完全匹配

返回格式:
[
    {{
        "from_entity": "源实体名称",
        "to_entity": "目标实体名称", 
        "relation_type": "关系类型",
        "strength": 0.8,
        "properties": {{
            "description": "关系描述",
            "context": "在文本中的上下文",
            "confidence": 0.8
        }}
    }}
]

请只返回JSON数组，不要包含其他内容。
"""
        
        try:
            response = await self.llm.generate([{"role": "user", "content": prompt}])
            
            # 解析JSON响应
            relations = json.loads(response)
            
            if not isinstance(relations, list):
                logger.warning("LLM返回的不是列表格式")
                return []
            
            return relations
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败: {e}")
            # 尝试从响应中提取JSON
            return self._extract_json_from_response(response)
        except Exception as e:
            logger.error(f"LLM关系提取失败: {e}")
            return []
    
    def _extract_json_from_response(self, response: str) -> List[Dict[str, Any]]:
        """
        从LLM响应中提取JSON
        """
        try:
            # 查找JSON数组
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # 如果没有找到数组，尝试查找单个对象
            obj_match = re.search(r'\{.*\}', response, re.DOTALL)
            if obj_match:
                obj_str = obj_match.group()
                obj = json.loads(obj_str)
                return [obj] if isinstance(obj, dict) else []
            
            return []
            
        except Exception as e:
            logger.error(f"从响应中提取JSON失败: {e}")
            return []
    
    def _validate_relations(
        self, 
        relations: List[Dict[str, Any]], 
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        验证和清理提取的关系
        """
        validated = []
        entity_names = {entity["name"] for entity in entities}
        seen_relations = set()
        
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            
            # 检查必需字段
            from_entity = relation.get("from_entity", "").strip()
            to_entity = relation.get("to_entity", "").strip()
            relation_type = relation.get("relation_type", "").strip().lower()
            strength = relation.get("strength", 0.5)
            
            if not from_entity or not to_entity or not relation_type:
                continue
            
            # 验证实体存在
            if from_entity not in entity_names or to_entity not in entity_names:
                continue
            
            # 避免自关系
            if from_entity == to_entity:
                continue
            
            # 去重
            relation_key = (from_entity, to_entity, relation_type)
            if relation_key in seen_relations:
                continue
            seen_relations.add(relation_key)
            
            # 验证关系类型
            if relation_type not in self.relation_types:
                # 尝试映射到标准类型
                relation_type = self._map_relation_type(relation_type)
                if not relation_type:
                    continue
            
            # 验证强度
            try:
                strength = float(strength)
                strength = max(0.0, min(1.0, strength))  # 限制在0-1范围
            except (ValueError, TypeError):
                strength = 0.5
            
            # 清理属性
            properties = relation.get("properties", {})
            if not isinstance(properties, dict):
                properties = {}
            
            # 添加默认属性
            properties.setdefault("confidence", 0.8)
            properties.setdefault("extracted_at", datetime.now().isoformat())
            
            validated_relation = {
                "from_entity": from_entity,
                "to_entity": to_entity,
                "relation_type": relation_type,
                "strength": strength,
                "properties": properties
            }
            
            validated.append(validated_relation)
        
        return validated
    
    def _map_relation_type(self, relation_type: str) -> Optional[str]:
        """
        将非标准关系类型映射到标准类型
        """
        type_mapping = {
            "喜欢": "likes",
            "爱": "likes",
            "偏好": "likes",
            "不喜欢": "dislikes",
            "讨厌": "dislikes",
            "使用": "uses",
            "运用": "uses",
            "工作": "works_with",
            "合作": "works_with",
            "学习": "learns",
            "学会": "learns",
            "教授": "teaches",
            "教": "teaches",
            "拥有": "owns",
            "属于": "belongs_to",
            "位于": "located_in",
            "在": "located_in",
            "相关": "related_to",
            "导致": "causes",
            "引起": "causes",
            "阻止": "prevents",
            "防止": "prevents",
            "改善": "improves",
            "提高": "improves",
            "减少": "reduces",
            "降低": "reduces",
            "依赖": "depends_on",
            "依靠": "depends_on",
            "冲突": "conflicts_with",
            "矛盾": "conflicts_with",
            "类似": "similar_to",
            "相似": "similar_to",
            "不同": "different_from",
            "区别": "different_from",
            "部分": "part_of",
            "包含": "contains",
            "包括": "contains"
        }
        
        return type_mapping.get(relation_type.lower())
    
    async def batch_extract_relations(
        self,
        text_entity_pairs: List[Tuple[str, List[Dict[str, Any]]]],
        max_relations_per_text: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        批量提取关系
        
        Args:
            text_entity_pairs: (文本, 实体列表) 的元组列表
            max_relations_per_text: 每个文本最大提取关系数
            
        Returns:
            List[List[Dict[str, Any]]]: 每个文本对应的关系列表
        """
        results = []
        
        for text, entities in text_entity_pairs:
            relations = await self.extract_relations(
                text=text,
                entities=entities,
                max_relations=max_relations_per_text
            )
            results.append(relations)
        
        logger.info(f"批量关系提取完成: {len(text_entity_pairs)} 个文本，共提取 {sum(len(r) for r in results)} 个关系")
        return results
    
    def get_relation_statistics(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取关系统计信息
        
        Args:
            relations: 关系列表
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not relations:
            return {
                "total_count": 0,
                "type_distribution": {},
                "strength_stats": {},
                "entity_connectivity": {}
            }
        
        # 类型分布
        type_distribution = {}
        strengths = []
        entity_connections = {}
        
        for relation in relations:
            relation_type = relation.get("relation_type", "unknown")
            type_distribution[relation_type] = type_distribution.get(relation_type, 0) + 1
            
            strength = relation.get("strength", 0.5)
            strengths.append(strength)
            
            # 统计实体连接度
            from_entity = relation.get("from_entity", "")
            to_entity = relation.get("to_entity", "")
            
            entity_connections[from_entity] = entity_connections.get(from_entity, 0) + 1
            entity_connections[to_entity] = entity_connections.get(to_entity, 0) + 1
        
        # 强度统计
        strength_stats = {
            "mean": sum(strengths) / len(strengths) if strengths else 0,
            "min": min(strengths) if strengths else 0,
            "max": max(strengths) if strengths else 0
        }
        
        return {
            "total_count": len(relations),
            "type_distribution": type_distribution,
            "strength_stats": strength_stats,
            "entity_connectivity": entity_connections
        }
    
    async def extract_relations_from_memory(
        self,
        memory_content: str,
        entities: List[Dict[str, Any]],
        memory_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        从记忆内容中提取关系
        
        Args:
            memory_content: 记忆内容
            entities: 实体列表
            memory_type: 记忆类型
            context: 上下文信息
            
        Returns:
            List[Dict[str, Any]]: 提取的关系列表
        """
        # 根据记忆类型调整关系提取策略
        if memory_type == "preference":
            # 偏好类记忆，重点提取喜欢/不喜欢关系
            max_relations = 3
        elif memory_type == "fact":
            # 事实类记忆，重点提取各种关系
            max_relations = 8
        elif memory_type == "skill":
            # 技能类记忆，重点提取使用/学习关系
            max_relations = 5
        else:
            max_relations = 6
        
        relations = await self.extract_relations(
            text=memory_content,
            entities=entities,
            max_relations=max_relations
        )
        
        # 添加记忆上下文信息
        for relation in relations:
            relation["properties"]["memory_type"] = memory_type
            if context:
                relation["properties"]["context"] = context
        
        return relations
    
    def find_relation_patterns(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        发现关系模式
        
        Args:
            relations: 关系列表
            
        Returns:
            Dict[str, Any]: 关系模式分析结果
        """
        if not relations:
            return {"patterns": [], "insights": []}
        
        # 分析关系模式
        patterns = []
        insights = []
        
        # 1. 对称关系分析
        symmetric_relations = self._find_symmetric_relations(relations)
        if symmetric_relations:
            patterns.append({
                "type": "symmetric_relations",
                "count": len(symmetric_relations),
                "relations": symmetric_relations
            })
            insights.append(f"发现 {len(symmetric_relations)} 对对称关系")
        
        # 2. 传递关系分析
        transitive_relations = self._find_transitive_relations(relations)
        if transitive_relations:
            patterns.append({
                "type": "transitive_relations", 
                "count": len(transitive_relations),
                "relations": transitive_relations
            })
            insights.append(f"发现 {len(transitive_relations)} 个传递关系链")
        
        # 3. 中心实体分析
        central_entities = self._find_central_entities(relations)
        if central_entities:
            patterns.append({
                "type": "central_entities",
                "entities": central_entities
            })
            insights.append(f"发现 {len(central_entities)} 个中心实体")
        
        return {
            "patterns": patterns,
            "insights": insights
        }
    
    def _find_symmetric_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找对称关系"""
        symmetric = []
        relation_map = {}
        
        for relation in relations:
            key = (relation["from_entity"], relation["to_entity"], relation["relation_type"])
            reverse_key = (relation["to_entity"], relation["from_entity"], relation["relation_type"])
            
            if reverse_key in relation_map:
                symmetric.append({
                    "relation1": relation_map[reverse_key],
                    "relation2": relation
                })
            
            relation_map[key] = relation
        
        return symmetric
    
    def _find_transitive_relations(self, relations: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """查找传递关系"""
        # 简化的传递关系检测
        transitive_chains = []
        
        # 构建关系图
        graph = {}
        for relation in relations:
            from_entity = relation["from_entity"]
            to_entity = relation["to_entity"]
            relation_type = relation["relation_type"]
            
            if from_entity not in graph:
                graph[from_entity] = []
            graph[from_entity].append((to_entity, relation_type, relation))
        
        # 查找长度为2的传递链
        for entity, connections in graph.items():
            for target, rel_type, rel in connections:
                if target in graph:
                    for target_target, target_rel_type, target_rel in graph[target]:
                        if rel_type == target_rel_type:  # 相同关系类型
                            transitive_chains.append([rel, target_rel])
        
        return transitive_chains
    
    def _find_central_entities(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找中心实体"""
        entity_connections = {}
        
        for relation in relations:
            from_entity = relation["from_entity"]
            to_entity = relation["to_entity"]
            
            entity_connections[from_entity] = entity_connections.get(from_entity, 0) + 1
            entity_connections[to_entity] = entity_connections.get(to_entity, 0) + 1
        
        # 找出连接度最高的实体
        sorted_entities = sorted(
            entity_connections.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 返回连接度大于平均值的实体
        if not sorted_entities:
            return []
        
        avg_connections = sum(entity_connections.values()) / len(entity_connections)
        central_entities = [
            {"entity": entity, "connections": count}
            for entity, count in sorted_entities
            if count > avg_connections
        ]
        
        return central_entities[:5]  # 返回前5个中心实体
