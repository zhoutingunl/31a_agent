"""
文件名: base.py
功能: Pydantic Schema 基类，提供统一的响应格式
"""

from typing import Generic, TypeVar, Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


# 定义泛型类型
T = TypeVar('T')


class ResponseBase(BaseModel, Generic[T]):
    """
    统一响应格式基类
    
    所有 API 响应都应使用此格式，保证一致性。
    
    字段:
        code (int): 响应代码（0-成功，非0-失败）
        message (str): 响应消息
        data (T): 响应数据
    """
    
    code: int = Field(default=0, description="响应代码：0-成功，非0-失败")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "code": 0,
                "message": "success",
                "data": {}
            }
        }


class SuccessResponse(ResponseBase[T], Generic[T]):
    """
    成功响应
    
    用于返回成功的 API 响应。
    """
    
    @classmethod
    def create(cls, data: T, message: str = "操作成功"):
        """
        创建成功响应
        
        参数:
            data: 响应数据
            message (str): 响应消息
        
        返回:
            SuccessResponse: 成功响应对象
        """
        return cls(code=0, message=message, data=data)


class ErrorResponse(BaseModel):
    """
    错误响应
    
    用于返回错误的 API 响应。
    
    字段:
        code (int): 错误代码
        message (str): 错误消息
        details (dict): 错误详情
    """
    
    code: int = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="错误详情")
    
    @classmethod
    def create(cls, code: int, message: str, details: dict = None):
        """
        创建错误响应
        
        参数:
            code (int): 错误代码
            message (str): 错误消息
            details (dict): 错误详情
        
        返回:
            ErrorResponse: 错误响应对象
        """
        return cls(code=code, message=message, details=details)
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "code": 400,
                "message": "请求参数错误",
                "details": {"field": "user_id", "error": "不能为空"}
            }
        }


class PaginationMeta(BaseModel):
    """
    分页元信息
    
    字段:
        total (int): 总记录数
        page (int): 当前页码
        page_size (int): 每页大小
        total_pages (int): 总页数
    """
    
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")
    
    @classmethod
    def create(cls, total: int, page: int, page_size: int):
        """
        创建分页元信息
        
        参数:
            total (int): 总记录数
            page (int): 当前页码
            page_size (int): 每页大小
        
        返回:
            PaginationMeta: 分页元信息对象
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

