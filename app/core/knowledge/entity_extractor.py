"""
实体提取器

从文本中提取实体，包括实体识别、类型分类和属性提取
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EntityExtractor:
    """
    实体提取器
    
    从文本中提取实体:
    - 使用LLM识别实体
    - 实体类型分类
    - 实体属性提取
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化实体提取器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self.entity_types = [
            "person",      # 人物
            "product",     # 产品
            "concept",     # 概念
            "event",       # 事件
            "location",    # 地点
            "organization", # 组织
            "technology",  # 技术
            "skill",       # 技能
            "preference",  # 偏好
            "goal"         # 目标
        ]
        logger.info("实体提取器初始化完成")
    
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        max_entities: int = 10
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取实体
        
        Args:
            text: 输入文本
            entity_types: 指定的实体类型列表
            max_entities: 最大提取实体数量
            
        Returns:
            List[Dict[str, Any]]: 提取的实体列表
        """
        try:
            if not text or not text.strip():
                return []
            
            # 使用LLM提取实体
            entities = await self._extract_with_llm(
                text=text,
                entity_types=entity_types or self.entity_types,
                max_entities=max_entities
            )
            
            # 后处理和验证
            validated_entities = self._validate_entities(entities)
            
            logger.debug(f"从文本中提取到 {len(validated_entities)} 个实体")
            return validated_entities
            
        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []
    
    async def _extract_with_llm(
        self,
        text: str,
        entity_types: List[str],
        max_entities: int
    ) -> List[Dict[str, Any]]:
        """
        使用LLM提取实体
        """
        prompt = f"""
请从以下文本中提取实体，返回JSON格式：

文本: {text}

实体类型: {', '.join(entity_types)}

要求:
1. 提取最多 {max_entities} 个实体
2. 每个实体必须包含名称、类型和属性
3. 属性应该包含相关的描述信息
4. 实体名称要准确，避免重复

返回格式:
[
    {{
        "name": "实体名称",
        "type": "实体类型",
        "properties": {{
            "description": "实体描述",
            "confidence": 0.8,
            "context": "在文本中的上下文"
        }}
    }}
]

请只返回JSON数组，不要包含其他内容。
"""
        
        try:
            response = await self.llm.generate([{"role": "user", "content": prompt}])
            
            # 解析JSON响应
            entities = json.loads(response)
            
            if not isinstance(entities, list):
                logger.warning("LLM返回的不是列表格式")
                return []
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应JSON失败: {e}")
            # 尝试从响应中提取JSON
            return self._extract_json_from_response(response)
        except Exception as e:
            logger.error(f"LLM实体提取失败: {e}")
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
    
    def _validate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和清理提取的实体
        """
        validated = []
        seen_names = set()
        
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            
            # 检查必需字段
            if not entity.get("name") or not entity.get("type"):
                continue
            
            name = entity["name"].strip()
            entity_type = entity["type"].strip().lower()
            
            # 去重
            if name in seen_names:
                continue
            seen_names.add(name)
            
            # 验证实体类型
            if entity_type not in self.entity_types:
                # 尝试映射到标准类型
                entity_type = self._map_entity_type(entity_type)
                if not entity_type:
                    continue
            
            # 清理属性
            properties = entity.get("properties", {})
            if not isinstance(properties, dict):
                properties = {}
            
            # 添加默认属性
            properties.setdefault("confidence", 0.8)
            properties.setdefault("extracted_at", datetime.now().isoformat())
            
            validated_entity = {
                "name": name,
                "type": entity_type,
                "properties": properties
            }
            
            validated.append(validated_entity)
        
        return validated
    
    def _map_entity_type(self, entity_type: str) -> Optional[str]:
        """
        将非标准实体类型映射到标准类型
        """
        type_mapping = {
            "人": "person",
            "人物": "person",
            "用户": "person",
            "产品": "product",
            "商品": "product",
            "概念": "concept",
            "想法": "concept",
            "事件": "event",
            "活动": "event",
            "地点": "location",
            "位置": "location",
            "组织": "organization",
            "公司": "organization",
            "技术": "technology",
            "技能": "skill",
            "能力": "skill",
            "偏好": "preference",
            "喜欢": "preference",
            "目标": "goal",
            "目的": "goal"
        }
        
        return type_mapping.get(entity_type.lower())
    
    async def batch_extract_entities(
        self,
        texts: List[str],
        entity_types: Optional[List[str]] = None,
        max_entities_per_text: int = 5
    ) -> List[List[Dict[str, Any]]]:
        """
        批量提取实体
        
        Args:
            texts: 文本列表
            entity_types: 实体类型列表
            max_entities_per_text: 每个文本最大提取实体数
            
        Returns:
            List[List[Dict[str, Any]]]: 每个文本对应的实体列表
        """
        results = []
        
        for text in texts:
            entities = await self.extract_entities(
                text=text,
                entity_types=entity_types,
                max_entities=max_entities_per_text
            )
            results.append(entities)
        
        logger.info(f"批量提取完成: {len(texts)} 个文本，共提取 {sum(len(r) for r in results)} 个实体")
        return results
    
    def get_entity_statistics(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取实体统计信息
        
        Args:
            entities: 实体列表
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not entities:
            return {
                "total_count": 0,
                "type_distribution": {},
                "confidence_stats": {}
            }
        
        # 类型分布
        type_distribution = {}
        confidences = []
        
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            type_distribution[entity_type] = type_distribution.get(entity_type, 0) + 1
            
            confidence = entity.get("properties", {}).get("confidence", 0.8)
            confidences.append(confidence)
        
        # 置信度统计
        confidence_stats = {
            "mean": sum(confidences) / len(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0
        }
        
        return {
            "total_count": len(entities),
            "type_distribution": type_distribution,
            "confidence_stats": confidence_stats
        }
    
    async def extract_entities_from_memory(
        self,
        memory_content: str,
        memory_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        从记忆内容中提取实体
        
        Args:
            memory_content: 记忆内容
            memory_type: 记忆类型
            context: 上下文信息
            
        Returns:
            List[Dict[str, Any]]: 提取的实体列表
        """
        # 根据记忆类型调整提取策略
        if memory_type == "preference":
            # 偏好类记忆，重点提取产品和概念
            entity_types = ["product", "concept", "preference"]
        elif memory_type == "fact":
            # 事实类记忆，重点提取人物、组织、事件
            entity_types = ["person", "organization", "event", "location"]
        elif memory_type == "skill":
            # 技能类记忆，重点提取技术和技能
            entity_types = ["technology", "skill", "concept"]
        else:
            # 默认提取所有类型
            entity_types = self.entity_types
        
        entities = await self.extract_entities(
            text=memory_content,
            entity_types=entity_types,
            max_entities=8
        )
        
        # 添加记忆上下文信息
        for entity in entities:
            entity["properties"]["memory_type"] = memory_type
            if context:
                entity["properties"]["context"] = context
        
        return entities
