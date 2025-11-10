"""
文件名: registry.py
功能: 统一的工具注册中心

在这里注册所有工具（包括自定义工具和 MCP 工具）
"""

from typing import List

from app.tools.manager import tool_manager
from app.core.mcp.loader import create_mcp_tools
from app.tools.base import AgentTool
from app.tools.powershell.powershell_tool import PowerShellTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


def register_custom_tools() -> List[AgentTool]:
    """
    注册自定义工具
    
    返回：
        List[AgentTool]: 自定义工具列表
    """
    custom_tools = [
        # PowerShell 工具
        PowerShellTool(),
        
        # 在这里添加更多自定义工具
        # FileReadTool(),
        # HTTPTool(),
    ]
    
    return custom_tools


def register_mcp_tools(mcp_config_path: str = None) -> List[AgentTool]:
    """
    注册 MCP 工具
    
    自动从 mcp.json 加载并注册所有 MCP 工具
    
    参数：
        mcp_config_path (str): MCP 配置文件路径（默认为 ~/.cursor/mcp.json）
    
    返回：
        List[AgentTool]: MCP 工具列表
    """
    try:
        mcp_tools = create_mcp_tools(mcp_config_path)
        logger.info(f"加载了 {len(mcp_tools)} 个 MCP 工具")
        return mcp_tools
    except Exception as e:
        logger.error("加载 MCP 工具失败", error=str(e))
        return []


def register_all_tools(enable_mcp: bool = True, mcp_config_path: str = None):
    """
    注册所有工具
    
    参数：
        enable_mcp (bool): 是否启用 MCP 工具（默认 True）
        mcp_config_path (str): MCP 配置文件路径
    """
    all_tools = []
    
    # 1. 注册自定义工具
    logger.info("开始注册自定义工具...")
    custom_tools = register_custom_tools()
    all_tools.extend(custom_tools)
    
    # 2. 注册 MCP 工具
    if enable_mcp:
        logger.info("开始注册 MCP 工具...")
        mcp_tools = register_mcp_tools(mcp_config_path)
        all_tools.extend(mcp_tools)
    else:
        logger.info("MCP 工具已禁用")
    
    # 3. 统一注册到 tool_manager
    success_count = 0
    for tool in all_tools:
        try:
            tool_manager.register_tool(tool)
            logger.info(f"✓ {tool.name} 注册成功")
            success_count += 1
        except Exception as e:
            logger.warning(f"✗ {tool.name} 注册失败: {str(e)}")
    
    logger.info(
        f"工具注册完成",
        total=len(all_tools),
        success=success_count,
        failed=len(all_tools) - success_count
    )
    
    return tool_manager

