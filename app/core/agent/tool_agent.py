"""
文件名: tool_agent.py
功能: 工具调用 Agent，使用 LangGraph 预构建 Agent（基于开源框架）
"""

from typing import List, Dict, Any, Iterator, Union

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.agent.base import BaseAgent
from app.core.llm.base import BaseLLM
from app.tools.manager import ToolManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolAgent(BaseAgent):
    """
    工具调用 Agent（基于 LangGraph）
    
    功能：
    - 使用 LangGraph create_react_agent（预构建的开源 Agent）
    - 支持工具调用（使用 LangChain Tools）
    - 自动决策是否需要调用工具
    - 支持多轮工具调用
    
    这个 Agent 完全基于 LangGraph 开源框架！
    """
    
    def __init__(self, llm: BaseLLM, tool_manager: ToolManager):
        """
        初始化工具 Agent
        
        参数:
            llm (BaseLLM): LLM 实例
            tool_manager (ToolManager): 工具管理器
        """
        super().__init__(llm)
        self.tool_manager = tool_manager  # 工具管理器
        
        # 获取所有工具（LangChain 格式）
        self.tools = tool_manager.get_all_tools()
        
        # 使用 LangGraph 的 create_react_agent 创建 Agent（开源代码）
        self.agent_executor = create_react_agent(
            model=self.llm.client,  # LangChain ChatOpenAI 实例
            tools=self.tools  # 工具列表
        )
        
        self.logger.info(
            "ToolAgent 初始化成功（使用 LangGraph create_react_agent）",
            tool_count=len(self.tools)
        )
    
    def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        运行 Agent（使用 LangGraph create_react_agent）
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            stream (bool): 是否流式输出（暂不支持）
            **kwargs: 其他参数
        
        返回:
            str: Agent 回复
        """
        self.logger.info(
            "ToolAgent 开始运行（LangGraph create_react_agent）",
            message_count=len(messages),
            tool_count=len(self.tools)
        )
        
        # 转换消息格式为 LangChain BaseMessage
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # 执行 LangGraph Agent（完全使用开源代码）
        final_state = self.agent_executor.invoke({"messages": langchain_messages})
        
        # 提取最终回复
        final_messages = final_state["messages"]
        last_message = final_messages[-1]
        
        response_content = last_message.content
        
        self.logger.info(
            "ToolAgent 运行完成（LangGraph）",
            response_length=len(response_content),
            total_steps=len(final_messages)
        )
        
        return response_content

