"""
文件名: manager.py
功能: 工具管理器，负责工具的注册、查询和执行
"""

from typing import Dict, List, Any, Optional

from langchain_core.tools import BaseTool

from app.utils.logger import get_logger
from app.utils.exceptions import ToolExecutionError, ValidationError

logger = get_logger(__name__)


class ToolManager:
    """
    工具管理器类
    
    功能：
    - 注册和管理所有工具
    - 查询可用工具列表
    - 执行工具调用
    - 验证工具参数
    
    属性:
        _tools (Dict[str, BaseTool]): 工具注册表（工具名 -> 工具实例）
    """
    
    def __init__(self):
        """初始化工具管理器"""
        self._tools: Dict[str, BaseTool] = {}  # 工具注册表
        self.logger = get_logger(__name__)  # 日志记录器
        
        self.logger.info("工具管理器初始化")
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具
        
        参数:
            tool (BaseTool): 工具实例
        
        异常:
            ValidationError: 工具名称重复时抛出
        """
        if tool.name in self._tools:
            raise ValidationError(
                f"工具名称重复: {tool.name}",
                details={"tool_name": tool.name}
            )
        
        self._tools[tool.name] = tool
        
        self.logger.info(
            "工具注册成功",
            tool_name=tool.name,
            tool_description=tool.description
        )
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        参数:
            tool_name (str): 工具名称
        
        返回:
            Optional[BaseTool]: 工具实例，如果不存在返回 None
        """
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        获取所有工具实例（LangChain 格式）
        
        返回:
            List[BaseTool]: 工具实例列表
        """
        return list(self._tools.values())
    
    def get_tool_list(self) -> List[Dict[str, Any]]:
        """
        获取工具列表信息
        
        返回:
            List[Dict[str, Any]]: 工具信息列表
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema() if tool.args_schema else {}
            }
            for tool in self._tools.values()
        ]
    
    def execute_tool(self, tool_name: str, **params) -> Any:
        """
        执行工具
        
        参数:
            tool_name (str): 工具名称
            **params: 工具参数
        
        返回:
            Any: 工具执行结果
        
        异常:
            ToolExecutionError: 工具不存在或执行失败时抛出
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            raise ToolExecutionError(
                f"工具不存在: {tool_name}",
                tool_name=tool_name,
                details={"available_tools": list(self._tools.keys())}
            )
        
        try:
            # 执行工具
            result = tool._run(**params)
            return result
            
        except Exception as e:
            raise ToolExecutionError(
                f"工具执行失败: {str(e)}",
                tool_name=tool_name,
                details={"params": params, "error": str(e)}
            )
    
    def __len__(self) -> int:
        """返回已注册工具的数量"""
        return len(self._tools)
    
    def __repr__(self) -> str:
        """返回工具管理器的字符串表示"""
        return f"<ToolManager: {len(self._tools)} tools registered>"


# 全局工具管理器实例
tool_manager = ToolManager()

