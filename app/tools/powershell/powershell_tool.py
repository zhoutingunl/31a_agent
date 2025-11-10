"""
文件名: powershell_tool.py
功能: PowerShell 命令执行工具（会话模式）
"""

import subprocess
import time
import re
import threading
import signal
import os
from typing import Any, Type, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, Field

from app.tools.base import AgentTool, ToolInput
from app.utils.logger import get_logger
from app.utils.exceptions import ToolExecutionError
from app.core.roles.role_manager import role_manager

logger = get_logger(__name__)


class PowerShellInput(ToolInput):
    """
    PowerShell 工具输入
    
    字段:
        command (str): 要执行的 PowerShell 命令
        timeout (int): 超时时间（秒），默认30秒
        cwd (Optional[str]): 工作目录，默认为项目根目录
        role_type (Optional[str]): 角色类型，用于安全检查
    """
    
    command: str = Field(..., description="要执行的 PowerShell 命令")
    timeout: int = Field(30, description="超时时间（秒），默认30秒")
    cwd: Optional[str] = Field(None, description="工作目录，默认为项目根目录")
    role_type: Optional[str] = Field("general", description="角色类型，用于安全检查（general 或 customer_service）")


class PowerShellTool(AgentTool):
    """
    PowerShell 命令执行工具（会话模式）
    
    功能：
    - 维护持久的 PowerShell 进程会话
    - 支持连续执行多个命令，共享变量和环境
    - 自定义工作目录和超时时间
    - 返回详细的执行结果（输出、错误、退出码、耗时）
    - 基于角色的安全检查
    """
    
    name: str = "powershell_execute"
    description: str = """执行 PowerShell 命令（会话模式）
    
支持：
- 连续执行多个命令，共享变量和环境
- 自定义工作目录和超时时间
- 返回详细的执行结果（输出、错误、退出码、耗时）
- 基于角色的安全检查

示例：
- Get-Date
- $a=1; $a+1
- ls C:\
- Get-Process | Where-Object {$_.CPU -gt 100}
"""
    args_schema: Type[BaseModel] = PowerShellInput
    
    def __init__(self):
        """初始化 PowerShell 工具"""
        super().__init__()
        
        # PowerShell 进程相关
        self.process: Optional[subprocess.Popen] = None
        self.command_history: list = []
        self.current_cwd: str = str(Path(__file__).parent.parent.parent.parent)  # 项目根目录
        
        # 危险命令模式（通用助手限制）
        self.dangerous_patterns = [
            r'Remove-Item.*-Recurse',
            r'rm\s+-rf',
            r'Format-',
            r'Clear-Disk',
            r'Set-ExecutionPolicy',
            r'Stop-Computer',
            r'Restart-Computer',
            r'Shutdown',
            r'Format-Volume',
            r'Clear-RecycleBin',
            r'Remove-WmiObject',
            r'Invoke-Expression',
            r'IEX',
            r'Invoke-Command.*-ScriptBlock',
            r'Start-Process.*-FilePath.*\.exe',
            r'New-Item.*-ItemType.*HardLink',
            r'New-Item.*-ItemType.*SymbolicLink',
            r'Set-ItemProperty.*-Path.*HKLM',
            r'Set-ItemProperty.*-Path.*HKCU',
            r'Remove-ItemProperty',
            r'New-ItemProperty',
            r'Set-Service',
            r'Stop-Service',
            r'Remove-Service',
            r'New-Service',
            r'Set-NetFirewallRule',
            r'New-NetFirewallRule',
            r'Remove-NetFirewallRule',
            r'Disable-NetAdapter',
            r'Enable-NetAdapter',
            r'Remove-NetAdapter',
        ]
        
        # 启动 PowerShell 进程
        self._start_powershell_process()
    
    def _start_powershell_process(self):
        """启动 PowerShell 进程"""
        try:
            self.process = subprocess.Popen(
                ["powershell", "-NoLogo", "-NoProfile", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.current_cwd,
                encoding='utf-8',
                errors='ignore'
            )
            
            self.logger.info("PowerShell 进程启动成功")
            
        except Exception as e:
            self.logger.error(f"启动 PowerShell 进程失败: {e}")
            raise ToolExecutionError(
                f"启动 PowerShell 进程失败: {str(e)}",
                tool_name=self.name,
                details={"error": str(e)}
            )
    
    def _restart_powershell_process(self):
        """重启 PowerShell 进程"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
        
        self._start_powershell_process()
        self.logger.info("PowerShell 进程已重启")
    
    def execute(self, command: str, timeout: int = 30, cwd: str = None, role_type: str = "general") -> Dict[str, Any]:
        """
        执行 PowerShell 命令
        
        参数:
            command (str): PowerShell 命令
            timeout (int): 超时时间（秒）
            cwd (str): 工作目录
        
        返回:
            Dict[str, Any]: 执行结果
        """
        start_time = time.time()
        
        try:
            # 安全检查（基于角色）
            if not self._is_command_allowed_by_role(command, role_type):
                raise ToolExecutionError(
                    "命令被安全策略阻止",
                    tool_name=self.name,
                    details={"command": command, "role_type": role_type, "reason": "安全策略限制"}
                )
            
            # 设置工作目录
            if cwd:
                if not os.path.exists(cwd):
                    raise ToolExecutionError(
                        f"工作目录不存在: {cwd}",
                        tool_name=self.name,
                        details={"cwd": cwd}
                    )
                # 在命令前添加 cd 命令
                full_command = f"cd '{cwd}'; {command}"
            else:
                full_command = command
            
            # 检查进程是否还在运行
            if not self.process or self.process.poll() is not None:
                self.logger.warning("PowerShell 进程已停止，正在重启...")
                self._restart_powershell_process()
            
            # 执行命令
            result = self._execute_command(full_command, timeout)
            
            execution_time = time.time() - start_time
            
            # 记录命令历史
            self.command_history.append({
                "command": command,
                "timestamp": time.time(),
                "execution_time": execution_time,
                "success": result["success"]
            })
            
            # 构建返回结果
            return {
                "success": result["success"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "execution_time": round(execution_time, 3),
                "command": command,
                "message": result["message"],
                "cwd": cwd or self.current_cwd
            }
            
        except ToolExecutionError:
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"PowerShell 命令执行失败: {e}")
            raise ToolExecutionError(
                f"PowerShell 命令执行失败: {str(e)}",
                tool_name=self.name,
                details={"command": command, "error": str(e), "execution_time": execution_time}
            )
    
    def _execute_command(self, command: str, timeout: int) -> Dict[str, Any]:
        """执行单个命令"""
        try:
            # 发送命令到 PowerShell
            self.process.stdin.write(command + "\n")
            self.process.stdin.write("Write-Host 'POWERSHELL_TOOL_END_MARKER'\n")
            self.process.stdin.flush()
            
            # 读取输出
            stdout_lines = []
            stderr_lines = []
            
            # 使用线程来读取输出，支持超时
            stdout_data = []
            stderr_data = []
            read_timeout = False
            
            def read_stdout():
                nonlocal read_timeout
                try:
                    while True:
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line == "POWERSHELL_TOOL_END_MARKER":
                            break
                        stdout_data.append(line)
                except:
                    pass
            
            def read_stderr():
                try:
                    while True:
                        line = self.process.stderr.readline()
                        if not line:
                            break
                        stderr_data.append(line.strip())
                except:
                    pass
            
            # 启动读取线程
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待完成或超时
            stdout_thread.join(timeout)
            stderr_thread.join(1)  # stderr 超时时间短一些
            
            if stdout_thread.is_alive():
                read_timeout = True
                # 强制终止读取
                try:
                    self.process.terminate()
                except:
                    pass
            
            stdout = "\n".join(stdout_data)
            stderr = "\n".join(stderr_data)
            
            # 检查进程状态
            exit_code = self.process.poll()
            if exit_code is None:
                exit_code = 0  # 进程还在运行，认为成功
            
            success = exit_code == 0 and not read_timeout
            
            message = "执行成功"
            if read_timeout:
                message = f"命令执行超时（{timeout}秒）"
            elif exit_code != 0:
                message = f"命令执行失败，退出码: {exit_code}"
            
            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "message": message
            }
            
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "message": f"执行异常: {str(e)}"
            }
    
    def _is_command_allowed(self, command: str) -> bool:
        """
        检查命令是否允许执行
        
        参数:
            command (str): PowerShell 命令
        
        返回:
            bool: 是否允许执行
        """
        # 获取当前角色配置（通过工具管理器获取）
        # 这里我们需要一个方法来获取当前的角色信息
        # 暂时使用默认的安全检查逻辑
        
        # 检查危险命令模式
        command_lower = command.lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command_lower, re.IGNORECASE):
                self.logger.warning(
                    "检测到危险命令",
                    command=command,
                    pattern=pattern
                )
                return False
        
        return True
    
    def _is_command_allowed_by_role(self, command: str, role_type: str) -> bool:
        """
        根据角色类型检查命令是否允许执行
        
        参数:
            command (str): PowerShell 命令
            role_type (str): 角色类型
        
        返回:
            bool: 是否允许执行
        """
        try:
            # 获取角色配置
            role_config = role_manager.get_role(role_type)
            if not role_config or not role_config.security_config:
                # 如果没有安全配置，使用默认限制模式
                return self._is_command_allowed(command)
            
            security_config = role_config.security_config
            
            # 根据安全模式进行检查
            if security_config.powershell_mode == "whitelist":
                # 白名单模式：仅允许白名单中的命令
                return command in security_config.powershell_whitelist
            else:
                # 限制模式：限制危险命令
                command_lower = command.lower()
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, command_lower, re.IGNORECASE):
                        self.logger.warning(
                            "检测到危险命令",
                            command=command,
                            pattern=pattern,
                            role_type=role_type
                        )
                        return False
                return True
                
        except Exception as e:
            self.logger.error(f"安全检查失败: {e}")
            # 出错时使用默认限制模式
            return self._is_command_allowed(command)
    
    def get_command_history(self) -> list:
        """获取命令历史"""
        return self.command_history.copy()
    
    def clear_command_history(self):
        """清空命令历史"""
        self.command_history.clear()
    
    def __del__(self):
        """析构函数，清理 PowerShell 进程"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
