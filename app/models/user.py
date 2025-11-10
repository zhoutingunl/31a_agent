"""
文件名: user.py
功能: 用户数据模型
"""

from sqlalchemy import Column, BigInteger, String, SmallInteger, Integer
from sqlalchemy.orm import relationship

from app.models.database import Base
from app.models.base import TimestampMixin, BaseModelMixin


class User(Base, TimestampMixin, BaseModelMixin):
    """
    用户模型
    
    存储用户基本信息，用于区分不同用户。
    
    字段:
        id: 用户ID，自增主键
        username: 用户名，唯一标识
        nickname: 用户昵称
        avatar: 头像URL
        status: 用户状态（0-禁用，1-正常）
        created_at: 创建时间
        updated_at: 更新时间
    
    关系:
        conversations: 用户的所有会话
    """
    
    __tablename__ = "user"  # 表名
    __table_args__ = {"comment": "用户表"}  # 表注释
    
    # 主键
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="用户ID，自增主键"
    )
    
    # 基本信息
    username = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="用户名，唯一标识"
    )
    
    nickname = Column(
        String(100),
        nullable=True,
        comment="用户昵称，可为空"
    )
    
    avatar = Column(
        String(500),
        nullable=True,
        comment="用户头像URL，可为空"
    )
    
    # 状态
    status = Column(
        SmallInteger,
        nullable=False,
        default=1,
        index=True,
        comment="用户状态：0-禁用，1-正常"
    )
    
    # 关系（一对多：一个用户有多个会话）
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"  # 删除用户时级联删除会话
    )
    
    # Agent 相关关系
    # knowledge_entities = relationship(
    #     "KnowledgeGraph",
    #     back_populates="user",
    #     cascade="all, delete-orphan"  # 删除用户时级联删除知识实体
    # )

