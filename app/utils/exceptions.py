"""
文件名: exceptions.py
功能: 自定义异常类，提供统一的异常处理机制
"""

from typing import Any, Dict, Optional


class AgentException(Exception):
    """
    Agent 通用异常基类
    
    所有自定义异常都应继承此类，便于统一捕获和处理。
    
    属性:
        message (str): 异常信息
        details (Dict[str, Any], optional): 异常详细信息
        error_code (str, optional): 错误代码
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message  # 异常信息
        self.details = details or {}  # 异常详细信息
        self.error_code = error_code  # 错误代码
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """将异常转换为字典格式，便于 API 返回"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ConfigError(AgentException):
    """
    配置错误异常
    
    当配置文件缺失、格式错误或必需配置项缺失时抛出。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            error_code="CONFIG_ERROR"
        )


class DatabaseError(AgentException):
    """
    数据库错误异常
    
    当数据库连接失败、查询错误或事务失败时抛出。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            error_code="DATABASE_ERROR"
        )


class LLMError(AgentException):
    """
    LLM 调用错误异常
    
    当 LLM API 调用失败、超时或返回错误时抛出。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            error_code="LLM_ERROR"
        )


class ToolExecutionError(AgentException):
    """
    工具执行错误异常
    
    当工具调用失败、参数错误或执行超时时抛出。
    
    属性:
        tool_name (str): 工具名称
    """
    
    def __init__(
        self,
        message: str,
        tool_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.tool_name = tool_name  # 工具名称
        super().__init__(
            message=message,
            details={**(details or {}), "tool_name": tool_name},
            error_code="TOOL_EXECUTION_ERROR"
        )


class ValidationError(AgentException):
    """
    数据验证错误异常
    
    当输入数据不符合预期格式或验证规则时抛出。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            error_code="VALIDATION_ERROR"
        )


class AuthenticationError(AgentException):
    """
    认证错误异常
    
    当用户认证失败或权限不足时抛出。
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            error_code="AUTHENTICATION_ERROR"
        )


class ResourceNotFoundError(AgentException):
    """
    资源未找到异常
    
    当请求的资源（如会话、消息）不存在时抛出。
    """
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Any,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details={
                **(details or {}),
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            error_code="RESOURCE_NOT_FOUND"
        )


class TimeoutError(AgentException):
    """
    超时错误异常
    
    当操作执行超时时抛出。
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            details={**(details or {}), "timeout_seconds": timeout_seconds},
            error_code="TIMEOUT_ERROR"
        )

