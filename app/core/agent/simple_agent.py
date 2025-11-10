"""
文件名: simple_agent.py
功能: 简单 Agent，直接调用 LLM（无工具）
"""

from typing import List, Dict, Any, Iterator, Union

from app.core.agent.base import BaseAgent
from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleAgent(BaseAgent):
    """
    简单 Agent 类
    
    功能：
    - 直接调用 LLM 进行对话
    - 不使用工具
    - 适用于简单的问答场景
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化简单 Agent
        
        参数:
            llm (BaseLLM): LLM 实例
        """
        super().__init__(llm)
    
    def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        运行 Agent
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            stream (bool): 是否流式输出
            **kwargs: 其他参数
        
        返回:
            Union[str, Iterator[str]]: LLM 回复
        """
        self.logger.info(
            "SimpleAgent 开始处理",
            message_count=len(messages),
            stream=stream
        )
        
        # 直接调用 LLM
        response = self.llm.chat(messages, stream=stream, **kwargs)
        
        if not stream:
            self.logger.info(
                "SimpleAgent 处理完成",
                response_length=len(response) if response else 0
            )
        
        return response

