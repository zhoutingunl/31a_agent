"""
文件名: customer_service.py
功能: 电商客服API接口
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
router = APIRouter(prefix="/customer_service", tags=["电商客服"])


@router.post("/chat", response_model=SuccessResponse[ChatResponse], summary="电商客服对话")
async def customer_service_chat(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    电商客服对话接口
    
    功能特点:
    - 仅使用会话级短期记忆（不记忆用户个人信息）
    - 工具权限受限（仅允许订单查询、商品搜索等）
    - 专注于电商场景的快速响应
    - 预留RAG知识库支持（商品/政策文档检索）
    
    参数:
        request (MessageSend): 消息请求
        
    返回:
        SuccessResponse[ChatResponse]: 对话响应
    """
    try:
        # 初始化电商客服角色服务
        role_service = RoleService(
            db=db,
            llm=llm,
            role_type="customer_service"
        )
        
        # 处理对话
        response = await role_service.chat(request, stream=False)
        
        logger.info(
            "电商客服对话完成",
            conversation_id=response.conversation_id,
            message_id=response.message_id
        )
        
        return SuccessResponse(
            data=response,
            message="客服响应成功"
        )
        
    except Exception as e:
        logger.error(f"电商客服对话失败: {e}")
        raise


@router.get("/info", summary="获取电商客服信息")
async def get_customer_service_info(
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    获取电商客服角色信息
    
    返回:
        角色配置信息
    """
    try:
        role_service = RoleService(
            db=db,
            llm=llm,
            role_type="customer_service"
        )
        
        info = role_service.get_role_info()
        
        return SuccessResponse(
            data=info,
            message="获取角色信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取电商客服信息失败: {e}")
        raise
