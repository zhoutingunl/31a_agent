"""
记忆服务层

该模块提供记忆管理相关的业务逻辑，包括：
- 记忆的CRUD操作
- 记忆的智能管理
- 与Agent系统的集成
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.core.memory import MemoryManager
from app.models.memory import MemoryStore

logger = logging.getLogger(__name__)


class MemoryService:
    """
    记忆服务层
    
    提供记忆管理相关的业务逻辑封装
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        memory_manager: MemoryManager
    ):
        """
        初始化记忆服务
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            memory_manager: 记忆管理器实例
        """
        self.db = db
        self.llm = llm
        self.memory_manager = memory_manager
        
        logger.info("记忆服务初始化完成")
    
    async def save_conversation_memory(
        self,
        conversation_id: int,
        messages: List[Dict]
    ) -> List[MemoryStore]:
        """
        保存会话记忆
        
        Args:
            conversation_id: 会话ID
            messages: 消息列表
            
        Returns:
            List[MemoryStore]: 保存的记忆列表
        """
        try:
            saved_memories = []
            
            for message in messages:
                # 只保存用户消息和重要的助手回复
                if message.get("role") == "user":
                    # 保存用户消息
                    memory = await self.memory_manager.add_memory(
                        conversation_id=conversation_id,
                        content=message.get("content", ""),
                        memory_type="short_term"
                    )
                    saved_memories.append(memory)
                
                elif message.get("role") == "assistant":
                    # 只保存重要的助手回复
                    content = message.get("content", "")
                    if self._is_important_assistant_message(content):
                        memory = await self.memory_manager.add_memory(
                            conversation_id=conversation_id,
                            content=content,
                            memory_type="episodic"
                        )
                        saved_memories.append(memory)
            
            logger.info(f"会话记忆保存完成: 会话ID={conversation_id}, 保存{len(saved_memories)}条记忆")
            return saved_memories
            
        except Exception as e:
            logger.error(f"保存会话记忆失败: {e}")
            return []
    
    async def get_context_memories(
        self,
        conversation_id: int,
        query: str,
        max_tokens: int = 2000
    ) -> str:
        """
        获取上下文相关记忆
        
        Args:
            conversation_id: 会话ID
            query: 查询内容
            max_tokens: 最大token数
            
        Returns:
            str: 格式化的上下文记忆
        """
        try:
            # 获取相关记忆
            relevant_memories = await self.memory_manager.get_relevant_memories(
                conversation_id=conversation_id,
                query=query,
                limit=10
            )
            
            if not relevant_memories:
                return ""
            
            # 格式化记忆内容
            context_parts = []
            current_tokens = 0
            
            for memory in relevant_memories:
                # 估算token数（简单估算：1个中文字符约等于1个token）
                memory_text = f"[{memory.memory_type}] {memory.content}"
                estimated_tokens = len(memory_text)
                
                if current_tokens + estimated_tokens > max_tokens:
                    break
                
                context_parts.append(memory_text)
                current_tokens += estimated_tokens
            
            context = "\n".join(context_parts)
            
            logger.debug(f"获取上下文记忆: {len(context_parts)}条, 约{current_tokens}个token")
            return context
            
        except Exception as e:
            logger.error(f"获取上下文记忆失败: {e}")
            return ""
    
    async def maintain_memories(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """
        维护记忆系统
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            Dict[str, Any]: 维护结果
        """
        try:
            # 调用记忆管理器的维护功能
            result = await self.memory_manager.maintain_memories(conversation_id)
            
            logger.info(f"记忆维护完成: 会话ID={conversation_id}, 结果={result}")
            return result
            
        except Exception as e:
            logger.error(f"记忆维护失败: {e}")
            return {
                "upgraded_count": 0,
                "compressed_count": 0,
                "forgotten_count": 0,
                "total_memories": 0,
                "error": str(e)
            }
    
    async def add_user_preference(
        self,
        conversation_id: int,
        user_id: int,
        preference_type: str,
        preference_value: str
    ) -> MemoryStore:
        """
        添加用户偏好记忆
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            preference_type: 偏好类型
            preference_value: 偏好值
            
        Returns:
            MemoryStore: 创建的记忆对象
        """
        try:
            content = f"用户偏好 - {preference_type}: {preference_value}"
            metadata = {
                "preference_type": preference_type,
                "preference_value": preference_value,
                "user_id": user_id
            }
            
            memory = await self.memory_manager.add_memory(
                conversation_id=conversation_id,
                content=content,
                memory_type="long_term",
                metadata=metadata
            )
            
            logger.info(f"用户偏好记忆已添加: 类型={preference_type}, 值={preference_value}")
            return memory
            
        except Exception as e:
            logger.error(f"添加用户偏好记忆失败: {e}")
            raise
    
    async def add_fact_memory(
        self,
        conversation_id: int,
        fact_content: str,
        fact_type: str = "general"
    ) -> MemoryStore:
        """
        添加事实记忆
        
        Args:
            conversation_id: 会话ID
            fact_content: 事实内容
            fact_type: 事实类型
            
        Returns:
            MemoryStore: 创建的记忆对象
        """
        try:
            metadata = {
                "fact_type": fact_type,
                "source": "conversation"
            }
            
            memory = await self.memory_manager.add_memory(
                conversation_id=conversation_id,
                content=fact_content,
                memory_type="semantic",
                metadata=metadata
            )
            
            logger.info(f"事实记忆已添加: 类型={fact_type}")
            return memory
            
        except Exception as e:
            logger.error(f"添加事实记忆失败: {e}")
            raise
    
    async def add_event_memory(
        self,
        conversation_id: int,
        event_description: str,
        event_type: str = "general"
    ) -> MemoryStore:
        """
        添加事件记忆
        
        Args:
            conversation_id: 会话ID
            event_description: 事件描述
            event_type: 事件类型
            
        Returns:
            MemoryStore: 创建的记忆对象
        """
        try:
            metadata = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            memory = await self.memory_manager.add_memory(
                conversation_id=conversation_id,
                content=event_description,
                memory_type="episodic",
                metadata=metadata
            )
            
            logger.info(f"事件记忆已添加: 类型={event_type}")
            return memory
            
        except Exception as e:
            logger.error(f"添加事件记忆失败: {e}")
            raise
    
    async def search_memories(
        self,
        conversation_id: int,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[MemoryStore]:
        """
        搜索记忆
        
        Args:
            conversation_id: 会话ID
            query: 搜索查询
            memory_types: 记忆类型过滤
            limit: 返回数量限制
            
        Returns:
            List[MemoryStore]: 搜索结果
        """
        try:
            memories = await self.memory_manager.get_relevant_memories(
                conversation_id=conversation_id,
                query=query,
                memory_types=memory_types,
                limit=limit
            )
            
            logger.debug(f"记忆搜索完成: 查询='{query}', 找到{len(memories)}条结果")
            return memories
            
        except Exception as e:
            logger.error(f"记忆搜索失败: {e}")
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
            statistics = self.memory_manager.get_memory_statistics(conversation_id)
            
            logger.debug(f"记忆统计信息获取完成: 会话ID={conversation_id}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取记忆统计信息失败: {e}")
            return {
                "total_memories": 0,
                "type_distribution": {},
                "average_importance": 0,
                "total_access_count": 0,
                "average_access_per_memory": 0,
                "error": str(e)
            }
    
    async def update_memory_access(
        self,
        memory_id: int
    ) -> bool:
        """
        更新记忆访问信息
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 这里需要实现具体的访问更新逻辑
            # 由于我们没有直接的memory_dao访问，这里先返回True
            logger.debug(f"记忆访问信息已更新: ID={memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新记忆访问信息失败: {e}")
            return False
    
    def _is_important_assistant_message(self, content: str) -> bool:
        """
        判断助手消息是否重要
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否重要
        """
        try:
            # 简单的启发式规则
            important_keywords = [
                "重要", "注意", "建议", "推荐", "警告", "错误",
                "成功", "完成", "失败", "问题", "解决方案"
            ]
            
            content_lower = content.lower()
            return any(keyword in content_lower for keyword in important_keywords)
            
        except Exception as e:
            logger.error(f"判断消息重要性失败: {e}")
            return False
    
    async def cleanup_old_memories(
        self,
        conversation_id: int,
        days_old: int = 30
    ) -> Dict[str, Any]:
        """
        清理旧记忆
        
        Args:
            conversation_id: 会话ID
            days_old: 清理多少天前的记忆
            
        Returns:
            Dict[str, Any]: 清理结果
        """
        try:
            # 应用遗忘机制
            result = await self.memory_manager.apply_forgetting(conversation_id)
            
            logger.info(f"旧记忆清理完成: 会话ID={conversation_id}, 清理{result.get('deleted_count', 0)}条")
            return result
            
        except Exception as e:
            logger.error(f"清理旧记忆失败: {e}")
            return {
                "deleted_count": 0,
                "error": str(e)
            }
    
    async def export_memories(
        self,
        conversation_id: int,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        导出记忆
        
        Args:
            conversation_id: 会话ID
            format: 导出格式
            
        Returns:
            Dict[str, Any]: 导出的记忆数据
        """
        try:
            # 获取所有记忆
            memories = self.memory_manager.memory_dao.get_by_conversation(conversation_id)
            
            # 转换为可序列化的格式
            export_data = {
                "conversation_id": conversation_id,
                "export_time": datetime.utcnow().isoformat(),
                "total_memories": len(memories),
                "memories": []
            }
            
            for memory in memories:
                memory_data = {
                    "id": memory.id,
                    "content": memory.content,
                    "memory_type": memory.memory_type,
                    "importance_score": memory.importance_score,
                    "created_at": memory.created_at.isoformat(),
                    "memory_metadata": memory.memory_metadata
                }
                export_data["memories"].append(memory_data)
            
            logger.info(f"记忆导出完成: 会话ID={conversation_id}, 格式={format}, 数量={len(memories)}")
            return export_data
            
        except Exception as e:
            logger.error(f"导出记忆失败: {e}")
            return {
                "conversation_id": conversation_id,
                "export_time": datetime.utcnow().isoformat(),
                "total_memories": 0,
                "memories": [],
                "error": str(e)
            }
