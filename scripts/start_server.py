"""
文件名: start_server.py
功能: 完善的服务器启动脚本，支持优雅关闭
"""

import sys
import os
import signal
import atexit
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

import uvicorn
from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 全局变量存储进程
server_process = None
child_processes = []

def cleanup_processes():
    """清理所有相关进程"""
    global server_process, child_processes
    
    print("\n" + "=" * 60)
    print("正在清理进程...")
    print("=" * 60)
    
    # 清理子进程
    for proc in child_processes:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"✓ 子进程 {proc.pid} 已终止")
            except:
                try:
                    proc.kill()
                    print(f"✓ 子进程 {proc.pid} 已强制终止")
                except:
                    print(f"✗ 无法终止子进程 {proc.pid}")
    
    # 清理主进程
    if server_process and server_process.poll() is None:
        try:
            server_process.terminate()
            server_process.wait(timeout=5)
            print(f"✓ 主进程 {server_process.pid} 已终止")
        except:
            try:
                server_process.kill()
                print(f"✓ 主进程 {server_process.pid} 已强制终止")
            except:
                print(f"✗ 无法终止主进程 {server_process.pid}")
    
    # 清理端口占用
    cleanup_port_processes()
    
    print("进程清理完成")
    print("=" * 60)

def cleanup_port_processes():
    """清理占用端口的进程"""
    try:
        import psutil
        
        # 获取配置的端口
        port = config.get("app.port", 8000)
        
        # 查找占用端口的进程
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                if proc.info['connections']:
                    for conn in proc.info['connections']:
                        if conn.laddr.port == port:
                            print(f"发现占用端口 {port} 的进程: PID={proc.info['pid']}, Name={proc.info['name']}")
                            proc.terminate()
                            proc.wait(timeout=3)
                            print(f"✓ 已终止占用端口的进程 {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        print("提示: 安装 psutil 可以更好地清理进程 (pip install psutil)")
    except Exception as e:
        print(f"清理端口进程时出错: {e}")

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在优雅关闭...")
    cleanup_processes()
    sys.exit(0)

def register_cleanup():
    """注册清理函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    # 注册退出时的清理函数
    atexit.register(cleanup_processes)

def main():
    """启动开发服务器"""
    global server_process
    
    # 注册清理函数
    register_cleanup()
    
    print("\n" + "=" * 60)
    print("Agent 项目 - 开发服务器启动")
    print("=" * 60)
    
    # 从配置中获取服务器参数
    host = config.get("app.host", "0.0.0.0")
    port = config.get("app.port", 8000)
    debug = config.get("app.debug", True)
    
    print(f"\n服务配置:")
    print(f"  - 主机: {host}")
    print(f"  - 端口: {port}")
    print(f"  - 调试模式: {debug}")
    print(f"\n访问地址:")
    print(f"  - Web 界面: http://localhost:{port}/")
    print(f"  - API 文档: http://localhost:{port}/docs")
    print(f"  - 健康检查: http://localhost:{port}/health")
    print(f"\n按 Ctrl+C 停止服务器")
    print("=" * 60 + "\n")
    
    logger.info(
        "启动开发服务器",
        host=host,
        port=port,
        debug=debug
    )
    
    try:
        # 启动服务器
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug,  # 开发模式下自动重载
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n收到键盘中断信号...")
    except Exception as e:
        print(f"\n服务器启动失败: {e}")
    finally:
        cleanup_processes()

if __name__ == "__main__":
    main()
