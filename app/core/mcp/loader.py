"""
文件名: loader.py
功能: MCP 配置加载器

从 mcp.json 加载配置并创建工具
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.mcp.client import MCPClient
from app.core.mcp.manager import mcp_manager
from app.tools.mcp.wrapper import MCPToolWrapper
from app.utils.logger import get_logger

logger = get_logger(__name__)


def load_mcp_config(config_path: Optional[str] = None) -> Dict:
    """
    加载 MCP 配置文件
    
    参数：
        config_path (Optional[str]): 配置文件路径，默认为项目根目录下的 mcp.json
    
    返回：
        Dict: MCP 配置
    """
    if config_path is None:
        # 默认路径：项目根目录/mcp.json
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "mcp.json"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logger.warning(f"MCP 配置文件不存在: {config_path}")
        return {"mcpServers": {}}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info(
            "MCP 配置加载成功",
            path=str(config_path),
            servers=list(config.get("mcpServers", {}).keys())
        )
        
        return config
        
    except Exception as e:
        logger.error(f"加载 MCP 配置失败: {config_path}", error=str(e))
        return {"mcpServers": {}}


def create_mcp_clients(config: Dict) -> List[MCPClient]:
    """
    根据配置创建 MCP 客户端
    
    参数：
        config (Dict): MCP 配置
    
    返回：
        List[MCPClient]: 客户端列表
    """
    clients = []
    servers = config.get("mcpServers", {})
    
    for server_name, server_config in servers.items():
        try:
            client = MCPClient(
                server_name=server_name,
                command=server_config.get("command", "npx"),
                args=server_config.get("args", []),
                env=server_config.get("env", {})
            )
            
            clients.append(client)
            mcp_manager.add_client(client)
            
            logger.info(f"创建 MCP 客户端: {server_name}")
            
        except Exception as e:
            logger.error(f"创建 MCP 客户端失败: {server_name}", error=str(e))
    
    return clients


def create_mcp_tools(config_path: Optional[str] = None) -> List[MCPToolWrapper]:
    """
    从配置文件创建所有 MCP 工具
    
    这是最核心的函数！它会：
    1. 加载 mcp.json 配置
    2. 连接到所有 MCP 服务器
    3. 发现所有可用工具
    4. 包装成 AgentTool
    
    参数：
        config_path (Optional[str]): 配置文件路径
    
    返回：
        List[MCPToolWrapper]: 工具列表
    """
    try:
        # 1. 加载配置
        config = load_mcp_config(config_path)
        
        # 2. 创建客户端
        clients = create_mcp_clients(config)
        
        if not clients:
            logger.warning("未发现任何 MCP 服务器")
            return []
        
        # 3. 发现所有工具
        all_mcp_tools = mcp_manager.list_all_tools()
        
        if not all_mcp_tools:
            logger.warning("未发现任何 MCP 工具")
            return []
        
        # 4. 包装成 AgentTool
        agent_tools = []
        for mcp_tool in all_mcp_tools:
            try:
                wrapper = MCPToolWrapper.from_mcp_tool(mcp_tool)
                agent_tools.append(wrapper)
                
                logger.info(
                    f"包装 MCP 工具: {wrapper.name}",
                    server=mcp_tool.get("_server_name")
                )
                
            except Exception as e:
                logger.warning(
                    f"包装 MCP 工具失败: {mcp_tool.get('name')}",
                    error=str(e)
                )
        
        logger.info(f"成功创建 {len(agent_tools)} 个 MCP 工具")
        
        return agent_tools
        
    except Exception as e:
        logger.error("创建 MCP 工具失败", error=str(e))
        return []

