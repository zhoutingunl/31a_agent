"""
文件名: conversation.py
功能: 会话相关的 Pydantic Schema
"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """
    创建会话请求 Schema
    
    字段:
        title (str): 会话标题
        model_provider (str): 模型提供商
        model_name (str): 模型名称
    """
    
    title: Optional[str] = Field(default="新对话", description="会话标题")
    model_provider: Optional[str] = Field(default=None, description="模型提供商")
    model_name: Optional[str] = Field(default=None, description="模型名称")


class ConversationResponse(BaseModel):
    """
    会话响应 Schema
    
    字段:
        id (int): 会话ID
        user_id (int): 用户ID
        title (str): 会话标题
        model_provider (str): 模型提供商
        model_name (str): 模型名称
        message_count (int): 消息数量
        last_message_at (datetime): 最后消息时间
        created_at (datetime): 创建时间
        updated_at (datetime): 更新时间
    """
    
    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")
    model_provider: Optional[str] = Field(default=None, description="模型提供商")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    message_count: int = Field(..., description="消息数量")
    last_message_at: Optional[datetime] = Field(default=None, description="最后消息时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        """Pydantic 配置"""
        from_attributes = True  # 允许从 ORM 模型创建


class ConversationUpdate(BaseModel):
    """
    更新会话请求 Schema
    
    字段:
        title (str): 会话标题
    """
    
    title: str = Field(..., min_length=1, max_length=200, description="会话标题")

