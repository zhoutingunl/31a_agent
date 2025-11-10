"""
文件名: wrapper.py
功能: MCP 工具包装器

将 MCP 工具包装成 AgentTool
"""

from typing import Type, Dict, Any
from pydantic import BaseModel, Field, create_model

from app.tools.base import AgentTool, ToolInput
from app.core.mcp.manager import mcp_manager
from app.utils.logger import get_logger
from app.utils.exceptions import ToolExecutionError

logger = get_logger(__name__)


class MCPToolWrapper(AgentTool):
    """
    MCP 工具包装器
    
    将任何 MCP 工具动态包装成 AgentTool
    """
    
    # MCP 相关信息
    _server_name: str = ""  # MCP 服务器名称
    _mcp_tool_name: str = ""  # MCP 工具原始名称
    
    def __init__(self, server_name: str, mcp_tool: Dict[str, Any]):
        """
        初始化 MCP 工具包装器
        
        参数：
            server_name (str): MCP 服务器名称
            mcp_tool (Dict): MCP 工具定义
        """
        super().__init__()
        
        self._server_name = server_name
        self._mcp_tool_name = mcp_tool.get("name", "")
        
        # 设置工具属性
        object.__setattr__(self, 'name', self._format_tool_name(mcp_tool.get("name", "")))
        object.__setattr__(self, 'description', mcp_tool.get("description", "MCP 工具"))
        
        # 动态创建参数 Schema
        schema = self._create_input_schema(mcp_tool)
        object.__setattr__(self, 'args_schema', schema)
        
        logger.info(f"创建 MCP 工具包装器: {self.name}")
    
    def _format_tool_name(self, name: str) -> str:
        """
        格式化工具名称
        
        将 MCP 工具名称转换为 Agent 工具名称
        例如: mcp_mysql_query -> mysql_query
        
        参数：
            name (str): 原始名称
        
        返回：
            str: 格式化后的名称
        """
        # 如果名称已经有 mcp_ 前缀，保留它
        # 否则添加 mcp_ 前缀避免与现有工具冲突
        if not name.startswith("mcp_"):
            return f"mcp_{name}"
        return name
    
    def _create_input_schema(self, mcp_tool: Dict[str, Any]) -> Type[BaseModel]:
        """
        根据 MCP 工具定义动态创建 Pydantic Schema
        
        参数：
            mcp_tool (Dict): MCP 工具定义
        
        返回：
            Type[BaseModel]: Pydantic 模型类
        """
        input_schema = mcp_tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        # 动态创建字段
        fields = {}
        for prop_name, prop_def in properties.items():
            field_type = self._json_type_to_python(prop_def.get("type", "string"))
            field_desc = prop_def.get("description", "")
            
            # 判断是否必填
            if prop_name in required:
                fields[prop_name] = (field_type, Field(..., description=field_desc))
            else:
                default_value = prop_def.get("default")
                fields[prop_name] = (field_type, Field(default=default_value, description=field_desc))
        
        # 如果没有参数，创建一个空的 Schema
        if not fields:
            fields["dummy"] = (str, Field(default="", description="无参数"))
        
        # 动态创建 Pydantic 模型
        schema_name = f"{self._format_tool_name(mcp_tool.get('name', 'Tool'))}Input"
        return create_model(schema_name, **fields, __base__=ToolInput)
    
    def _json_type_to_python(self, json_type: str) -> type:
        """
        将 JSON Schema 类型转换为 Python 类型
        
        参数：
            json_type (str): JSON 类型
        
        返回：
            type: Python 类型
        """
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(json_type, str)
    
    def execute(self, **kwargs):
        """
        执行 MCP 工具
        
        参数：
            **kwargs: 工具参数
        
        返回：
            工具执行结果
        """
        # 移除 dummy 参数（如果存在）
        kwargs.pop("dummy", None)
        
        try:
            logger.info(
                f"调用 MCP 工具: {self._mcp_tool_name}",
                server=self._server_name,
                params=kwargs
            )
            
            # 调用 MCP 工具
            result = mcp_manager.call_tool(
                server_name=self._server_name,
                tool_name=self._mcp_tool_name,
                arguments=kwargs
            )
            
            logger.info(
                f"MCP 工具执行成功: {self._mcp_tool_name}",
                server=self._server_name
            )
            
            return {
                "success": True,
                "data": result,
                "server": self._server_name,
                "tool": self._mcp_tool_name,
                "message": f"MCP 工具 {self.name} 执行成功"
            }
            
        except Exception as e:
            logger.error(
                f"MCP 工具执行失败: {self._mcp_tool_name}",
                server=self._server_name,
                error=str(e)
            )
            raise ToolExecutionError(
                f"MCP 工具执行失败: {str(e)}",
                tool_name=self.name,
                details={
                    "server": self._server_name,
                    "mcp_tool": self._mcp_tool_name,
                    "error": str(e)
                }
            )
    
    @classmethod
    def from_mcp_tool(cls, mcp_tool: Dict[str, Any]) -> "MCPToolWrapper":
        """
        从 MCP 工具定义创建包装器
        
        参数：
            mcp_tool (Dict): MCP 工具定义（包含 _server_name 字段）
        
        返回：
            MCPToolWrapper: 包装器实例
        """
        server_name = mcp_tool.pop("_server_name", "unknown")
        return cls(server_name=server_name, mcp_tool=mcp_tool)

