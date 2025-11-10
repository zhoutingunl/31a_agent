"""
文件名: deps.py
功能: FastAPI 依赖注入函数
"""

from typing import Generator

from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.llm.base import BaseLLM
from app.core.llm.factory import create_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 直接使用 get_db 作为依赖注入函数
get_database = get_db


def get_llm_instance() -> BaseLLM:
    """
    获取 LLM 实例（依赖注入）
    
    根据配置创建默认的 LLM 实例。
    
    Returns:
        BaseLLM: LLM 实例
    
    示例:
        >>> from fastapi import Depends
        >>> def endpoint(llm: BaseLLM = Depends(get_llm_instance)):
        >>>     response = llm.chat([{"role": "user", "content": "Hello"}])
    """
    return create_llm()

