"""
文件名: deepseek.py
功能: DeepSeek LLM 适配器
"""

from typing import List, Dict, Any, Iterator, Union

from langchain_openai import ChatOpenAI

from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger
from app.utils.exceptions import LLMError

logger = get_logger(__name__)


class DeepSeekLLM(BaseLLM):
    """
    DeepSeek LLM 适配器
    
    使用 LangChain 的 ChatOpenAI 适配器调用 DeepSeek API。
    DeepSeek API 兼容 OpenAI 接口格式。
    
    属性:
        api_key (str): DeepSeek API Key
        base_url (str): DeepSeek API 地址
        client (ChatOpenAI): LangChain ChatOpenAI 客户端
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model_name: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60
    ):
        """
        初始化 DeepSeek LLM
        
        参数:
            api_key (str): DeepSeek API Key
            base_url (str): API 地址
            model_name (str): 模型名称
            temperature (float): 温度参数
            max_tokens (int): 最大Token数
            timeout (int): 超时时间
        """
        super().__init__(model_name, temperature, max_tokens, timeout)
        
        self.api_key = api_key  # API Key
        self.base_url = base_url  # API 地址
        
        # 创建 LangChain ChatOpenAI 客户端
        self.client = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        self.logger.info(
            "DeepSeek LLM 初始化成功",
            model=model_name,
            base_url=base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        对话接口
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            stream (bool): 是否流式输出
            **kwargs: 其他参数
        
        返回:
            str | Iterator[str]: 回复内容或流式迭代器
        
        异常:
            LLMError: LLM 调用失败时抛出
        """
        try:
            self.logger.debug(
                "调用 DeepSeek API",
                message_count=len(messages),
                stream=stream
            )
            
            if stream:
                # 流式调用
                response = self.client.stream(messages)
                return self._stream_response(response)
            else:
                # 非流式调用
                response = self.client.invoke(messages)
                content = response.content
                
                self.logger.debug(
                    "DeepSeek API 调用成功",
                    response_length=len(content)
                )
                
                return content
                
        except Exception as e:
            self.logger.error(
                "DeepSeek API 调用失败",
                error=str(e),
                exc_info=True
            )
            raise LLMError(
                f"DeepSeek API 调用失败: {str(e)}",
                details={
                    "model": self.model_name,
                    "message_count": len(messages),
                    "error": str(e)
                }
            )
    
    def _stream_response(self, response) -> Iterator[str]:
        """
        处理流式响应
        
        参数:
            response: LangChain 流式响应对象
        
        Yields:
            str: 每个 Token 的内容
        """
        try:
            for chunk in response:
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            self.logger.error(
                "流式响应处理失败",
                error=str(e),
                exc_info=True
            )
            raise LLMError(
                f"流式响应处理失败: {str(e)}",
                details={"error": str(e)}
            )
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        带工具调用的对话接口
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            tools (List[Dict[str, Any]]): 工具定义列表
            **kwargs: 其他参数
        
        返回:
            Dict[str, Any]: 包含回复和工具调用的字典
        """
        try:
            self.logger.debug(
                "调用 DeepSeek API（带工具）",
                message_count=len(messages),
                tool_count=len(tools)
            )
            
            # 绑定工具到 LLM
            llm_with_tools = self.client.bind_tools(tools)
            
            # 调用 LLM
            response = llm_with_tools.invoke(messages)
            
            # 解析响应
            result = {
                "content": response.content,
                "tool_calls": []
            }
            
            # 提取工具调用
            if hasattr(response, 'tool_calls') and response.tool_calls:
                result["tool_calls"] = [
                    {
                        "name": tool_call.get("name"),
                        "args": tool_call.get("args", {})
                    }
                    for tool_call in response.tool_calls
                ]
            
            self.logger.debug(
                "DeepSeek API 调用成功（带工具）",
                tool_call_count=len(result["tool_calls"])
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "DeepSeek API 调用失败（带工具）",
                error=str(e),
                exc_info=True
            )
            raise LLMError(
                f"DeepSeek API 调用失败: {str(e)}",
                details={
                    "model": self.model_name,
                    "tool_count": len(tools),
                    "error": str(e)
                }
            )

