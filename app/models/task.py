"""
文件名: task.py
功能: 任务管理相关的数据库模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, String, Text, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class Task(Base):
    """
    任务表模型
    
    功能：存储智能体的任务分解与执行信息
    支持任务层次结构、依赖关系、状态跟踪等
    """
    
    __tablename__ = "task"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    
    # 关联字段
    conversation_id = Column(BigInteger, ForeignKey("conversation.id", ondelete="CASCADE"), 
                           nullable=False, comment="会话ID")
    parent_task_id = Column(BigInteger, ForeignKey("task.id", ondelete="CASCADE"), 
                          nullable=True, comment="父任务ID（自引用）")
    
    # 任务基本信息
    task_type = Column(String(50), nullable=False, comment="任务类型：plan/execute/reflect/tool_call")
    description = Column(Text, nullable=False, comment="任务描述")
    status = Column(String(20), nullable=False, default="pending", 
                   comment="状态：pending/running/completed/failed/cancelled")
    priority = Column(Integer, default=0, comment="优先级（数值越大优先级越高）")
    
    # 依赖关系
    dependencies = Column(JSON, nullable=True, comment="依赖任务ID列表 [1, 2, 3]")
    
    # 执行结果
    result = Column(Text, nullable=True, comment="执行结果")
    error_message = Column(Text, nullable=True, comment="错误信息（失败时）")
    retry_count = Column(Integer, default=0, comment="重试次数")
    
    # 元数据
    task_metadata = Column(JSON, nullable=True, comment="元数据（工具参数、执行上下文等）")
    
    # 时间字段
    started_at = Column(DateTime, nullable=True, comment="开始执行时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=func.now(), 
                       onupdate=func.now(), comment="更新时间")
    
    # 关系映射
    # conversation = relationship("Conversation", back_populates="tasks")
    # parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    # subtasks = relationship("Task", back_populates="parent_task", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type={self.task_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "parent_task_id": self.parent_task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "metadata": self.task_metadata,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def is_completed(self) -> bool:
        """检查任务是否已完成"""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.status == "failed"
    
    @property
    def is_running(self) -> bool:
        """检查任务是否正在运行"""
        return self.status == "running"
    
    @property
    def is_pending(self) -> bool:
        """检查任务是否待执行"""
        return self.status == "pending"
    
    def can_start(self) -> bool:
        """检查任务是否可以开始执行"""
        if self.status != "pending":
            return False
        
        # 检查依赖任务是否都已完成
        if self.dependencies:
            # 这里需要查询数据库检查依赖任务状态
            # 暂时返回 True，实际实现时需要在 DAO 层处理
            pass
        
        return True
    
    def mark_started(self) -> None:
        """标记任务为开始状态"""
        self.status = "running"
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, result: Optional[str] = None) -> None:
        """标记任务为完成状态"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result
    
    def mark_failed(self, error_message: str) -> None:
        """标记任务为失败状态"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.retry_count += 1
