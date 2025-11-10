"""
文件名: chat.py
功能: 对话接口
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import get_database, get_llm_instance
from app.schemas.base import SuccessResponse
from app.schemas.message import MessageSend, ChatResponse, MessageResponse, ExecuteRequest, ExecuteResponse, StreamResponse
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
# from app.core.memory.context_builder import ContextBuilder  # 暂时禁用
from app.core.agent.simple_agent import SimpleAgent
from app.core.agent.tool_agent import ToolAgent  # ⭐ LangGraph Agent
from app.core.llm.base import BaseLLM
from app.tools.manager import tool_manager  # ⭐ 工具管理器
from app.tools.registry import register_all_tools  # ⭐ 统一工具注册中心
from app.services.planning_service import PlanningService  # ⭐ 规划服务
from app.dao.task_dao import TaskDAO  # ⭐ 任务DAO
from app.services.reflection_service import ReflectionService  # ⭐ 反思服务
from app.utils.logger import get_logger
from app.utils.config import config

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/chat", tags=["对话"])

# ⭐ 注册所有工具（自定义 + MCP，启动时执行一次）
try:
    register_all_tools(enable_mcp=True)  # 重新启用 MCP 工具
    logger.info(f"所有工具已注册到对话接口，共 {len(tool_manager)} 个工具")
except Exception as e:
    logger.warning("工具注册失败", error=str(e))


@router.post("/send", response_model=SuccessResponse[ChatResponse], summary="发送消息（非流式）")
async def send_message(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    发送消息并获取回复（非流式）
    
    参数:
        request (MessageSend): 消息发送请求
        db (Session): 数据库会话
        llm (BaseLLM): LLM 实例
    
    返回:
        SuccessResponse[ChatResponse]: 对话响应
    """
    logger.info(
        "收到消息",
        conversation_id=request.conversation_id,
        content_length=len(request.content)
    )
    
    # 初始化服务
    conv_service = ConversationService(db)
    msg_service = MessageService(db)
    
    # 检查会话是否存在
    conversation = conv_service.get_conversation(request.conversation_id)
    if not conversation:
        from app.utils.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=request.conversation_id
        )
    
    # 保存用户消息
    user_message = msg_service.create_message(
        conversation_id=request.conversation_id,
        role="user",
        content=request.content
    )
    
    # 构建上下文
    system_prompt = config.get("prompts.system", "你是一个智能助手。")
    recent_messages = msg_service.get_recent_messages(request.conversation_id, limit=20)
    
    # 暂时简化处理，直接构建消息列表
    llm_messages = []
    if system_prompt:
        llm_messages.append({"role": "system", "content": system_prompt})
    
    for msg in recent_messages:
        llm_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # 调用 ToolAgent（LangGraph）⭐
    agent = ToolAgent(llm, tool_manager)
    assistant_content = agent.run(llm_messages, stream=False)
    
    # 保存助手消息
    assistant_message = msg_service.create_message(
        conversation_id=request.conversation_id,
        role="assistant",
        content=assistant_content,
        model_provider=llm.get_model_info()["provider"],
        model_name=llm.model_name
    )
    
    logger.info(
        "消息处理完成",
        conversation_id=request.conversation_id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id
    )
    
    # 构建响应
    response_data = ChatResponse(
        conversation_id=request.conversation_id,
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(assistant_message)
    )
    
    return SuccessResponse.create(
        data=response_data,
        message="对话成功"
    )


