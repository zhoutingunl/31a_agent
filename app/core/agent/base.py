"""
文件名: base.py
功能: Agent 基类接口

提供所有Agent的统一基类，确保LLM实例的正确传递和日志记录
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Iterator, Union, Optional

from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Agent 基类
    
    定义所有 Agent 的统一接口，确保LLM实例的正确传递。
    
    属性:
        llm: LLM 实例
        logger: 日志记录器
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None):
        """
        初始化 Agent
        
        参数:
            llm: LLM 实例（可选，某些Agent可能不需要直接使用LLM）
        """
        self.llm = llm  # LLM 实例
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")  # 日志记录器
    
    @abstractmethod
    def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        运行 Agent（抽象方法）
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            stream (bool): 是否流式输出
            **kwargs: 其他参数
        
        返回:
            Union[str, Iterator[str]]: 回复内容或流式迭代器
        """
        pass

