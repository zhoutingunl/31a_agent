"""
上下文构建器

该模块负责构建LLM的上下文，包括：
- 历史消息的格式化
- 相关记忆的集成
- 系统提示词的添加
- 上下文长度的控制
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.schemas.message import MessageSend
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    上下文构建器
    
    负责构建LLM的完整上下文，包括历史消息和相关记忆
    """
    
    def __init__(
        self, 
        db: Session, 
        memory_service: MemoryService,
        system_prompt: str = None
    ):
        """
        初始化上下文构建器
        
        Args:
            db: 数据库会话
            memory_service: 记忆服务实例
            system_prompt: 系统提示词
        """
        self.db = db
        self.memory_service = memory_service
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(__name__)
    
    async def build_context(
        self,
        conversation_id: int,
        user_id: int,
        include_memories: bool = True,
        max_history: int = 10
    ) -> List[MessageSend]:
        """
        构建完整的上下文
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            include_memories: 是否包含相关记忆
            max_history: 最大历史消息数
            
        Returns:
            List[MessageSend]: 格式化的消息列表
        """
        try:
            # 获取历史消息
            messages = await self._get_history_messages(
                conversation_id, max_history
            )
            
            # 获取相关记忆（如果启用）
            if include_memories and messages:
                relevant_memories = await self.memory_service.get_context_memories(
                    conversation_id=conversation_id,
                    query=messages[-1].content if messages else "",
                    max_tokens=2000
                )
                
                # 将记忆作为系统消息插入
                if relevant_memories:
                    memory_message = MessageSend(
                        role="system",
                        content=f"相关历史记忆:\n{relevant_memories}"
                    )
                    messages.insert(0, memory_message)
            
            # 添加系统提示词
            if self.system_prompt:
                system_message = MessageSend(
                    role="system",
                    content=self.system_prompt
                )
                messages.insert(0, system_message)
            
            self.logger.debug(f"上下文构建完成: 会话ID={conversation_id}, 消息数={len(messages)}")
            return messages
            
        except Exception as e:
            self.logger.error(f"上下文构建失败: {e}")
            return []
    
    def build_messages(
        self,
        messages: List[Message],
        include_system: bool = True
    ) -> List[Dict[str, str]]:
        """
        构建 LLM 消息列表（兼容旧接口）
        
        Args:
            messages: 消息对象列表
            include_system: 是否包含系统提示词
        
        Returns:
            List[Dict[str, str]]: LLM 消息格式列表
        """
        llm_messages = []
        
        # 添加系统提示词
        if include_system and self.system_prompt:
            llm_messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # 转换消息格式
        for msg in messages:
            # 只包含 user 和 assistant 消息
            if msg.role in ["user", "assistant"]:
                llm_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        self.logger.debug(
            f"消息构建完成: 消息数={len(llm_messages)}, 包含系统提示={include_system}"
        )
        
        return llm_messages
    
    async def _get_history_messages(
        self,
        conversation_id: int,
        max_history: int
    ) -> List[MessageSend]:
        """
        获取历史消息
        
        Args:
            conversation_id: 会话ID
            max_history: 最大历史消息数
            
        Returns:
            List[MessageSend]: 历史消息列表
        """
        try:
            # 这里需要实现从数据库获取历史消息的逻辑
            # 暂时返回空列表，后续会实现
            return []
            
        except Exception as e:
            self.logger.error(f"获取历史消息失败: {e}")
            return []
    
    def get_summary(self, messages: List[Message]) -> str:
        """
        生成对话摘要（简化版，仅拼接内容）
        
        Args:
            messages: 消息列表
        
        Returns:
            str: 对话摘要
        """
        summary_parts = []
        
        for msg in messages[:10]:  # 只取前10条
            role_name = "用户" if msg.role == "user" else "助手"
            content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            summary_parts.append(f"{role_name}: {content}")
        
        return "\n".join(summary_parts)

