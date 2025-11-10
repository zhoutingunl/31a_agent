"""
文件名: message.py
功能: 消息数据模型
"""

from sqlalchemy import Column, BigInteger, String, Text, SmallInteger, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.base import TimestampMixin, BaseModelMixin


class Message(Base, TimestampMixin, BaseModelMixin):
    """
    消息模型
    
    存储会话中的所有消息（包括用户、助手、系统、工具消息）。
    
    字段:
        id: 消息ID，自增主键
        conversation_id: 会话ID，外键关联 conversation 表
        role: 消息角色（user-用户，assistant-助手，system-系统，tool-工具）
        content: 消息内容
        content_type: 内容类型（text-纯文本，image-图片，file-文件）
        token_count: Token 数量统计
        model_provider: 生成该消息的模型提供商
        model_name: 生成该消息的模型名称
        metadata: 元数据（JSON格式）
        is_compressed: 是否已被压缩
        parent_message_id: 父消息ID
        created_at: 创建时间
        updated_at: 更新时间
    
    关系:
        conversation: 所属会话
    """
    
    __tablename__ = "message"  # 表名
    __table_args__ = {"comment": "消息表"}  # 表注释
    
    # 主键
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="消息ID，自增主键"
    )
    
    # 外键
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID，外键关联 conversation 表"
    )
    
    # 消息信息
    role = Column(
        String(20),
        nullable=False,
        index=True,
        comment="消息角色：user-用户，assistant-助手，system-系统，tool-工具"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="消息内容，文本格式"
    )
    
    content_type = Column(
        String(20),
        nullable=False,
        default="text",
        comment="内容类型：text-纯文本，image-图片，file-文件"
    )
    
    # Token 统计
    token_count = Column(
        Integer,
        nullable=True,
        comment="Token 数量统计（可选）"
    )
    
    # 模型信息（仅 assistant 消息）
    model_provider = Column(
        String(50),
        nullable=True,
        comment="生成该消息的模型提供商（仅 assistant）"
    )
    
    model_name = Column(
        String(100),
        nullable=True,
        comment="生成该消息的模型名称（仅 assistant）"
    )
    
    # 元数据（JSON格式，存储额外信息）
    # 注意: metadata 是 SQLAlchemy 保留字段，使用 extra_data 代替
    extra_data = Column(
        JSON,
        nullable=True,
        comment="元数据，JSON 格式，存储额外信息（如工具调用、附件等）"
    )
    
    # 记忆管理
    is_compressed = Column(
        SmallInteger,
        nullable=False,
        default=0,
        index=True,
        comment="是否已被压缩：0-否，1-是"
    )
    
    # 对话分支（可选）
    parent_message_id = Column(
        BigInteger,
        nullable=True,
        comment="父消息ID（用于追踪对话分支，可选）"
    )
    
    # 关系
    conversation = relationship(
        "Conversation",
        back_populates="messages"
    )

