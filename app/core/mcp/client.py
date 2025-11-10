"""
文件名: client.py
功能: MCP 客户端，用于连接和调用 MCP 服务器

MCP (Model Context Protocol) 客户端实现
支持：
- 自动发现 MCP 服务器
- 动态加载工具
- 调用 MCP 工具
"""

import json
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    MCP 客户端
    
    功能：
    - 连接到 MCP 服务器
    - 列出可用工具
    - 调用工具
    """
    
    def __init__(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        """
        初始化 MCP 客户端
        
        参数：
            server_name (str): 服务器名称
            command (str): 启动命令
            args (List[str]): 命令参数
            env (Optional[Dict[str, str]]): 环境变量
        """
        self.server_name = server_name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self.tools_cache: Optional[List[Dict]] = None
        
        logger.info(f"初始化 MCP 客户端: {server_name}")
    
    def start(self):
        """启动 MCP 服务器进程"""
        try:
            import os
            env = os.environ.copy()
            env.update(self.env)
            
            # 确保 Node.js 路径在环境变量中
            # 优先级：mcp.json 中的 env 配置 > .env 文件 > 系统环境变量
            
            # 1. 获取系统环境变量
            system_path = os.environ.get('PATH', '')
            system_node_home = os.environ.get('NODE_HOME') or os.environ.get('NODEJS_HOME')
            
            # 2. 获取 .env 文件中的环境变量（通过 os.environ，因为 load_dotenv() 已经加载）
            dotenv_path = os.environ.get('PATH', '')
            dotenv_node_home = os.environ.get('NODE_HOME') or os.environ.get('NODEJS_HOME')
            
            # 3. 获取 mcp.json 中的 env 配置
            mcp_env_path = env.get('PATH', '')
            mcp_node_home = env.get('NODE_HOME') or env.get('NODEJS_HOME')
            
            # 4. 按优先级合并 PATH
            # 优先级：mcp.json env > .env > 系统环境变量
            final_path = mcp_env_path or dotenv_path or system_path
            env['PATH'] = final_path
            
            # 5. 如果命令是 npx，按优先级查找 Node.js 路径
            command_to_use = self.command
            if self.command == 'npx':
                # 按优先级查找 NODE_HOME
                node_home = mcp_node_home or dotenv_node_home or system_node_home
                
                if node_home and os.path.exists(node_home):
                    # 使用找到的 Node.js 路径
                    npx_paths = [
                        os.path.join(node_home, 'npx.cmd'),
                        os.path.join(node_home, 'npx'),
                    ]
                else:
                    # 使用常见的默认路径
                    npx_paths = [
                        r'D:\java\tool\node22\npx.cmd',
                        r'D:\java\tool\node22\npx',
                        'npx.cmd',
                        'npx'
                    ]
                
                for npx_path in npx_paths:
                    if os.path.exists(npx_path) or npx_path in ['npx.cmd', 'npx']:
                        command_to_use = npx_path
                        break
            
            # 调试信息：记录 PATH 设置
            logger.debug(f"MCP 客户端 PATH 设置: {env.get('PATH', '')[:200]}...")
            logger.debug(f"使用命令: {command_to_use}")
            
            self.process = subprocess.Popen(
                [command_to_use] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='ignore'  # 忽略编码错误
            )
            
            logger.info(f"MCP 服务器已启动: {self.server_name}")
            
        except Exception as e:
            self.start_failed = True
            logger.error(
                f"启动 MCP 服务器失败: {self.server_name}",
                error=str(e),
                command=self.command,
                args=self.args,
                env_keys=list(self.env.keys()) if self.env else []
            )
            # 不再抛出异常，而是标记为失败
    
    def stop(self):
        """停止 MCP 服务器进程"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"MCP 服务器已停止: {self.server_name}")
            except Exception as e:
                logger.warning(f"停止 MCP 服务器失败: {self.server_name}", error=str(e))
                if self.process:
                    self.process.kill()
    
    def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """
        发送 JSON-RPC 请求
        
        参数：
            method (str): 方法名
            params (Optional[Dict]): 参数
        
        返回：
            Dict: 响应结果
        """
        if not self.process or self.process.poll() is not None:
            self.start()
        
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # 发送请求
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # 读取响应，可能需要读取多行直到找到 JSON
            response_line = None
            max_attempts = 10  # 最多尝试读取 10 行
            
            for attempt in range(max_attempts):
                line = self.process.stdout.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                    
                # 记录原始响应用于调试
                logger.debug(f"MCP 原始响应 (尝试 {attempt + 1}): {line}")
                
                # 尝试解析为 JSON
                try:
                    response = json.loads(line)
                    response_line = line
                    break
                except json.JSONDecodeError:
                    # 如果不是 JSON，继续读取下一行
                    logger.debug(f"跳过非 JSON 行: {line}")
                    continue
            
            if response_line is None:
                # 读取错误输出以获取更多信息
                stderr_output = self.process.stderr.read() if self.process.stderr else "无错误输出"
                raise Exception(f"未收到有效 JSON 响应。错误输出: {stderr_output}")
            
            if "error" in response:
                raise Exception(f"MCP 错误: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"MCP 请求失败: {method}", error=str(e))
            raise
    
    def list_tools(self) -> List[Dict]:
        """
        列出所有可用工具
        
        返回：
            List[Dict]: 工具列表
        """
        if self.tools_cache is not None:
            return self.tools_cache
        
        try:
            result = self._send_request("tools/list")
            tools = result.get("tools", [])
            self.tools_cache = tools
            
            logger.info(
                f"发现 MCP 工具",
                server=self.server_name,
                count=len(tools)
            )
            
            return tools
            
        except Exception as e:
            logger.error(f"列出 MCP 工具失败: {self.server_name}", error=str(e))
            return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用 MCP 工具
        
        参数：
            tool_name (str): 工具名称
            arguments (Dict[str, Any]): 工具参数
        
        返回：
            Any: 工具执行结果
        """
        try:
            result = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            logger.info(
                "MCP 工具调用成功",
                server=self.server_name,
                tool=tool_name
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"MCP 工具调用失败: {tool_name}",
                server=self.server_name,
                error=str(e)
            )
            raise
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
    
    def __del__(self):
        """析构函数"""
        self.stop()

