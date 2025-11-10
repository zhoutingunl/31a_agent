"""
文件名: helpers.py
功能: 辅助工具函数集合
"""

from datetime import datetime
from typing import Any, Dict, Optional


def format_timestamp(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳为字符串
    
    参数:
        dt (datetime, optional): 日期时间对象，默认为当前时间
        fmt (str): 格式化字符串，默认为 "YYYY-MM-DD HH:MM:SS"
    
    返回:
        str: 格式化后的时间字符串
    
    示例:
        >>> format_timestamp()
        '2025-10-12 14:30:00'
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本，如果超过最大长度则添加省略号
    
    参数:
        text (str): 要截断的文本
        max_length (int): 最大长度，默认 100
        suffix (str): 截断后的后缀，默认为 "..."
    
    返回:
        str: 截断后的文本
    
    示例:
        >>> truncate_text("这是一段很长的文本" * 10, 20)
        '这是一段很长的文本这是一...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def safe_dict_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    安全地从嵌套字典中获取值
    
    参数:
        data (dict): 字典数据
        *keys: 键路径
        default: 默认值
    
    返回:
        获取的值，如果不存在则返回 default
    
    示例:
        >>> data = {"user": {"profile": {"name": "张三"}}}
        >>> safe_dict_get(data, "user", "profile", "name")
        '张三'
        >>> safe_dict_get(data, "user", "profile", "age", default=0)
        0
    """
    result = data
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return default
    return result


def mask_sensitive_info(text: str, visible_chars: int = 4) -> str:
    """
    脱敏敏感信息（如 API Key、密码等）
    
    参数:
        text (str): 原始文本
        visible_chars (int): 保留可见字符数，默认 4
    
    返回:
        str: 脱敏后的文本
    
    示例:
        >>> mask_sensitive_info("sk-1234567890abcdef")
        'sk-1****cdef'
    """
    if len(text) <= visible_chars * 2:
        return "*" * len(text)
    
    return f"{text[:visible_chars]}****{text[-visible_chars:]}"


def bytes_to_human_readable(size_bytes: int) -> str:
    """
    将字节大小转换为人类可读的格式
    
    参数:
        size_bytes (int): 字节大小
    
    返回:
        str: 人类可读的大小字符串
    
    示例:
        >>> bytes_to_human_readable(1024)
        '1.00 KB'
        >>> bytes_to_human_readable(1048576)
        '1.00 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典（后面的字典会覆盖前面的）
    
    参数:
        *dicts: 要合并的字典
    
    返回:
        Dict: 合并后的字典
    
    示例:
        >>> merge_dicts({"a": 1}, {"b": 2}, {"a": 3})
        {'a': 3, 'b': 2}
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def parse_bool(value: Any) -> bool:
    """
    将各种类型的值解析为布尔值
    
    参数:
        value: 要解析的值
    
    返回:
        bool: 解析后的布尔值
    
    示例:
        >>> parse_bool("true")
        True
        >>> parse_bool("0")
        False
        >>> parse_bool(1)
        True
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "on", "是")
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    return False

