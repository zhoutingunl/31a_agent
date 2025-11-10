"""
文件名: general.py
功能: 通用助手API接口
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_database, get_llm_instance
from app.schemas.base import SuccessResponse
from app.schemas.message import MessageSend, ChatResponse
from app.services.role_service import RoleService
from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/general", tags=["通用助手"])


@router.post("/chat", response_model=SuccessResponse[ChatResponse], summary="通用助手对话")
async def general_chat(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    通用助手对话接口
    
    功能特点:
    - 支持完整的记忆管理（短期、长期、知识图谱）
    - 支持所有工具调用
    - 支持任务规划和分解
    - 支持自我反思和纠错
    
    参数:
        request (MessageSend): 消息请求
        
    返回:
        SuccessResponse[ChatResponse]: 对话响应
    """
    try:
        # 初始化通用助手角色服务
        role_service = RoleService(
            db=db,
            llm=llm,
            role_type="general"
        )
        
        # 处理对话
        response = await role_service.chat(request, stream=False)
        
        logger.info(
            "通用助手对话完成",
            conversation_id=response.conversation_id,
            message_id=response.message_id
        )
        
        return SuccessResponse(
            data=response,
            message="对话成功"
        )
        
    except Exception as e:
        logger.error(f"通用助手对话失败: {e}")
        raise


@router.get("/info", summary="获取通用助手信息")
async def get_general_info(
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    获取通用助手角色信息
    
    返回:
        角色配置信息
    """
    try:
        role_service = RoleService(
            db=db,
            llm=llm,
            role_type="general"
        )
        
        info = role_service.get_role_info()
        
        return SuccessResponse(
            data=info,
            message="获取角色信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取通用助手信息失败: {e}")
        raise
