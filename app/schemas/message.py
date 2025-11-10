"""
文件名: message.py
功能: 消息相关的 Pydantic Schema
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class MessageSend(BaseModel):
    """
    发送消息请求 Schema
    
    字段:
        conversation_id (int): 会话ID
        content (str): 消息内容
    """
    
    conversation_id: int = Field(..., description="会话ID")
    content: str = Field(..., min_length=1, description="消息内容")


class VoiceTextRequest(BaseModel):
    """
    语音识别文本请求 Schema
    
    字段:
        text (str): 口语化文本
        conversation_id (int): 会话ID
    """
    
    text: str = Field(..., min_length=1, description="口语化文本")
    conversation_id: int = Field(..., description="会话ID")


class MessageResponse(BaseModel):
    """
    消息响应 Schema
    
    字段:
        id (int): 消息ID
        conversation_id (int): 会话ID
        role (str): 消息角色
        content (str): 消息内容
        content_type (str): 内容类型
        token_count (int): Token 数量
        created_at (datetime): 创建时间
    """
    
    id: int = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="会话ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    content_type: str = Field(..., description="内容类型")
    token_count: Optional[int] = Field(default=None, description="Token 数量")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        """Pydantic 配置"""
        from_attributes = True


class ChatResponse(BaseModel):
    """
    对话响应 Schema
    
    字段:
        conversation_id (int): 会话ID
        user_message (MessageResponse): 用户消息
        assistant_message (MessageResponse): 助手回复
    """
    
    conversation_id: int = Field(..., description="会话ID")
    user_message: MessageResponse = Field(..., description="用户消息")
    assistant_message: MessageResponse = Field(..., description="助手回复")


class ExecuteRequest(BaseModel):
    """
    执行请求 Schema（支持反思功能）
    
    字段:
        conversation_id (int): 会话ID
        task (str): 任务描述
        enable_reflection (bool): 是否启用反思
        max_retries (Optional[int]): 最大重试次数
        expected_goal (Optional[str]): 期望目标
        constraints (Optional[List[str]]): 约束条件
        context_info (Optional[Dict[str, Any]]): 上下文信息
    """
    
    conversation_id: int = Field(..., description="会话ID")
    task: str = Field(..., min_length=1, description="任务描述")
    enable_reflection: bool = Field(default=True, description="是否启用反思")
    max_retries: Optional[int] = Field(default=None, ge=1, le=10, description="最大重试次数")
    expected_goal: Optional[str] = Field(default=None, description="期望目标")
    constraints: Optional[List[str]] = Field(default_factory=list, description="约束条件")
    context_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


class ExecuteResponse(BaseModel):
    """
    执行响应 Schema
    
    字段:
        output (str): 输出内容
        success (bool): 是否成功
        retry_count (int): 重试次数
        execution_time (float): 执行时间（秒）
        reflection_enabled (bool): 是否启用反思
        final_feedback (Optional[Dict[str, Any]]): 最终反馈
        error (Optional[str]): 错误信息
    """
    
    output: str = Field(..., description="输出内容")
    success: bool = Field(..., description="是否成功")
    retry_count: int = Field(..., description="重试次数")
    execution_time: float = Field(..., description="执行时间（秒）")
    reflection_enabled: bool = Field(..., description="是否启用反思")
    final_feedback: Optional[Dict[str, Any]] = Field(default=None, description="最终反馈")
    error: Optional[str] = Field(default=None, description="错误信息")


class StreamResponse(BaseModel):
    """
    流式响应 Schema
    
    字段:
        type (str): 响应类型
        message (str): 消息内容
        data (Optional[Dict[str, Any]]): 响应数据
        timestamp (str): 时间戳
    """
    
    type: str = Field(..., description="响应类型")
    message: str = Field(..., description="消息内容")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    timestamp: str = Field(..., description="时间戳")

