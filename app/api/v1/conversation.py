"""
文件名: conversation.py
功能: 会话管理接口
"""

from typing import List

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.schemas.base import SuccessResponse
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate
)
from app.services.conversation_service import ConversationService
from app.utils.logger import get_logger
from app.utils.exceptions import ResourceNotFoundError

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/conversations", tags=["会话管理"])


@router.post("", response_model=SuccessResponse[ConversationResponse], summary="创建会话")
async def create_conversation(
    request: ConversationCreate,
    user_id: int = Query(1, description="用户ID"),  # 暂时硬编码为1
    db: Session = Depends(get_database)
):
    """
    创建新会话
    
    参数:
        request (ConversationCreate): 创建请求
        user_id (int): 用户ID
        db (Session): 数据库会话
    
    返回:
        SuccessResponse[ConversationResponse]: 创建的会话信息
    """
    service = ConversationService(db)
    
    # 创建会话
    conversation = service.create_conversation(
        user_id=user_id,
        title=request.title or "新对话",
        model_provider=request.model_provider,
        model_name=request.model_name
    )
    
    # 转换为响应格式
    response_data = ConversationResponse.model_validate(conversation)
    
    return SuccessResponse.create(
        data=response_data,
        message="会话创建成功"
    )


@router.get("", response_model=SuccessResponse[List[ConversationResponse]], summary="获取会话列表")
async def get_conversations(
    user_id: int = Query(1, description="用户ID"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回的最大记录数"),
    db: Session = Depends(get_database)
):
    """
    获取用户的会话列表
    
    参数:
        user_id (int): 用户ID
        skip (int): 跳过的记录数
        limit (int): 返回的最大记录数
        db (Session): 数据库会话
    
    返回:
        SuccessResponse[List[ConversationResponse]]: 会话列表
    """
    service = ConversationService(db)
    
    # 查询会话列表
    conversations = service.get_user_conversations(
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    
    # 转换为响应格式
    response_data = [
        ConversationResponse.model_validate(conv)
        for conv in conversations
    ]
    
    return SuccessResponse.create(
        data=response_data,
        message="查询成功"
    )


@router.get("/{conversation_id}", response_model=SuccessResponse[ConversationResponse], summary="获取会话详情")
async def get_conversation(
    conversation_id: int = Path(..., description="会话ID"),
    db: Session = Depends(get_database)
):
    """
    获取会话详情
    
    参数:
        conversation_id (int): 会话ID
        db (Session): 数据库会话
    
    返回:
        SuccessResponse[ConversationResponse]: 会话信息
    
    异常:
        ResourceNotFoundError: 会话不存在时抛出
    """
    service = ConversationService(db)
    
    # 查询会话
    conversation = service.get_conversation(conversation_id)
    
    if not conversation:
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=conversation_id
        )
    
    # 转换为响应格式
    response_data = ConversationResponse.model_validate(conversation)
    
    return SuccessResponse.create(
        data=response_data,
        message="查询成功"
    )


@router.patch("/{conversation_id}", response_model=SuccessResponse[ConversationResponse], summary="更新会话")
async def update_conversation(
    request: ConversationUpdate,
    conversation_id: int = Path(..., description="会话ID"),
    db: Session = Depends(get_database)
):
    """
    更新会话信息
    
    参数:
        request (ConversationUpdate): 更新请求
        conversation_id (int): 会话ID
        db (Session): 数据库会话
    
    返回:
        SuccessResponse[ConversationResponse]: 更新后的会话信息
    """
    service = ConversationService(db)
    
    # 更新会话标题
    conversation = service.update_title(conversation_id, request.title)
    
    if not conversation:
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=conversation_id
        )
    
    # 转换为响应格式
    response_data = ConversationResponse.model_validate(conversation)
    
    return SuccessResponse.create(
        data=response_data,
        message="更新成功"
    )


@router.delete("/{conversation_id}", response_model=SuccessResponse[bool], summary="删除会话")
async def delete_conversation(
    conversation_id: int = Path(..., description="会话ID"),
    db: Session = Depends(get_database)
):
    """
    删除会话（软删除）
    
    参数:
        conversation_id (int): 会话ID
        db (Session): 数据库会话
    
    返回:
        SuccessResponse[bool]: 是否删除成功
    """
    service = ConversationService(db)
    
    # 删除会话
    success = service.delete_conversation(conversation_id)
    
    return SuccessResponse.create(
        data=success,
        message="删除成功" if success else "会话不存在"
    )

