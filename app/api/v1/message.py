"""
文件名: message.py
功能: 消息管理接口
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_database
from app.schemas.base import SuccessResponse
from app.schemas.message import MessageResponse
from app.services.message_service import MessageService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["消息管理"])


@router.get("/messages", response_model=SuccessResponse[List[MessageResponse]], summary="获取消息列表")
async def get_messages(
    conversation_id: int = Query(..., description="会话ID"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_database)
):
    """
    获取会话的消息列表
    
    参数:
        conversation_id (int): 会话ID
        limit (int): 返回数量限制（1-100）
    
    返回:
        SuccessResponse[List[MessageResponse]]: 消息列表
    """
    logger.info(
        "获取消息列表",
        conversation_id=conversation_id,
        limit=limit
    )
    
    msg_service = MessageService(db)
    messages = msg_service.get_recent_messages(conversation_id, limit=limit)
    
    logger.info(
        "消息列表获取成功",
        conversation_id=conversation_id,
        message_count=len(messages)
    )
    
    # 转换为响应格式
    response_data = [
        MessageResponse.model_validate(msg)
        for msg in messages
    ]
    
    return SuccessResponse.create(
        data=response_data,
        message="查询成功"
    )

