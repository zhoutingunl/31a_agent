"""
文件名: stop_server.py
功能: 停止服务器脚本，清理所有相关进程
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    # Windows 控制台编码设置
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
elif sys.platform == 'darwin':
    # macOS 通常已经使用 UTF-8，但确保环境变量设置正确
    import os
    os.environ.setdefault('LANG', 'en_US.UTF-8')
    os.environ.setdefault('LC_ALL', 'en_US.UTF-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.config import config

def kill_processes_by_name(process_name):
    """根据进程名终止进程"""
    try:
        if sys.platform == 'win32':
            # Windows 系统
            result = subprocess.run(
                ['taskkill', '/F', '/IM', process_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ 已终止所有 {process_name} 进程")
            else:
                print(f"没有找到 {process_name} 进程")
        else:
            # Linux/macOS 系统
            result = subprocess.run(
                ['pkill', '-f', process_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ 已终止所有 {process_name} 进程")
            else:
                print(f"没有找到 {process_name} 进程")
    except Exception as e:
        print(f"终止进程时出错: {e}")

def kill_processes_by_port(port):
    """根据端口终止进程"""
    try:
        if sys.platform == 'win32':
            # Windows 系统 - 查找占用端口的进程
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                pids = set()
                
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid.isdigit():
                                pids.add(pid)
                
                # 终止找到的进程
                for pid in pids:
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], check=True)
                        print(f"✓ 已终止占用端口 {port} 的进程 PID={pid}")
                    except subprocess.CalledProcessError:
                        print(f"✗ 无法终止进程 PID={pid}")
                
                if not pids:
                    print(f"没有找到占用端口 {port} 的进程")
        else:
            # Linux/macOS 系统
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(['kill', '-9', pid], check=True)
                        print(f"✓ 已终止占用端口 {port} 的进程 PID={pid}")
                    except subprocess.CalledProcessError:
                        print(f"✗ 无法终止进程 PID={pid}")
            else:
                print(f"没有找到占用端口 {port} 的进程")
                
    except Exception as e:
        print(f"根据端口终止进程时出错: {e}")

def main():
    """停止服务器"""
    print("\n" + "=" * 60)
    print("Agent 项目 - 停止服务器")
    print("=" * 60)
    
    # 获取配置的端口
    port = config.get("app.port", 8000)
    
    print(f"\n正在停止服务器 (端口: {port})...")
    
    # 1. 根据端口终止进程
    print("\n1. 清理占用端口的进程:")
    kill_processes_by_port(port)
    
    # 2. 终止所有 Python 进程（更彻底）
    print("\n2. 清理 Python 进程:")
    if sys.platform == 'win32':
        kill_processes_by_name("python.exe")
    elif sys.platform == 'darwin':
        # macOS 上可能有多种 Python 可执行文件名
        kill_processes_by_name("python")
        kill_processes_by_name("python3")
    else:
        # Linux
        kill_processes_by_name("python")
    
    # 3. 等待一下让进程完全终止
    print("\n3. 等待进程完全终止...")
    time.sleep(2)
    
    # 4. 验证端口是否已释放
    print("\n4. 验证端口状态:")
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                if f':{port}' in result.stdout and 'LISTENING' in result.stdout:
                    print(f"⚠️  端口 {port} 仍被占用")
                else:
                    print(f"✓ 端口 {port} 已释放")
        else:
            result = subprocess.run(
                ['lsof', '-i', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"⚠️  端口 {port} 仍被占用")
            else:
                print(f"✓ 端口 {port} 已释放")
    except Exception as e:
        print(f"验证端口状态时出错: {e}")
    
    print("\n服务器停止完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
