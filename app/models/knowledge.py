"""
文件名: knowledge.py
功能: 知识图谱相关的数据库模型
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, BigInteger, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class KnowledgeGraph(Base):
    """
    知识图谱实体表模型
    
    功能：存储知识图谱中的实体信息
    支持用户个性化知识图谱构建
    """
    
    __tablename__ = "knowledge_graph"
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="实体ID")
    
    # 关联字段
    user_id = Column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), 
                    nullable=False, comment="用户ID")
    
    # 实体基本信息
    entity_type = Column(String(50), nullable=False, 
                        comment="实体类型：person/product/order/concept")
    entity_name = Column(String(200), nullable=False, comment="实体名称")
    properties = Column(JSON, nullable=True, comment="实体属性（键值对）")
    
    # 时间字段
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=func.now(), 
                       onupdate=func.now(), comment="更新时间")
    
    # 关系映射
    # user = relationship("User", back_populates="knowledge_entities")
    outgoing_relations = relationship("KnowledgeRelation", 
                                    foreign_keys="KnowledgeRelation.from_entity_id",
                                    back_populates="from_entity",
                                    cascade="all, delete-orphan")
    incoming_relations = relationship("KnowledgeRelation", 
                                    foreign_keys="KnowledgeRelation.to_entity_id",
                                    back_populates="to_entity",
                                    cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<KnowledgeGraph(id={self.id}, type={self.entity_type}, name={self.entity_name})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def all_relations(self) -> List["KnowledgeRelation"]:
        """获取所有关系（出边和入边）"""
        return self.outgoing_relations + self.incoming_relations
    
    def get_relations_by_type(self, relation_type: str) -> List["KnowledgeRelation"]:
        """根据关系类型获取关系"""
        return [rel for rel in self.all_relations if rel.relation_type == relation_type]
    
    def get_related_entities(self, relation_type: Optional[str] = None) -> List["KnowledgeGraph"]:
        """获取相关实体"""
        related = []
        for rel in self.all_relations:
            if relation_type is None or rel.relation_type == relation_type:
                if rel.from_entity_id == self.id:
                    related.append(rel.to_entity)
                else:
                    related.append(rel.from_entity)
        return related
    
    def add_property(self, key: str, value: Any) -> None:
        """添加属性"""
        if self.properties is None:
            self.properties = {}
        self.properties[key] = value
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """获取属性"""
        if self.properties is None:
            return default
        return self.properties.get(key, default)
    
    def remove_property(self, key: str) -> None:
        """删除属性"""
        if self.properties is not None and key in self.properties:
            del self.properties[key]


class KnowledgeRelation(Base):
    """
    知识图谱关系表模型
    
    功能：存储知识图谱中实体间的关系
    支持有向关系、权重、属性等
    """
    
    __tablename__ = "knowledge_relation"
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="关系ID")
    
    # 关联字段
    from_entity_id = Column(BigInteger, ForeignKey("knowledge_graph.id", ondelete="CASCADE"), 
                          nullable=False, comment="起始实体ID")
    to_entity_id = Column(BigInteger, ForeignKey("knowledge_graph.id", ondelete="CASCADE"), 
                        nullable=False, comment="目标实体ID")
    
    # 关系基本信息
    relation_type = Column(String(50), nullable=False, 
                          comment="关系类型：owns/likes/related_to/depends_on")
    weight = Column(Float, default=1.0, comment="关系权重（0-1）")
    properties = Column(JSON, nullable=True, comment="关系属性")
    
    # 时间字段
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    
    # 关系映射
    from_entity = relationship("KnowledgeGraph", 
                             foreign_keys=[from_entity_id],
                             back_populates="outgoing_relations")
    to_entity = relationship("KnowledgeGraph", 
                           foreign_keys=[to_entity_id],
                           back_populates="incoming_relations")
    
    def __repr__(self) -> str:
        return f"<KnowledgeRelation(id={self.id}, from={self.from_entity_id}, to={self.to_entity_id}, type={self.relation_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "from_entity_id": self.from_entity_id,
            "to_entity_id": self.to_entity_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "properties": self.properties,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def set_weight(self, weight: float) -> None:
        """设置关系权重"""
        if 0.0 <= weight <= 1.0:
            self.weight = weight
        else:
            raise ValueError("关系权重必须在 0.0 到 1.0 之间")
    
    def add_property(self, key: str, value: Any) -> None:
        """添加关系属性"""
        if self.properties is None:
            self.properties = {}
        self.properties[key] = value
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """获取关系属性"""
        if self.properties is None:
            return default
        return self.properties.get(key, default)
    
    def remove_property(self, key: str) -> None:
        """删除关系属性"""
        if self.properties is not None and key in self.properties:
            del self.properties[key]
