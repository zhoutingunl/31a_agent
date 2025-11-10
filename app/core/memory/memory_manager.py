"""
记忆管理器

该模块是记忆管理系统的核心，负责：
- 记忆的添加、检索、更新、删除
- 自动分类和评分
- 短期记忆到长期记忆的升级
- 记忆的压缩和遗忘
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.dao.memory_dao import MemoryDAO
from app.models.memory import MemoryStore
from .memory_classifier import MemoryClassifier
from .importance_scorer import ImportanceScorer
from .memory_compressor import MemoryCompressor
from .forgetting_mechanism import ForgettingMechanism

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    记忆管理器主类
    
    统一管理记忆的整个生命周期，协调各个子模块
    """
    
    def __init__(self, db: Session, llm: BaseLLM, vector_store=None):
        """
        初始化记忆管理器
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            vector_store: 向量存储实例（可选）
        """
        self.db = db
        self.llm = llm
        self.vector_store = vector_store
        
        # 初始化DAO和子模块
        self.memory_dao = MemoryDAO(db)
        self.classifier = MemoryClassifier(llm)
        self.scorer = ImportanceScorer(llm)
        self.compressor = MemoryCompressor(llm)
        self.forgetting = ForgettingMechanism()
        
        logger.info("记忆管理器初始化完成")
    
    async def add_memory(
        self, 
        conversation_id: int,
        content: str,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> MemoryStore:
        """
        添加新记忆
        
        Args:
            conversation_id: 会话ID
            content: 记忆内容
            memory_type: 记忆类型（可选，会自动分类）
            metadata: 元数据
            
        Returns:
            MemoryStore: 创建的记忆对象
        """
        try:
            # 自动分类记忆类型
            if memory_type is None:
                memory_type = await self.classifier.classify_memory(content)
            
            # 创建记忆对象
            memory = MemoryStore(
                conversation_id=conversation_id,
                content=content,
                memory_type=memory_type,
                memory_metadata=metadata or {}
            )
            
            # 计算重要性分数
            importance_score = await self.scorer.score_memory(memory)
            memory.importance_score = importance_score
            
            # 保存到数据库
            saved_memory = self.memory_dao.create(memory)
            
            # 添加到向量存储（如果可用）
            if self.vector_store:
                try:
                    await self.vector_store.add_memory(
                        memory_id=saved_memory.id,
                        content=content,
                        memory_type=memory_type,
                        metadata=metadata or {}
                    )
                except Exception as e:
                    logger.warning(f"添加记忆到向量存储失败: {e}")
            
            logger.info(f"新记忆已添加: ID={saved_memory.id}, 类型={memory_type}, "
                       f"重要性={importance_score:.3f}")
            
            return saved_memory
            
        except Exception as e:
            logger.error(f"添加记忆失败: {e}")
            raise
    
    async def get_relevant_memories(
        self,
        conversation_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[MemoryStore]:
        """
        获取相关记忆
        
        Args:
            conversation_id: 会话ID
            query: 查询内容
            memory_types: 记忆类型过滤（可选）
            limit: 返回数量限制
            
        Returns:
            List[MemoryStore]: 相关记忆列表
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
            
            # 简单的关键词匹配（后续会升级为语义搜索）
            relevant_memories = self._simple_relevance_search(
                filtered_memories, query
            )
            
            # 按重要性排序并限制数量
            relevant_memories.sort(
                key=lambda m: m.importance_score or 0,
                reverse=True
            )
            
            result = relevant_memories[:limit]
            
            logger.debug(f"找到{len(result)}条相关记忆")
            return result
            
        except Exception as e:
            logger.error(f"获取相关记忆失败: {e}")
            return []
    
    async def semantic_search(
        self,
        conversation_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[MemoryStore]:
        """
        语义搜索记忆
        
        Args:
            conversation_id: 会话ID
            query: 查询内容
            memory_types: 记忆类型过滤
            limit: 返回数量限制
            
        Returns:
            List[MemoryStore]: 相关记忆列表
        """
        try:
            if not self.vector_store:
                logger.warning("向量存储不可用，降级到关键词搜索")
                return await self.get_relevant_memories(
                    conversation_id=conversation_id,
                    query=query,
                    memory_types=memory_types,
                    limit=limit
                )
            
            # 使用向量存储进行语义搜索
            vector_results = await self.vector_store.search_memories(
                query=query,
                memory_type=memory_types[0] if memory_types else None,
                top_k=limit
            )
            
            # 获取完整记忆对象
            memory_ids = [result[0] for result in vector_results]
            memories = []
            
            for memory_id in memory_ids:
                memory = self.memory_dao.get_by_id(memory_id)
                if memory:
                    memories.append(memory)
            
            logger.debug(f"语义搜索完成: 查询='{query}', 找到{len(memories)}条结果")
            return memories
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            # 降级到关键词搜索
            return await self.get_relevant_memories(
                conversation_id=conversation_id,
                query=query,
                memory_types=memory_types,
                limit=limit
            )
    
    async def upgrade_to_long_term(
        self,
        short_term_memories: List[MemoryStore]
    ) -> List[MemoryStore]:
        """
        将短期记忆升级为长期记忆
        
        Args:
            short_term_memories: 短期记忆列表
            
        Returns:
            List[MemoryStore]: 升级后的长期记忆列表
        """
        try:
            upgraded_memories = []
            
            for memory in short_term_memories:
                # 检查是否应该升级
                if self._should_upgrade_to_long_term(memory):
                    # 更新记忆类型
                    memory.memory_type = "long_term"
                    
                    # 重新计算重要性分数
                    new_importance = await self.scorer.score_memory(memory)
                    memory.importance_score = new_importance
                    
                    # 更新元数据
                    metadata = memory.memory_metadata or {}
                    metadata["upgraded_at"] = datetime.utcnow().isoformat()
                    metadata["original_type"] = "short_term"
                    memory.memory_metadata = metadata
                    
                    # 保存到数据库
                    updated_memory = self.memory_dao.update(memory)
                    upgraded_memories.append(updated_memory)
                    
                    logger.debug(f"记忆已升级为长期记忆: ID={memory.id}")
            
            logger.info(f"成功升级{len(upgraded_memories)}条短期记忆为长期记忆")
            return upgraded_memories
            
        except Exception as e:
            logger.error(f"记忆升级失败: {e}")
            return []
    
    async def compress_memories(
        self,
        memories: List[MemoryStore]
    ) -> MemoryStore:
        """
        压缩多个记忆为单个摘要记忆
        
        Args:
            memories: 要压缩的记忆列表
            
        Returns:
            MemoryStore: 压缩后的记忆对象
        """
        try:
            if not memories:
                raise ValueError("记忆列表不能为空")
            
            # 使用压缩器压缩记忆
            compressed_memory = await self.compressor.compress_memories(memories)
            
            # 保存压缩后的记忆
            saved_memory = self.memory_dao.create(compressed_memory)
            
            # 标记原始记忆为已压缩
            for memory in memories:
                metadata = memory.memory_metadata or {}
                metadata["compressed_into"] = saved_memory.id
                metadata["compressed_at"] = datetime.utcnow().isoformat()
                memory.memory_metadata = metadata
                self.memory_dao.update(memory)
            
            logger.info(f"成功压缩{len(memories)}条记忆为1条摘要记忆")
            return saved_memory
            
        except Exception as e:
            logger.error(f"记忆压缩失败: {e}")
            raise
    
    async def apply_forgetting(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """
        应用遗忘机制
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Dict[str, Any]: 遗忘结果统计
        """
        try:
            # 获取会话的所有记忆
            memories = self.memory_dao.get_by_conversation(conversation_id)
            
            # 应用遗忘机制
            result = await self.forgetting.apply_forgetting(memories)
            
            # 删除被遗忘的记忆
            forgotten_count = 0
            for memory in result["forgotten_memories"]:
                try:
                    self.memory_dao.delete(memory.id)
                    forgotten_count += 1
                except Exception as e:
                    logger.error(f"删除记忆失败: ID={memory.id}, 错误={e}")
            
            result["deleted_count"] = forgotten_count
            
            logger.info(f"遗忘机制应用完成: 删除了{forgotten_count}条记忆")
            return result
            
        except Exception as e:
            logger.error(f"应用遗忘机制失败: {e}")
            return {
                "total_memories": 0,
                "forgotten_count": 0,
                "retained_count": 0,
                "deleted_count": 0,
                "error": str(e)
            }
    
    async def maintain_memories(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """
        维护记忆系统
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Dict[str, Any]: 维护结果统计
        """
        try:
            maintenance_result = {
                "upgraded_count": 0,
                "compressed_count": 0,
                "forgotten_count": 0,
                "total_memories": 0
            }
            
            # 获取会话的所有记忆
            all_memories = self.memory_dao.get_by_conversation(conversation_id)
            maintenance_result["total_memories"] = len(all_memories)
            
            if not all_memories:
                return maintenance_result
            
            # 1. 升级短期记忆为长期记忆
            short_term_memories = [
                m for m in all_memories 
                if m.memory_type == "short_term"
            ]
            
            if short_term_memories:
                upgraded = await self.upgrade_to_long_term(short_term_memories)
                maintenance_result["upgraded_count"] = len(upgraded)
            
            # 2. 压缩相似记忆
            long_term_memories = [
                m for m in all_memories 
                if m.memory_type == "long_term"
            ]
            
            if len(long_term_memories) > 10:  # 只有长期记忆较多时才压缩
                # 按重要性分组，压缩低重要性记忆
                low_importance_memories = [
                    m for m in long_term_memories
                    if (m.importance_score or 0) < 0.5
                ]
                
                if len(low_importance_memories) > 5:
                    try:
                        await self.compress_memories(low_importance_memories[:5])
                        maintenance_result["compressed_count"] = 5
                    except Exception as e:
                        logger.error(f"记忆压缩失败: {e}")
            
            # 3. 应用遗忘机制
            forget_result = await self.apply_forgetting(conversation_id)
            maintenance_result["forgotten_count"] = forget_result.get("deleted_count", 0)
            
            logger.info(f"记忆维护完成: 升级{maintenance_result['upgraded_count']}条, "
                       f"压缩{maintenance_result['compressed_count']}条, "
                       f"遗忘{maintenance_result['forgotten_count']}条")
            
            return maintenance_result
            
        except Exception as e:
            logger.error(f"记忆维护失败: {e}")
            return {
                "upgraded_count": 0,
                "compressed_count": 0,
                "forgotten_count": 0,
                "total_memories": 0,
                "error": str(e)
            }
    
    def _should_upgrade_to_long_term(self, memory: MemoryStore) -> bool:
        """
        判断记忆是否应该升级为长期记忆
        
        Args:
            memory: 记忆对象
            
        Returns:
            bool: 是否应该升级
        """
        try:
            # 检查记忆类型
            if memory.memory_type != "short_term":
                return False
            
            # 检查重要性分数
            if memory.importance_score and memory.importance_score >= 0.6:
                return True
            
            # 检查访问频率
            metadata = memory.memory_metadata or {}
            access_count = metadata.get("access_count", 0)
            if access_count >= 3:
                return True
            
            # 检查创建时间（超过24小时的短期记忆考虑升级）
            if (datetime.utcnow() - memory.created_at).total_seconds() > 24 * 3600:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"升级判断失败: {e}")
            return False
    
    def _simple_relevance_search(
        self,
        memories: List[MemoryStore],
        query: str
    ) -> List[MemoryStore]:
        """
        简单的相关性搜索（后续会升级为语义搜索）
        
        Args:
            memories: 记忆列表
            query: 查询内容
            
        Returns:
            List[MemoryStore]: 相关记忆列表
        """
        try:
            query_lower = query.lower()
            relevant_memories = []
            
            for memory in memories:
                content_lower = memory.content.lower()
                
                # 简单的关键词匹配
                if any(keyword in content_lower for keyword in query_lower.split()):
                    relevant_memories.append(memory)
            
            return relevant_memories
            
        except Exception as e:
            logger.error(f"相关性搜索失败: {e}")
            return []
    
    def get_memory_statistics(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            memories = self.memory_dao.get_by_conversation(conversation_id)
            
            # 按类型统计
            type_stats = {}
            for memory in memories:
                memory_type = memory.memory_type
                if memory_type not in type_stats:
                    type_stats[memory_type] = 0
                type_stats[memory_type] += 1
            
            # 计算平均重要性
            importance_scores = [m.importance_score for m in memories if m.importance_score]
            avg_importance = sum(importance_scores) / len(importance_scores) if importance_scores else 0
            
            # 计算访问统计
            total_access = 0
            for memory in memories:
                metadata = memory.memory_metadata or {}
                total_access += metadata.get("access_count", 0)
            
            statistics = {
                "total_memories": len(memories),
                "type_distribution": type_stats,
                "average_importance": round(avg_importance, 3),
                "total_access_count": total_access,
                "average_access_per_memory": round(total_access / len(memories), 2) if memories else 0
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取记忆统计失败: {e}")
            return {
                "total_memories": 0,
                "type_distribution": {},
                "average_importance": 0,
                "total_access_count": 0,
                "average_access_per_memory": 0,
                "error": str(e)
            }
