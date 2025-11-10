"""
文件名: logging_middleware.py
功能: 请求日志中间件，记录所有 HTTP 请求
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    功能：
    - 记录所有 HTTP 请求和响应
    - 生成唯一的请求ID
    - 记录请求耗时
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求
        
        参数:
            request (Request): FastAPI 请求对象
            call_next (Callable): 下一个处理器
        
        返回:
            Response: 响应对象
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id  # 保存到请求状态中
        
        # 记录请求开始
        start_time = time.time()
        
        logger.info(
            "收到请求",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算耗时
            duration = time.time() - start_time
            
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            
            # 记录响应
            logger.info(
                "请求完成",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2)
            )
            
            return response
            
        except Exception as e:
            # 计算耗时
            duration = time.time() - start_time
            
            # 记录错误
            logger.error(
                "请求处理异常",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                exc_info=True
            )
            
            raise

