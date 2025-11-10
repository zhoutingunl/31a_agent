"""
文件名: conversation_dao.py
功能: 会话数据访问对象，负责会话相关的数据库操作
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, desc
from sqlalchemy.orm import Session, joinedload

from app.dao.base import BaseDAO
from app.models.conversation import Conversation
from app.utils.logger import get_logger
from app.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class ConversationDAO(BaseDAO[Conversation]):
    """
    会话 DAO 类
    
    提供会话相关的数据库操作，包括：
    - 查询用户的会话列表
    - 创建新会话
    - 更新会话信息
    - 删除会话
    """
    
    def __init__(self, db: Session):
        """
        初始化会话 DAO
        
        参数:
            db (Session): 数据库会话
        """
        super().__init__(Conversation, db)
    
    def get_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        include_deleted: bool = False
    ) -> List[Conversation]:
        """
        获取用户的会话列表
        
        参数:
            user_id (int): 用户ID
            skip (int): 跳过的记录数
            limit (int): 返回的最大记录数
            include_deleted (bool): 是否包含已删除的会话
        
        返回:
            List[Conversation]: 会话列表，按最后消息时间倒序
        """
        try:
            # 构建查询
            stmt = select(Conversation).where(Conversation.user_id == user_id)
            
            # 过滤已删除的会话
            if not include_deleted:
                stmt = stmt.where(Conversation.status == 1)
            
            # 按最后消息时间倒序排序
            stmt = stmt.order_by(desc(Conversation.last_message_at))
            
            # 分页
            stmt = stmt.offset(skip).limit(limit)
            
            # 执行查询
            result = self.db.execute(stmt).scalars().all()
            
            self.logger.debug(
                "查询用户会话列表",
                user_id=user_id,
                count=len(result)
            )
            
            return list(result)
            
        except Exception as e:
            self.logger.error(
                "查询用户会话列表失败",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "查询会话列表失败",
                details={"user_id": user_id, "error": str(e)}
            )
    
    def get_with_messages(self, conversation_id: int) -> Optional[Conversation]:
        """
        获取会话及其所有消息（预加载）
        
        参数:
            conversation_id (int): 会话ID
        
        返回:
            Optional[Conversation]: 会话对象（含消息列表）
        """
        try:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id
            ).options(
                joinedload(Conversation.messages)  # 预加载消息，避免 N+1 查询
            )
            
            result = self.db.execute(stmt).scalar_one_or_none()
            return result
            
        except Exception as e:
            self.logger.error(
                "查询会话（含消息）失败",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "查询会话失败",
                details={"conversation_id": conversation_id, "error": str(e)}
            )
    
    def update_message_count(self, conversation_id: int, increment: int = 1) -> None:
        """
        更新会话的消息数量
        
        参数:
            conversation_id (int): 会话ID
            increment (int): 增量（可为负数）
        """
        try:
            conversation = self.get_by_id(conversation_id)
            if conversation:
                conversation.message_count += increment
                conversation.last_message_at = datetime.now()
                self.db.commit()
                
                self.logger.debug(
                    "会话消息数量更新",
                    conversation_id=conversation_id,
                    new_count=conversation.message_count
                )
                
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "更新会话消息数量失败",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "更新会话失败",
                details={"conversation_id": conversation_id, "error": str(e)}
            )

