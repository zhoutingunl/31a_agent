"""
文件名: message_service.py
功能: 消息管理服务，负责消息相关的业务逻辑
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.dao.message_dao import MessageDAO
from app.dao.conversation_dao import ConversationDAO
from app.models.message import Message
from app.utils.logger import get_logger
from app.utils.exceptions import ResourceNotFoundError, ValidationError

logger = get_logger(__name__)


class MessageService:
    """
    消息管理服务类
    
    功能：
    - 创建新消息
    - 查询消息列表
    - 获取消息详情
    - 获取最近消息（用于上下文）
    
    属性:
        dao (MessageDAO): 消息数据访问对象
        conversation_dao (ConversationDAO): 会话数据访问对象
        logger: 日志记录器
    """
    
    def __init__(self, db: Session):
        """
        初始化消息服务
        
        参数:
            db (Session): 数据库会话
        """
        self.dao = MessageDAO(db)  # 消息 DAO
        self.conversation_dao = ConversationDAO(db)  # 会话 DAO
        self.logger = get_logger(__name__)  # 日志记录器
    
    def create_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        content_type: str = "text",
        model_provider: str = None,
        model_name: str = None,
        token_count: int = None,
        extra_data: dict = None
    ) -> Message:
        """
        创建新消息
        
        参数:
            conversation_id (int): 会话ID
            role (str): 消息角色（user, assistant, system, tool）
            content (str): 消息内容
            content_type (str): 内容类型，默认 text
            model_provider (str, optional): 模型提供商
            model_name (str, optional): 模型名称
            token_count (int, optional): Token 数量
            extra_data (dict, optional): 额外数据
        
        返回:
            Message: 创建的消息对象
        
        异常:
            ResourceNotFoundError: 会话不存在时抛出
            ValidationError: 参数验证失败时抛出
        """
        # 验证角色
        valid_roles = ["user", "assistant", "system", "tool"]
        if role not in valid_roles:
            raise ValidationError(
                f"无效的消息角色: {role}",
                details={"valid_roles": valid_roles}
            )
        
        # 检查会话是否存在
        conversation = self.conversation_dao.get_by_id(conversation_id)
        if not conversation:
            raise ResourceNotFoundError(
                "会话不存在",
                resource_type="Conversation",
                resource_id=conversation_id
            )
        
        # 创建消息对象
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
            model_provider=model_provider,
            model_name=model_name,
            token_count=token_count,
            extra_data=extra_data,
            is_compressed=0
        )
        
        # 保存到数据库
        message = self.dao.create(message)
        
        # 更新会话的消息计数和最后消息时间
        self.conversation_dao.update_message_count(conversation_id, increment=1)
        
        self.logger.info(
            "消息创建成功",
            message_id=message.id,
            conversation_id=conversation_id,
            role=role,
            content_length=len(content)
        )
        
        return message
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 100
    ) -> List[Message]:
        """
        获取会话的所有消息
        
        参数:
            conversation_id (int): 会话ID
            limit (int): 返回的最大记录数
        
        返回:
            List[Message]: 消息列表
        """
        return self.dao.get_conversation_messages(conversation_id, limit=limit)
    
    def get_recent_messages(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> List[Message]:
        """
        获取会话的最近N条消息
        
        参数:
            conversation_id (int): 会话ID
            limit (int): 返回的最大记录数
        
        返回:
            List[Message]: 最近的消息列表
        """
        return self.dao.get_recent_messages(conversation_id, limit)

