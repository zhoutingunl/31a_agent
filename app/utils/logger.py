"""
文件名: logger.py
功能: 统一的日志系统，提供中文友好的日志输出
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import colorlog


class StructuredLogger:
    """
    结构化日志记录器
    
    功能：
    - 中文友好的日志格式
    - 彩色控制台输出
    - 文件日志轮转
    - 支持结构化日志（键值对参数）
    
    属性:
        logger (logging.Logger): Python 标准日志记录器
        name (str): 日志记录器名称
    """
    
    def __init__(self, name: str):
        """
        初始化日志记录器
        
        参数:
            name (str): 日志记录器名称（通常使用 __name__）
        """
        self.name = name  # 日志记录器名称
        self.logger = logging.getLogger(name)  # 获取 Python 标准日志记录器
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """设置日志记录器（处理器、格式化器等）"""
        # 设置日志级别为 DEBUG（最低级别，由处理器控制实际输出）
        self.logger.setLevel(logging.DEBUG)
        
        # 添加控制台处理器（彩色输出）
        self._add_console_handler()
        
        # 添加文件处理器（日志文件）
        self._add_file_handler()
    
    def _add_console_handler(self) -> None:
        """添加控制台处理器（彩色输出）"""
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # 控制台只输出 INFO 及以上级别
        
        # 定义彩色日志格式
        console_format = (
            "%(log_color)s%(asctime)s%(reset)s | "
            "%(log_color)s%(levelname)-8s%(reset)s | "
            "%(cyan)s%(name)s%(reset)s | "
            "%(message)s"
        )
        
        # 创建彩色格式化器
        console_formatter = colorlog.ColoredFormatter(
            console_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        )
        
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self) -> None:
        """添加文件处理器（日志轮转）"""
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 应用日志文件（所有级别）
        app_log_path = log_dir / "app.log"
        app_handler = RotatingFileHandler(
            app_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # 保留5个备份文件
            encoding="utf-8"
        )
        app_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
        
        # 错误日志文件（仅 ERROR 及以上）
        error_log_path = log_dir / "error.log"
        error_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        
        # 定义文件日志格式（详细格式）
        file_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        )
        file_formatter = logging.Formatter(
            file_format,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        app_handler.setFormatter(file_formatter)
        error_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(app_handler)
        self.logger.addHandler(error_handler)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """
        格式化日志消息，添加结构化参数
        
        参数:
            message (str): 日志消息
            **kwargs: 额外的键值对参数
        
        返回:
            格式化后的消息字符串
        """
        if not kwargs:
            return message
        
        # 将键值对参数格式化为字符串
        params_str = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        return f"{message} | {params_str}"
    
    def debug(self, message: str, **kwargs) -> None:
        """
        记录 DEBUG 级别日志
        
        参数:
            message (str): 日志消息
            **kwargs: 额外的键值对参数
        """
        self.logger.debug(self._format_message(message, **kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        """
        记录 INFO 级别日志
        
        参数:
            message (str): 日志消息
            **kwargs: 额外的键值对参数
        """
        self.logger.info(self._format_message(message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """
        记录 WARNING 级别日志
        
        参数:
            message (str): 日志消息
            **kwargs: 额外的键值对参数
        """
        self.logger.warning(self._format_message(message, **kwargs))
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        记录 ERROR 级别日志
        
        参数:
            message (str): 日志消息
            exc_info (bool): 是否包含异常堆栈信息
            **kwargs: 额外的键值对参数
        """
        self.logger.error(
            self._format_message(message, **kwargs),
            exc_info=exc_info
        )
    
    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """
        记录 CRITICAL 级别日志
        
        参数:
            message (str): 日志消息
            exc_info (bool): 是否包含异常堆栈信息
            **kwargs: 额外的键值对参数
        """
        self.logger.critical(
            self._format_message(message, **kwargs),
            exc_info=exc_info
        )
    
    def exception(self, message: str, **kwargs) -> None:
        """
        记录异常日志（ERROR 级别 + 堆栈信息）
        
        参数:
            message (str): 日志消息
            **kwargs: 额外的键值对参数
        """
        self.logger.exception(self._format_message(message, **kwargs))


# 日志记录器缓存（避免重复创建）
_logger_cache: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    获取日志记录器实例（工厂函数）
    
    参数:
        name (str): 日志记录器名称（通常使用 __name__）
    
    返回:
        StructuredLogger: 日志记录器实例
    
    示例:
        >>> logger = get_logger(__name__)
        >>> logger.info("应用启动", version="0.1.0")
        >>> logger.error("数据库连接失败", error="Connection refused")
    """
    if name not in _logger_cache:
        _logger_cache[name] = StructuredLogger(name)
    
    return _logger_cache[name]


# 提供模块级别的默认日志记录器
logger = get_logger("agent")

