"""
文件名: conversation.py
功能: 会话数据模型
"""

from sqlalchemy import Column, BigInteger, String, SmallInteger, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.base import TimestampMixin, BaseModelMixin


class Conversation(Base, TimestampMixin, BaseModelMixin):
    """
    会话模型
    
    存储用户的对话会话信息。
    
    字段:
        id: 会话ID，自增主键
        user_id: 用户ID，外键关联 user 表
        title: 会话标题
        model_provider: 使用的模型提供商
        model_name: 使用的具体模型名称
        status: 会话状态（0-已删除，1-正常）
        message_count: 消息数量统计
        last_message_at: 最后一条消息时间
        created_at: 创建时间
        updated_at: 更新时间
    
    关系:
        user: 所属用户
        messages: 会话的所有消息
    """
    
    __tablename__ = "conversation"  # 表名
    __table_args__ = {"comment": "会话表"}  # 表注释
    
    # 主键
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="会话ID，自增主键"
    )
    
    # 外键
    user_id = Column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID，外键关联 user 表"
    )
    
    # 基本信息
    title = Column(
        String(200),
        nullable=False,
        default="新对话",
        comment="会话标题，默认为'新对话'"
    )
    
    model_provider = Column(
        String(50),
        nullable=True,
        comment="使用的模型提供商，如 deepseek、ollama"
    )
    
    model_name = Column(
        String(100),
        nullable=True,
        comment="使用的具体模型名称"
    )
    
    # 状态
    status = Column(
        SmallInteger,
        nullable=False,
        default=1,
        index=True,
        comment="会话状态：0-已删除，1-正常"
    )
    
    # 统计信息
    message_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="消息数量统计"
    )
    
    last_message_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后一条消息时间"
    )
    
    # 关系
    user = relationship(
        "User",
        back_populates="conversations"
    )
    
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",  # 删除会话时级联删除消息
        order_by="Message.created_at"  # 按创建时间排序
    )
    
    # Agent 相关关系
    # tasks = relationship(
    #     "Task",
    #     back_populates="conversation",
    #     cascade="all, delete-orphan",  # 删除会话时级联删除任务
    #     order_by="Task.created_at"  # 按创建时间排序
    # )
    
    # memories = relationship(
    #     "MemoryStore",
    #     back_populates="conversation",
    #     cascade="all, delete-orphan",  # 删除会话时级联删除记忆
    #     order_by="MemoryStore.created_at"  # 按创建时间排序
    # )

