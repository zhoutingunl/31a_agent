"""
文件名: manager.py
功能: MCP 服务器管理器

管理多个 MCP 客户端连接
"""

from typing import Dict, List, Optional, Any
from app.core.mcp.client import MCPClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MCPManager:
    """
    MCP 管理器
    
    功能：
    - 管理多个 MCP 客户端
    - 统一的工具调用接口
    - 自动重连
    """
    
    def __init__(self):
        """初始化 MCP 管理器"""
        self.clients: Dict[str, MCPClient] = {}
        logger.info("MCP 管理器已初始化")
    
    def add_client(self, client: MCPClient):
        """
        添加 MCP 客户端
        
        参数：
            client (MCPClient): MCP 客户端实例
        """
        self.clients[client.server_name] = client
        logger.info(f"添加 MCP 客户端: {client.server_name}")
    
    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """
        获取 MCP 客户端
        
        参数：
            server_name (str): 服务器名称
        
        返回：
            Optional[MCPClient]: 客户端实例
        """
        return self.clients.get(server_name)
    
    def list_all_tools(self) -> List[Dict]:
        """
        列出所有 MCP 工具
        
        返回：
            List[Dict]: 所有工具列表（包含 server_name 字段）
        """
        all_tools = []
        
        for server_name, client in self.clients.items():
            try:
                tools = client.list_tools()
                # 为每个工具添加 server_name 字段
                for tool in tools:
                    tool["_server_name"] = server_name
                all_tools.extend(tools)
            except Exception as e:
                logger.warning(f"列出工具失败: {server_name}", error=str(e))
        
        logger.info(f"发现 {len(all_tools)} 个 MCP 工具")
        return all_tools
    
    def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Any:
        """
        调用 MCP 工具
        
        参数：
            server_name (str): 服务器名称
            tool_name (str): 工具名称
            arguments (Dict): 工具参数
        
        返回：
            Any: 工具执行结果
        """
        client = self.get_client(server_name)
        if not client:
            raise ValueError(f"MCP 服务器不存在: {server_name}")
        
        return client.call_tool(tool_name, arguments)
    
    def stop_all(self):
        """停止所有 MCP 客户端"""
        for server_name, client in self.clients.items():
            try:
                client.stop()
            except Exception as e:
                logger.warning(f"停止 MCP 客户端失败: {server_name}", error=str(e))
        
        logger.info("所有 MCP 客户端已停止")
    
    def __del__(self):
        """析构函数"""
        self.stop_all()


# 全局 MCP 管理器实例
mcp_manager = MCPManager()

