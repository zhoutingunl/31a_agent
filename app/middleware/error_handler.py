"""
文件名: error_handler.py
功能: 全局异常处理中间件
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger
from app.utils.exceptions import (
    AgentException,
    ValidationError,
    ResourceNotFoundError,
    DatabaseError,
    LLMError,
    ToolExecutionError,
    ConfigError
)

logger = get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    
    捕获所有未处理的异常并返回统一的错误响应。
    
    参数:
        request (Request): 请求对象
        exc (Exception): 异常对象
    
    返回:
        JSONResponse: JSON 错误响应
    """
    # 获取请求ID（如果有）
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 根据异常类型返回不同的状态码和消息
    if isinstance(exc, ValidationError):
        status_code = 400
        error_dict = exc.to_dict()
    elif isinstance(exc, ResourceNotFoundError):
        status_code = 404
        error_dict = exc.to_dict()
    elif isinstance(exc, DatabaseError):
        status_code = 500
        error_dict = exc.to_dict()
    elif isinstance(exc, LLMError):
        status_code = 503
        error_dict = exc.to_dict()
    elif isinstance(exc, ToolExecutionError):
        status_code = 500
        error_dict = exc.to_dict()
    elif isinstance(exc, ConfigError):
        status_code = 500
        error_dict = exc.to_dict()
    elif isinstance(exc, AgentException):
        status_code = 500
        error_dict = exc.to_dict()
    else:
        # 未知异常
        status_code = 500
        error_dict = {
            "error": "InternalServerError",
            "message": "服务器内部错误",
            "error_code": "INTERNAL_ERROR",
            "details": {}
        }
        
        # 记录未知异常的详细信息
        logger.error(
            "未捕获的异常",
            request_id=request_id,
            error_type=type(exc).__name__,
            error=str(exc),
            exc_info=True
        )
    
    # 添加请求ID到错误响应
    error_dict["request_id"] = request_id
    
    # 记录异常（已知异常类型）
    if isinstance(exc, AgentException):
        logger.warning(
            "业务异常",
            request_id=request_id,
            error=error_dict["error"],
            error_message=error_dict["message"]  # 改名避免参数冲突
        )
    
    # 返回错误响应
    return JSONResponse(
        status_code=status_code,
        content=error_dict
    )

