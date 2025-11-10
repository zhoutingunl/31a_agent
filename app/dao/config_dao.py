"""
文件名: config_dao.py
功能: 配置管理数据访问层
负责配置文件的读写操作，包括 YAML 配置和提示词文件
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from ruamel.yaml import YAML

from app.utils.logger import get_logger
from app.utils.exceptions import ConfigError

logger = get_logger(__name__)


class ConfigDAO:
    """
    配置数据访问对象
    
    功能：
    - 读取和写入 config.yaml 配置文件
    - 管理提示词文件（config/prompts/ 目录）
    - 读取角色配置文件（app/core/roles/configs/ 目录）
    - 保留 YAML 文件的注释和格式
    """
    
    def __init__(self):
        """初始化配置 DAO"""
        # 配置文件路径
        self.config_path = Path("config/config.yaml")
        self.prompts_dir = Path("config/prompts")
        self.roles_dir = Path("app/core/roles/configs")
        
        # 使用 ruamel.yaml 保留格式和注释
        self.yaml_parser = YAML()
        self.yaml_parser.preserve_quotes = True
        self.yaml_parser.width = 4096  # 避免自动换行
    
    def read_yaml_config(self) -> Dict[str, Any]:
        """
        读取 config.yaml 配置文件
        
        返回:
            Dict[str, Any]: 配置字典
            
        异常:
            ConfigError: 文件不存在或格式错误时抛出
        """
        try:
            if not self.config_path.exists():
                raise ConfigError(
                    f"配置文件不存在: {self.config_path}",
                    details={"config_path": str(self.config_path)}
                )
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = self.yaml_parser.load(f)
            
            logger.info("成功读取配置文件", path=str(self.config_path))
            return config_data or {}
            
        except yaml.YAMLError as e:
            raise ConfigError(
                f"配置文件格式错误: {str(e)}",
                details={"config_path": str(self.config_path), "error": str(e)}
            )
        except Exception as e:
            raise ConfigError(
                f"读取配置文件失败: {str(e)}",
                details={"config_path": str(self.config_path), "error": str(e)}
            )
    
    def write_yaml_config(self, config_data: Dict[str, Any]) -> None:
        """
        写入 config.yaml 配置文件
        
        参数:
            config_data (Dict[str, Any]): 配置数据
            
        异常:
            ConfigError: 写入失败时抛出
        """
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入配置文件，保留格式
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.yaml_parser.dump(config_data, f)
            
            logger.info("成功写入配置文件", path=str(self.config_path))
            
        except Exception as e:
            raise ConfigError(
                f"写入配置文件失败: {str(e)}",
                details={"config_path": str(self.config_path), "error": str(e)}
            )
    
    def read_prompt_file(self, filename: str) -> str:
        """
        读取提示词文件
        
        参数:
            filename (str): 文件名
            
        返回:
            str: 文件内容
            
        异常:
            ConfigError: 文件不存在或读取失败时抛出
        """
        try:
            file_path = self.prompts_dir / filename
            
            if not file_path.exists():
                raise ConfigError(
                    f"提示词文件不存在: {filename}",
                    details={"filename": filename, "path": str(file_path)}
                )
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            logger.info("成功读取提示词文件", filename=filename)
            return content
            
        except Exception as e:
            raise ConfigError(
                f"读取提示词文件失败: {str(e)}",
                details={"filename": filename, "error": str(e)}
            )
    
    def write_prompt_file(self, filename: str, content: str) -> None:
        """
        写入提示词文件
        
        参数:
            filename (str): 文件名
            content (str): 文件内容
            
        异常:
            ConfigError: 写入失败时抛出
        """
        try:
            # 确保提示词目录存在
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = self.prompts_dir / filename
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info("成功写入提示词文件", filename=filename)
            
        except Exception as e:
            raise ConfigError(
                f"写入提示词文件失败: {str(e)}",
                details={"filename": filename, "error": str(e)}
            )
    
    def list_prompt_files(self) -> List[Dict[str, Any]]:
        """
        列出所有提示词文件
        
        返回:
            List[Dict[str, Any]]: 提示词文件信息列表
            每个字典包含: filename, category, description
        """
        try:
            if not self.prompts_dir.exists():
                return []
            
            prompt_files = []
            
            for file_path in self.prompts_dir.glob("*.txt"):
                filename = file_path.name
                
                # 根据文件名推断分类和描述
                category, description = self._parse_prompt_filename(filename)
                
                prompt_files.append({
                    "filename": filename,
                    "category": category,
                    "description": description
                })
            
            # 按文件名排序
            prompt_files.sort(key=lambda x: x["filename"])
            
            logger.info("成功列出提示词文件", count=len(prompt_files))
            return prompt_files
            
        except Exception as e:
            logger.error("列出提示词文件失败", error=str(e))
            return []
    
    def _parse_prompt_filename(self, filename: str) -> tuple[str, str]:
        """
        解析提示词文件名，推断分类和描述
        
        参数:
            filename (str): 文件名
            
        返回:
            tuple[str, str]: (分类, 描述)
        """
        # 移除 .txt 扩展名
        name = filename.replace(".txt", "")
        
        # 根据文件名模式推断分类和描述
        if name == "system":
            return "system", "全局系统提示词"
        elif name.startswith("general_"):
            category = name.replace("general_", "")
            descriptions = {
                "system": "通用助手系统提示词",
                "planner": "通用助手任务规划提示词",
                "reflection": "通用助手反思提示词"
            }
            return "general", descriptions.get(category, f"通用助手{category}提示词")
        elif name.startswith("customer_service_"):
            category = name.replace("customer_service_", "")
            descriptions = {
                "system": "电商客服系统提示词",
                "planner": "电商客服任务规划提示词",
                "reflection": "电商客服反思提示词"
            }
            return "customer_service", descriptions.get(category, f"电商客服{category}提示词")
        else:
            return "other", f"{name}提示词"
    
    def read_role_configs(self) -> List[Dict[str, Any]]:
        """
        读取所有角色配置文件
        
        返回:
            List[Dict[str, Any]]: 角色配置列表
        """
        try:
            if not self.roles_dir.exists():
                return []
            
            role_configs = []
            
            for file_path in self.roles_dir.glob("*.yaml"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        role_data = yaml.safe_load(f)
                    
                    if role_data:
                        role_configs.append(role_data)
                        
                except Exception as e:
                    logger.warning("读取角色配置文件失败", file=str(file_path), error=str(e))
                    continue
            
            logger.info("成功读取角色配置文件", count=len(role_configs))
            return role_configs
            
        except Exception as e:
            logger.error("读取角色配置文件失败", error=str(e))
            return []
    
    def backup_config(self) -> str:
        """
        备份当前配置文件
        
        返回:
            str: 备份文件路径
        """
        try:
            if not self.config_path.exists():
                raise ConfigError("配置文件不存在，无法备份")
            
            # 生成备份文件名（带时间戳）
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"config_backup_{timestamp}.yaml"
            backup_path = self.config_path.parent / backup_filename
            
            # 复制文件
            import shutil
            shutil.copy2(self.config_path, backup_path)
            
            logger.info("成功备份配置文件", backup_path=str(backup_path))
            return str(backup_path)
            
        except Exception as e:
            raise ConfigError(
                f"备份配置文件失败: {str(e)}",
                details={"error": str(e)}
            )
    
    def validate_config_structure(self, config_data: Dict[str, Any]) -> bool:
        """
        验证配置数据结构是否完整
        
        参数:
            config_data (Dict[str, Any]): 配置数据
            
        返回:
            bool: 是否有效
        """
        try:
            # 检查必需的顶级配置节
            required_sections = ["app", "database", "llm", "memory", "tools", "upload", "logging"]
            
            for section in required_sections:
                if section not in config_data:
                    logger.error("配置缺少必需节", section=section)
                    return False
            
            # 检查应用配置
            app_config = config_data.get("app", {})
            if not all(key in app_config for key in ["name", "version", "host", "port"]):
                logger.error("应用配置不完整")
                return False
            
            # 检查数据库配置
            db_config = config_data.get("database", {})
            if "mysql" not in db_config:
                logger.error("数据库配置缺少 MySQL 配置")
                return False
            
            # 检查 LLM 配置
            llm_config = config_data.get("llm", {})
            if not all(key in llm_config for key in ["default_provider", "module_configs", "providers"]):
                logger.error("LLM 配置不完整")
                return False
            
            logger.info("配置结构验证通过")
            return True
            
        except Exception as e:
            logger.error("配置结构验证失败", error=str(e))
            return False
