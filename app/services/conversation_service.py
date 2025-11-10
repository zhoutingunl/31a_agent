"""
文件名: conversation_service.py
功能: 会话管理服务，负责会话相关的业务逻辑
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.dao.conversation_dao import ConversationDAO
from app.dao.user_dao import UserDAO
from app.models.conversation import Conversation
from app.utils.logger import get_logger
from app.utils.exceptions import ResourceNotFoundError, ValidationError

logger = get_logger(__name__)


class ConversationService:
    """
    会话管理服务类
    
    功能：
    - 创建新会话
    - 查询会话列表
    - 获取会话详情
    - 删除会话
    - 更新会话标题
    
    属性:
        dao (ConversationDAO): 会话数据访问对象
        user_dao (UserDAO): 用户数据访问对象
        logger: 日志记录器
    """
    
    def __init__(self, db: Session):
        """
        初始化会话服务
        
        参数:
            db (Session): 数据库会话
        """
        self.dao = ConversationDAO(db)  # 会话 DAO
        self.user_dao = UserDAO(db)  # 用户 DAO
        self.logger = get_logger(__name__)  # 日志记录器
    
    def create_conversation(
        self,
        user_id: int,
        title: str = "新对话",
        model_provider: str = None,
        model_name: str = None
    ) -> Conversation:
        """
        创建新会话
        
        参数:
            user_id (int): 用户ID
            title (str): 会话标题
            model_provider (str, optional): 模型提供商
            model_name (str, optional): 模型名称
        
        返回:
            Conversation: 创建的会话对象
        
        异常:
            ResourceNotFoundError: 用户不存在时抛出
        """
        # 检查用户是否存在
        user = self.user_dao.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError(
                f"用户不存在",
                resource_type="User",
                resource_id=user_id
            )
        
        # 创建会话对象
        conversation = Conversation(
            user_id=user_id,
            title=title,
            model_provider=model_provider,
            model_name=model_name,
            status=1,
            message_count=0
        )
        
        # 保存到数据库
        conversation = self.dao.create(conversation)
        
        self.logger.info(
            "会话创建成功",
            conversation_id=conversation.id,
            user_id=user_id,
            title=title
        )
        
        return conversation
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """
        获取会话详情
        
        参数:
            conversation_id (int): 会话ID
        
        返回:
            Optional[Conversation]: 会话对象
        """
        return self.dao.get_by_id(conversation_id)
    
    def get_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """
        获取用户的会话列表
        
        参数:
            user_id (int): 用户ID
            skip (int): 跳过的记录数
            limit (int): 返回的最大记录数
        
        返回:
            List[Conversation]: 会话列表
        """
        return self.dao.get_user_conversations(user_id, skip, limit)
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除会话（软删除）
        
        参数:
            conversation_id (int): 会话ID
        
        返回:
            bool: 是否删除成功
        """
        success = self.dao.delete_by_id(conversation_id, soft_delete=True)
        
        if success:
            self.logger.info(
                "会话删除成功",
                conversation_id=conversation_id
            )
        
        return success
    
    def update_title(self, conversation_id: int, title: str) -> Optional[Conversation]:
        """
        更新会话标题
        
        参数:
            conversation_id (int): 会话ID
            title (str): 新标题
        
        返回:
            Optional[Conversation]: 更新后的会话对象
        """
        if not title or len(title) > 200:
            raise ValidationError(
                "会话标题不能为空且长度不能超过200字符",
                details={"title_length": len(title) if title else 0}
            )
        
        conversation = self.dao.update_by_id(conversation_id, {"title": title})
        
        if conversation:
            self.logger.info(
                "会话标题更新成功",
                conversation_id=conversation_id,
                new_title=title
            )
        
        return conversation

