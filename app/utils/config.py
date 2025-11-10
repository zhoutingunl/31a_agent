"""
文件名: config.py
功能: 配置管理器，负责加载和管理应用配置
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from app.utils.exceptions import ConfigError


class Config:
    """
    配置管理器类
    
    功能：
    - 从 YAML 文件加载配置
    - 支持环境变量占位符（${VAR}）
    - 支持点号访问（如 config.get("database.mysql.host")）
    - 自动加载 .env 文件
    
    属性:
        _config (Dict[str, Any]): 配置数据字典
        _config_path (Path): 配置文件路径
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置管理器
        
        参数:
            config_path (str): 配置文件路径，默认为 config/config.yaml
        
        异常:
            ConfigError: 配置文件不存在或格式错误时抛出
        """
        self._config: Dict[str, Any] = {}  # 配置数据
        self._config_path = Path(config_path)  # 配置文件路径
        
        # 加载 .env 文件中的环境变量
        load_dotenv()
        
        # 加载配置文件
        self._load_config()
    
    def _load_config(self) -> None:
        """
        从 YAML 文件加载配置
        
        异常:
            ConfigError: 配置文件不存在或解析失败时抛出
        """
        # 检查配置文件是否存在
        if not self._config_path.exists():
            raise ConfigError(
                f"配置文件不存在: {self._config_path}",
                details={"config_path": str(self._config_path)}
            )
        
        try:
            # 读取并解析 YAML 文件
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
            
            # 解析环境变量占位符
            self._config = self._resolve_env_vars(raw_config)
            
        except yaml.YAMLError as e:
            raise ConfigError(
                f"配置文件格式错误: {str(e)}",
                details={"config_path": str(self._config_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigError(
                f"加载配置文件失败: {str(e)}",
                details={"config_path": str(self._config_path), "error": str(e)}
            )
    
    def _resolve_env_vars(self, data: Any) -> Any:
        """
        递归解析配置中的环境变量占位符
        
        支持格式: ${VAR_NAME}
        
        参数:
            data: 配置数据（可以是字典、列表、字符串等）
        
        返回:
            解析后的配置数据
        """
        if isinstance(data, dict):
            # 递归处理字典
            return {key: self._resolve_env_vars(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            # 递归处理列表
            return [self._resolve_env_vars(item) for item in data]
        
        elif isinstance(data, str):
            # 解析字符串中的环境变量占位符
            # 匹配 ${VAR_NAME} 格式
            pattern = r"\$\{([^}]+)\}"
            
            def replacer(match):
                var_name = match.group(1)  # 获取变量名
                var_value = os.getenv(var_name)  # 从环境变量获取值
                
                if var_value is None:
                    # 环境变量不存在，保留原始占位符并记录警告
                    return match.group(0)
                
                return var_value
            
            return re.sub(pattern, replacer, data)
        
        else:
            # 其他类型直接返回
            return data
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号路径
        
        参数:
            key (str): 配置键，支持点号分隔的路径（如 "database.mysql.host"）
            default: 默认值，当配置不存在时返回
        
        返回:
            配置值，如果不存在则返回 default
        
        示例:
            >>> config.get("database.mysql.host")
            'localhost'
            >>> config.get("nonexistent.key", "default_value")
            'default_value'
        """
        # 将点号路径拆分为键列表
        keys = key.split(".")
        
        # 从配置字典中逐层获取值
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_required(self, key: str) -> Any:
        """
        获取必需的配置值，如果不存在则抛出异常
        
        参数:
            key (str): 配置键
        
        返回:
            配置值
        
        异常:
            ConfigError: 配置不存在时抛出
        """
        value = self.get(key)
        if value is None:
            raise ConfigError(
                f"缺少必需配置: {key}",
                details={"key": key}
            )
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值（运行时修改，不会写入文件）
        
        参数:
            key (str): 配置键，支持点号路径
            value: 配置值
        """
        keys = key.split(".")
        target = self._config
        
        # 逐层创建字典结构
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        
        # 设置最终值
        target[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        返回完整配置字典
        
        返回:
            配置字典的副本
        """
        return self._config.copy()
    
    def __repr__(self) -> str:
        """返回配置对象的字符串表示"""
        return f"<Config from {self._config_path}>"


# 全局配置实例（单例模式）
_config_instance: Optional[Config] = None


def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    获取全局配置实例（单例模式）
    
    参数:
        config_path (str): 配置文件路径
    
    返回:
        Config: 配置实例
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = Config(config_path)
    
    return _config_instance


# 提供便捷访问方式
try:
    config = get_config()
except ConfigError:
    # 如果配置文件不存在（如首次运行），创建一个空配置
    config = Config.__new__(Config)
    config._config = {}
    config._config_path = Path("config/config.yaml")

