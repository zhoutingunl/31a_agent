"""
混合检索器

实现结合向量检索、关键词检索、时间过滤和重要性排序的混合检索策略
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from app.models.memory import MemoryStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器
    
    结合多种检索策略：
    - 向量检索（语义相似度）
    - 关键词检索（精确匹配）
    - 时间过滤（最近优先）
    - 重要性排序（高分优先）
    """
    
    def __init__(
        self,
        vector_store=None,
        memory_dao=None
    ):
        """
        初始化混合检索器
        
        Args:
            vector_store: 向量存储实例
            memory_dao: 记忆DAO实例
        """
        self.vector_store = vector_store
        self.memory_dao = memory_dao
        
        logger.info("混合检索器初始化完成")
    
    async def retrieve(
        self,
        query: str,
        conversation_id: int,
        strategy: str = "hybrid",
        limit: int = 5,
        memory_types: Optional[List[str]] = None
    ) -> List[MemoryStore]:
        """
        检索记忆
        
        Args:
            query: 查询内容
            conversation_id: 会话ID
            strategy: 检索策略 ("vector", "keyword", "hybrid")
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            
        Returns:
            List[MemoryStore]: 检索结果
        """
        try:
            if strategy == "vector":
                return await self._vector_retrieve(query, conversation_id, limit, memory_types)
            elif strategy == "keyword":
                return await self._keyword_retrieve(query, conversation_id, limit, memory_types)
            elif strategy == "hybrid":
                return await self._hybrid_retrieve(query, conversation_id, limit, memory_types)
            else:
                raise ValueError(f"未知的检索策略: {strategy}")
                
        except Exception as e:
            logger.error(f"记忆检索失败: {e}")
            return []
    
    async def _vector_retrieve(
        self,
        query: str,
        conversation_id: int,
        limit: int,
        memory_types: Optional[List[str]] = None
    ) -> List[MemoryStore]:
        """
        向量检索
        
        Args:
            query: 查询内容
            conversation_id: 会话ID
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            
        Returns:
            List[MemoryStore]: 检索结果
        """
        try:
            if not self.vector_store:
                logger.warning("向量存储不可用，降级到关键词检索")
                return await self._keyword_retrieve(query, conversation_id, limit, memory_types)
            
            # 使用向量存储进行语义搜索
            vector_results = await self.vector_store.search_memories(
                query=query,
                memory_type=memory_types[0] if memory_types else None,
                top_k=limit * 2  # 获取更多结果用于后续过滤
            )
            
            # 获取完整记忆对象
            memory_ids = [result[0] for result in vector_results]
            memories = []
            
            for memory_id in memory_ids:
                memory = self.memory_dao.get_by_id(memory_id)
                if memory and memory.conversation_id == conversation_id:
                    memories.append(memory)
            
            # 按相似度排序
            id_to_score = {result[0]: result[1] for result in vector_results}
            memories.sort(key=lambda m: id_to_score.get(m.id, 0), reverse=True)
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    async def _keyword_retrieve(
        self,
        query: str,
        conversation_id: int,
        limit: int,
        memory_types: Optional[List[str]] = None
    ) -> List[MemoryStore]:
        """
        关键词检索
        
        Args:
            query: 查询内容
            conversation_id: 会话ID
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            
        Returns:
            List[MemoryStore]: 检索结果
        """
        try:
            # 获取会话的所有记忆
            all_memories = self.memory_dao.get_by_conversation(conversation_id)
            
            # 按类型过滤
            if memory_types:
                filtered_memories = [
                    m for m in all_memories 
                    if m.memory_type in memory_types
                ]
            else:
                filtered_memories = all_memories
            
            # 关键词匹配
            keywords = self._extract_keywords(query)
            relevant_memories = []
            
            for memory in filtered_memories:
                score = self._calculate_keyword_score(memory.content, keywords)
                if score > 0:
                    relevant_memories.append((memory, score))
            
            # 按关键词匹配分数排序
            relevant_memories.sort(key=lambda x: x[1], reverse=True)
            
            return [memory for memory, _ in relevant_memories[:limit]]
            
        except Exception as e:
            logger.error(f"关键词检索失败: {e}")
            return []
    
    async def _hybrid_retrieve(
        self,
        query: str,
        conversation_id: int,
        limit: int,
        memory_types: Optional[List[str]] = None
    ) -> List[MemoryStore]:
        """
        混合检索
        
        Args:
            query: 查询内容
            conversation_id: 会话ID
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            
        Returns:
            List[MemoryStore]: 检索结果
        """
        try:
            # 向量检索
            vector_memories = await self._vector_retrieve(
                query, conversation_id, limit * 2, memory_types
            )
            
            # 关键词检索
            keyword_memories = await self._keyword_retrieve(
                query, conversation_id, limit * 2, memory_types
            )
            
            # 合并结果
            all_memories = self._merge_results(vector_memories, keyword_memories)
            
            # 重新排序
            ranked_memories = self._rerank(all_memories, query)
            
            return ranked_memories[:limit]
            
        except Exception as e:
            logger.error(f"混合检索失败: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词
        
        Args:
            query: 查询内容
            
        Returns:
            List[str]: 关键词列表
        """
        try:
            # 简单的关键词提取
            # 去除标点符号，分割成词
            words = re.findall(r'\w+', query.lower())
            
            # 过滤停用词（简单版本）
            stop_words = {
                '的', '了', '在', '是', '我', '你', '他', '她', '它', '们',
                '这', '那', '有', '和', '与', '或', '但', '因为', '所以',
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'
            }
            
            keywords = [word for word in words if word not in stop_words and len(word) > 1]
            
            return keywords
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """
        计算关键词匹配分数
        
        Args:
            content: 内容
            keywords: 关键词列表
            
        Returns:
            float: 匹配分数
        """
        try:
            if not keywords:
                return 0.0
            
            content_lower = content.lower()
            matches = 0
            
            for keyword in keywords:
                if keyword in content_lower:
                    matches += 1
            
            # 计算匹配比例
            score = matches / len(keywords)
            
            # 考虑关键词在内容中的频率
            total_keyword_count = sum(content_lower.count(keyword) for keyword in keywords)
            frequency_bonus = min(0.2, total_keyword_count * 0.05)  # 最多0.2的奖励
            
            return score + frequency_bonus
            
        except Exception as e:
            logger.error(f"关键词分数计算失败: {e}")
            return 0.0
    
    def _merge_results(
        self,
        vector_memories: List[MemoryStore],
        keyword_memories: List[MemoryStore]
    ) -> List[MemoryStore]:
        """
        合并检索结果
        
        Args:
            vector_memories: 向量检索结果
            keyword_memories: 关键词检索结果
            
        Returns:
            List[MemoryStore]: 合并后的结果
        """
        try:
            # 使用字典去重
            memory_dict = {}
            
            # 添加向量检索结果（权重较高）
            for i, memory in enumerate(vector_memories):
                memory_dict[memory.id] = {
                    'memory': memory,
                    'vector_score': 1.0 - (i * 0.1),  # 递减分数
                    'keyword_score': 0.0
                }
            
            # 添加关键词检索结果
            for i, memory in enumerate(keyword_memories):
                if memory.id in memory_dict:
                    # 如果已存在，更新关键词分数
                    memory_dict[memory.id]['keyword_score'] = 1.0 - (i * 0.1)
                else:
                    # 如果不存在，添加新记录
                    memory_dict[memory.id] = {
                        'memory': memory,
                        'vector_score': 0.0,
                        'keyword_score': 1.0 - (i * 0.1)
                    }
            
            # 转换为列表
            all_memories = [data['memory'] for data in memory_dict.values()]
            
            return all_memories
            
        except Exception as e:
            logger.error(f"结果合并失败: {e}")
            return vector_memories + keyword_memories
    
    def _rerank(
        self,
        memories: List[MemoryStore],
        query: str
    ) -> List[MemoryStore]:
        """
        重新排序记忆
        
        Args:
            memories: 记忆列表
            query: 查询内容
            
        Returns:
            List[MemoryStore]: 重新排序后的记忆列表
        """
        try:
            # 计算综合分数
            scored_memories = []
            
            for memory in memories:
                score = self._calculate_comprehensive_score(memory, query)
                scored_memories.append((memory, score))
            
            # 按分数排序
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            
            return [memory for memory, _ in scored_memories]
            
        except Exception as e:
            logger.error(f"重新排序失败: {e}")
            return memories
    
    def _calculate_comprehensive_score(
        self,
        memory: MemoryStore,
        query: str
    ) -> float:
        """
        计算综合分数
        
        Args:
            memory: 记忆对象
            query: 查询内容
            
        Returns:
            float: 综合分数
        """
        try:
            score = 0.0
            
            # 重要性分数（权重：0.4）
            importance_score = memory.importance_score or 0.0
            score += importance_score * 0.4
            
            # 时间因素（权重：0.2）
            time_score = self._calculate_time_score(memory.created_at)
            score += time_score * 0.2
            
            # 访问频率（权重：0.1）
            access_score = self._calculate_access_score(memory)
            score += access_score * 0.1
            
            # 内容长度（权重：0.1）
            length_score = self._calculate_length_score(memory.content)
            score += length_score * 0.1
            
            # 记忆类型（权重：0.2）
            type_score = self._calculate_type_score(memory.memory_type)
            score += type_score * 0.2
            
            return min(1.0, score)  # 确保分数不超过1.0
            
        except Exception as e:
            logger.error(f"综合分数计算失败: {e}")
            return 0.0
    
    def _calculate_time_score(self, created_at: datetime) -> float:
        """
        计算时间分数
        
        Args:
            created_at: 创建时间
            
        Returns:
            float: 时间分数
        """
        try:
            now = datetime.utcnow()
            time_diff = (now - created_at).total_seconds() / 3600  # 小时
            
            # 使用指数衰减
            if time_diff <= 1:  # 1小时内
                return 1.0
            elif time_diff <= 24:  # 1天内
                return 0.8
            elif time_diff <= 168:  # 1周内
                return 0.6
            elif time_diff <= 720:  # 1月内
                return 0.4
            else:  # 1月以上
                return 0.2
                
        except Exception as e:
            logger.error(f"时间分数计算失败: {e}")
            return 0.5
    
    def _calculate_access_score(self, memory: MemoryStore) -> float:
        """
        计算访问分数
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 访问分数
        """
        try:
            metadata = memory.memory_metadata or {}
            access_count = metadata.get("access_count", 0)
            
            # 使用对数函数计算访问分数
            if access_count == 0:
                return 0.1
            elif access_count <= 5:
                return 0.3 + (access_count * 0.1)
            elif access_count <= 20:
                return 0.8 + ((access_count - 5) * 0.01)
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"访问分数计算失败: {e}")
            return 0.3
    
    def _calculate_length_score(self, content: str) -> float:
        """
        计算内容长度分数
        
        Args:
            content: 内容
            
        Returns:
            float: 长度分数
        """
        try:
            length = len(content)
            
            # 适中的长度得分最高
            if 50 <= length <= 500:
                return 1.0
            elif 20 <= length < 50 or 500 < length <= 1000:
                return 0.8
            elif 10 <= length < 20 or 1000 < length <= 2000:
                return 0.6
            else:
                return 0.4
                
        except Exception as e:
            logger.error(f"长度分数计算失败: {e}")
            return 0.5
    
    def _calculate_type_score(self, memory_type: str) -> float:
        """
        计算记忆类型分数
        
        Args:
            memory_type: 记忆类型
            
        Returns:
            float: 类型分数
        """
        try:
            type_scores = {
                "long_term": 1.0,
                "semantic": 0.9,
                "episodic": 0.8,
                "short_term": 0.6
            }
            
            return type_scores.get(memory_type, 0.5)
            
        except Exception as e:
            logger.error(f"类型分数计算失败: {e}")
            return 0.5
