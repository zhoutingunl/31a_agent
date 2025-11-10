"""
文件名: memory.py
功能: 记忆管理相关的数据库模型
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, BigInteger, String, Text, Float, Integer, BLOB, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class MemoryStore(Base):
    """
    记忆存储表模型
    
    功能：存储智能体的各种类型记忆
    支持短期记忆、长期记忆、情景记忆、语义记忆等
    """
    
    __tablename__ = "memory_store"
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="记忆ID")
    
    # 关联字段
    conversation_id = Column(BigInteger, ForeignKey("conversation.id", ondelete="CASCADE"), 
                           nullable=False, comment="会话ID")
    
    # 记忆基本信息
    memory_type = Column(String(20), nullable=False, 
                        comment="记忆类型：short_term/long_term/episodic/semantic")
    content = Column(Text, nullable=False, comment="记忆内容")
    
    # 向量嵌入（用于语义检索）
    embedding = Column(BLOB, nullable=True, comment="向量嵌入（用于语义检索）")
    
    # 重要性评分
    importance_score = Column(Float, default=0.0, comment="重要性评分（0-1）")
    
    # 访问统计
    access_count = Column(Integer, default=0, comment="访问次数")
    last_accessed_at = Column(DateTime, nullable=True, comment="最后访问时间")
    
    # 过期时间（短期记忆）
    expires_at = Column(DateTime, nullable=True, comment="过期时间（短期记忆）")
    
    # 元数据
    memory_metadata = Column(JSON, nullable=True, comment="元数据（来源、关联实体等）")
    
    # 时间字段
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    
    # 关系映射
    # conversation = relationship("Conversation", back_populates="memories")
    
    def __repr__(self) -> str:
        return f"<MemoryStore(id={self.id}, type={self.memory_type}, importance={self.importance_score})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "embedding": self.embedding,  # 注意：实际使用时可能需要特殊处理
            "importance_score": self.importance_score,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.memory_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def is_short_term(self) -> bool:
        """检查是否为短期记忆"""
        return self.memory_type == "short_term"
    
    @property
    def is_long_term(self) -> bool:
        """检查是否为长期记忆"""
        return self.memory_type == "long_term"
    
    @property
    def is_episodic(self) -> bool:
        """检查是否为情景记忆"""
        return self.memory_type == "episodic"
    
    @property
    def is_semantic(self) -> bool:
        """检查是否为语义记忆"""
        return self.memory_type == "semantic"
    
    @property
    def is_expired(self) -> bool:
        """检查记忆是否已过期"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def mark_accessed(self) -> None:
        """标记记忆被访问"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
    
    def set_embedding(self, embedding_data: bytes) -> None:
        """设置向量嵌入"""
        self.embedding = embedding_data
    
    def get_embedding(self) -> Optional[bytes]:
        """获取向量嵌入"""
        return self.embedding
    
    def set_importance(self, score: float) -> None:
        """设置重要性评分"""
        if 0.0 <= score <= 1.0:
            self.importance_score = score
        else:
            raise ValueError("重要性评分必须在 0.0 到 1.0 之间")
    
    def set_expiration(self, expires_at: datetime) -> None:
        """设置过期时间"""
        self.expires_at = expires_at
    
    def extend_expiration(self, hours: int = 24) -> None:
        """延长过期时间"""
        if self.expires_at:
            from datetime import timedelta
            self.expires_at += timedelta(hours=hours)
        else:
            self.expires_at = datetime.utcnow() + timedelta(hours=hours)
