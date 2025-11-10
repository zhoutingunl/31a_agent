"""
文件名: base.py
功能: LLM 基类接口，定义统一的 LLM 调用规范
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Iterator, Optional, Union

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseLLM(ABC):
    """
    LLM 基类
    
    定义所有 LLM 适配器的统一接口。
    所有 LLM 实现（DeepSeek、Ollama、千帆等）都应继承此类。
    
    属性:
        model_name (str): 模型名称
        temperature (float): 温度参数（控制随机性）
        max_tokens (int): 最大生成Token数
        timeout (int): 超时时间（秒）
    """
    
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60
    ):
        """
        初始化 LLM
        
        参数:
            model_name (str): 模型名称
            temperature (float): 温度参数
            max_tokens (int): 最大生成Token数
            timeout (int): 超时时间（秒）
        """
        self.model_name = model_name  # 模型名称
        self.temperature = temperature  # 温度参数
        self.max_tokens = max_tokens  # 最大Token数
        self.timeout = timeout  # 超时时间
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")  # 日志记录器
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        对话接口（抽象方法）
        
        参数:
            messages (List[Dict[str, str]]): 消息列表，格式：[{"role": "user", "content": "..."}]
            stream (bool): 是否流式输出
            **kwargs: 其他参数
        
        返回:
            str | Iterator[str]: 非流式返回字符串，流式返回迭代器
        """
        pass
    
    @abstractmethod
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        带工具调用的对话接口（抽象方法）
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            tools (List[Dict[str, Any]]): 工具定义列表
            **kwargs: 其他参数
        
        返回:
            Dict[str, Any]: 包含回复和工具调用的字典
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        返回:
            Dict[str, Any]: 模型信息字典
        """
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "provider": self.__class__.__name__.replace("LLM", "").lower()
        }
    
    def __repr__(self) -> str:
        """返回 LLM 对象的字符串表示"""
        return f"<{self.__class__.__name__}(model={self.model_name})>"

