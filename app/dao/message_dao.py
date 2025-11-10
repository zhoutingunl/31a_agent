"""
文件名: message_dao.py
功能: 消息数据访问对象，负责消息相关的数据库操作
"""

from typing import List, Optional

from sqlalchemy import select, desc, asc
from sqlalchemy.orm import Session

from app.dao.base import BaseDAO
from app.models.message import Message
from app.utils.logger import get_logger
from app.utils.exceptions import DatabaseError

logger = get_logger(__name__)


class MessageDAO(BaseDAO[Message]):
    """
    消息 DAO 类
    
    提供消息相关的数据库操作，包括：
    - 查询会话的消息列表
    - 创建新消息
    - 查询未压缩的消息
    - 标记消息为已压缩
    """
    
    def __init__(self, db: Session):
        """
        初始化消息 DAO
        
        参数:
            db (Session): 数据库会话
        """
        super().__init__(Message, db)
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
        only_uncompressed: bool = False
    ) -> List[Message]:
        """
        获取会话的消息列表
        
        参数:
            conversation_id (int): 会话ID
            skip (int): 跳过的记录数
            limit (int): 返回的最大记录数
            only_uncompressed (bool): 是否只返回未压缩的消息
        
        返回:
            List[Message]: 消息列表，按创建时间正序
        """
        try:
            # 构建查询
            stmt = select(Message).where(
                Message.conversation_id == conversation_id
            )
            
            # 只查询未压缩的消息
            if only_uncompressed:
                stmt = stmt.where(Message.is_compressed == 0)
            
            # 按创建时间正序排序
            stmt = stmt.order_by(asc(Message.created_at))
            
            # 分页
            stmt = stmt.offset(skip).limit(limit)
            
            # 执行查询
            result = self.db.execute(stmt).scalars().all()
            
            self.logger.debug(
                "查询会话消息列表",
                conversation_id=conversation_id,
                only_uncompressed=only_uncompressed,
                count=len(result)
            )
            
            return list(result)
            
        except Exception as e:
            self.logger.error(
                "查询会话消息列表失败",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "查询消息列表失败",
                details={"conversation_id": conversation_id, "error": str(e)}
            )
    
    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> List[Message]:
        """
        获取会话的最近N条消息（用于构建上下文）
        
        参数:
            conversation_id (int): 会话ID
            limit (int): 返回的最大记录数
        
        返回:
            List[Message]: 最近的消息列表，按创建时间正序
        """
        try:
            # 先按时间倒序查询最近N条，然后反转为正序
            stmt = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.is_compressed == 0  # 只查询未压缩的消息
            ).order_by(
                desc(Message.created_at)
            ).limit(limit)
            
            result = self.db.execute(stmt).scalars().all()
            
            # 反转列表，使其按时间正序
            messages = list(reversed(list(result)))
            
            self.logger.debug(
                "查询最近消息",
                conversation_id=conversation_id,
                limit=limit,
                count=len(messages)
            )
            
            return messages
            
        except Exception as e:
            self.logger.error(
                "查询最近消息失败",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "查询最近消息失败",
                details={"conversation_id": conversation_id, "error": str(e)}
            )
    
    def mark_as_compressed(self, message_ids: List[int]) -> int:
        """
        标记消息为已压缩
        
        参数:
            message_ids (List[int]): 消息ID列表
        
        返回:
            int: 更新的记录数
        """
        try:
            if not message_ids:
                return 0
            
            # 批量更新
            stmt = select(Message).where(Message.id.in_(message_ids))
            messages = self.db.execute(stmt).scalars().all()
            
            count = 0
            for message in messages:
                message.is_compressed = 1
                count += 1
            
            self.db.commit()
            
            self.logger.info(
                "消息标记为已压缩",
                count=count
            )
            
            return count
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "标记消息为已压缩失败",
                message_ids=message_ids,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                "标记消息失败",
                details={"message_ids": message_ids, "error": str(e)}
            )
    
    def count_by_conversation(self, conversation_id: int, only_uncompressed: bool = False) -> int:
        """
        统计会话的消息数量
        
        参数:
            conversation_id (int): 会话ID
            only_uncompressed (bool): 是否只统计未压缩的消息
        
        返回:
            int: 消息数量
        """
        filters = {"conversation_id": conversation_id}
        if only_uncompressed:
            filters["is_compressed"] = 0
        
        return self.count(**filters)