@router.post("/stream", summary="发送消息（流式）")
async def send_message_stream(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    发送消息并获取回复（流式）
    
    参数:
        request (MessageSend): 消息发送请求
        db (Session): 数据库会话
        llm (BaseLLM): LLM 实例
    
    返回:
        StreamingResponse: SSE 流式响应
    """
    logger.info(
        "收到流式消息请求",
        conversation_id=request.conversation_id,
        content_length=len(request.content)
    )
    
    # 初始化服务
    conv_service = ConversationService(db)
    msg_service = MessageService(db)
    
    # 检查会话是否存在
    conversation = conv_service.get_conversation(request.conversation_id)
    if not conversation:
        from app.utils.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=request.conversation_id
        )
    
    # 保存用户消息
    user_message = msg_service.create_message(
        conversation_id=request.conversation_id,
        role="user",
        content=request.content
    )
    
    # 构建上下文
    system_prompt = config.get("prompts.system", "你是一个智能助手。")
    recent_messages = msg_service.get_recent_messages(request.conversation_id, limit=20)
    
    # 暂时简化处理，直接构建消息列表
    llm_messages = []
    if system_prompt:
        llm_messages.append({"role": "system", "content": system_prompt})
    
    for msg in recent_messages:
        llm_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # 流式生成函数
    async def generate():
        """生成流式响应"""
        # ⚠️ 暂时用 SimpleAgent，因为 ToolAgent 的流式支持还需要实现
        agent = SimpleAgent(llm)
        response_stream = agent.run(llm_messages, stream=True)
        
        full_content = ""
        
        # 流式输出
        for chunk in response_stream:
            full_content += chunk
            # SSE 格式：data: 内容\n\n
            yield f"data: {chunk}\n\n"
        
        # 保存助手消息
        msg_service.create_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=full_content,
            model_provider=llm.get_model_info()["provider"],
            model_name=llm.model_name
        )
        
        logger.info(
            "流式消息处理完成",
            conversation_id=request.conversation_id,
            response_length=len(full_content)
        )
    
    # 返回流式响应
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def requires_planning(message: str) -> bool:
    """
    判断消息是否需要任务规划
    
    参数:
        message: 用户消息
    
    返回:
        bool: 是否需要规划
    """
    planning_keywords = [
        "帮我", "请帮我", "帮我做", "帮我完成", "帮我实现",
        "重构", "优化", "改进", "修复", "调试",
        "开发", "编写", "创建", "构建", "设计",
        "分析", "研究", "调查", "检查", "测试",
        "部署", "发布", "上线", "配置", "设置"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in planning_keywords)


@router.post("/plan", summary="任务规划")
async def plan_task(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    任务规划接口
    
    参数:
        request (MessageSend): 消息发送请求
        db (Session): 数据库会话
        llm (BaseLLM): LLM 实例
    
    返回:
        SuccessResponse: 规划结果
    """
    logger.info(
        "收到任务规划请求",
        conversation_id=request.conversation_id,
        content_length=len(request.content)
    )
    
    # 初始化服务
    conv_service = ConversationService(db)
    msg_service = MessageService(db)
    task_dao = TaskDAO(db)
    planning_service = PlanningService(task_dao, tool_manager)
    
    # 检查会话是否存在
    conversation = conv_service.get_conversation(request.conversation_id)
    if not conversation:
        from app.utils.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=request.conversation_id
        )
    
    # 保存用户消息
    user_message = msg_service.create_message(
        conversation_id=request.conversation_id,
        role="user",
        content=request.content
    )
    
    try:
        # 执行任务规划
        result = await planning_service.plan_and_execute(
            request=request.content,
            conversation_id=request.conversation_id,
            user_id=conversation.user_id
        )
        
        # 构建响应消息
        if result.success:
            response_content = f"任务规划完成！\n\n执行结果：{result.message}\n\n执行时间：{result.execution_time:.2f}秒\n\n任务统计：\n"
            for task_name, task_result in result.task_results.items():
                response_content += f"- {task_name}: {'✅ 成功' if task_result.get('success', False) else '❌ 失败'}\n"
        else:
            response_content = f"任务规划失败：{result.message}"
        
        # 保存助手消息
        assistant_message = msg_service.create_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=response_content,
            model_provider=llm.get_model_info()["provider"],
            model_name=llm.model_name
        )
        
        logger.info(
            "任务规划完成",
            conversation_id=request.conversation_id,
            success=result.success,
            execution_time=result.execution_time
        )
        
        # 构建响应
        response_data = ChatResponse(
            conversation_id=request.conversation_id,
            user_message=MessageResponse.model_validate(user_message),
            assistant_message=MessageResponse.model_validate(assistant_message)
        )
        
        return SuccessResponse.create(
            data=response_data,
            message="任务规划完成" if result.success else "任务规划失败"
        )
        
    except Exception as e:
        logger.error(f"任务规划失败: {str(e)}")
        
        # 保存错误消息
        error_message = msg_service.create_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=f"任务规划失败：{str(e)}",
            model_provider=llm.get_model_info()["provider"],
            model_name=llm.model_name
        )
        
        response_data = ChatResponse(
            conversation_id=request.conversation_id,
            user_message=MessageResponse.model_validate(user_message),
            assistant_message=MessageResponse.model_validate(error_message)
        )
        
        return SuccessResponse.create(
            data=response_data,
            message="任务规划失败"
        )


@router.post("/plan/stream", summary="任务规划（流式）")
async def plan_task_stream(
    request: MessageSend,
    db: Session = Depends(get_database),
    llm: BaseLLM = Depends(get_llm_instance)
):
    """
    任务规划接口（流式）
    
    参数:
        request (MessageSend): 消息发送请求
        db (Session): 数据库会话
        llm (BaseLLM): LLM 实例
    
    返回:
        StreamingResponse: 流式规划进度
    """
    logger.info(
        "收到流式任务规划请求",
        conversation_id=request.conversation_id,
        content_length=len(request.content)
    )
    
    # 初始化服务
    conv_service = ConversationService(db)
    msg_service = MessageService(db)
    task_dao = TaskDAO(db)
    planning_service = PlanningService(task_dao, tool_manager)
    
    # 检查会话是否存在
    conversation = conv_service.get_conversation(request.conversation_id)
    if not conversation:
        from app.utils.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(
            "会话不存在",
            resource_type="Conversation",
            resource_id=request.conversation_id
        )
    
    # 保存用户消息
    user_message = msg_service.create_message(
        conversation_id=request.conversation_id,
        role="user",
        content=request.content
    )
    
    # 流式生成函数
    async def generate():
        """生成流式规划进度"""
        try:
            # 流式执行任务规划
            async for progress in planning_service.plan_and_execute_stream(
                request=request.content,
                conversation_id=request.conversation_id,
                user_id=conversation.user_id
            ):
                # 发送进度信息
                progress_data = {
                    "type": progress["type"],
                    "message": progress["message"],
                    "timestamp": progress["timestamp"]
                }
                
                if "data" in progress:
                    progress_data["data"] = progress["data"]
                
                yield f"data: {progress_data}\n\n"
            
            # 发送完成消息
            yield f"data: {{'type': 'final', 'message': '任务规划完成', 'timestamp': '{datetime.utcnow().isoformat()}'}}\n\n"
            
        except Exception as e:
            logger.error(f"流式任务规划失败: {str(e)}")
            yield f"data: {{'type': 'error', 'message': '任务规划失败: {str(e)}', 'timestamp': '{datetime.utcnow().isoformat()}'}}\n\n"
    
    # 返回流式响应
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

