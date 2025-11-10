"""
角色管理器

负责加载、管理和提供角色配置
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache

from .role_config import RoleConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RoleManager:
    """
    角色管理器
    
    功能:
    - 加载所有角色配置
    - 提供角色配置查询
    - 工具权限过滤
    - 记忆策略获取
    """
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化角色管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self.roles: Dict[str, RoleConfig] = {}
        self.config_dir = Path(__file__).parent / "configs"
        
        # 加载所有角色配置
        self._load_all_roles()
        
        self._initialized = True
        logger.info(f"角色管理器初始化完成，加载了 {len(self.roles)} 个角色")
    
    def _load_all_roles(self):
        """
        从configs目录加载所有角色配置
        """
        try:
            if not self.config_dir.exists():
                logger.warning(f"角色配置目录不存在: {self.config_dir}")
                self.config_dir.mkdir(parents=True, exist_ok=True)
                return
            
            # 遍历所有YAML文件
            yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))
            
            for yaml_file in yaml_files:
                try:
                    role_config = RoleConfig.from_yaml(str(yaml_file))
                    self.roles[role_config.type] = role_config
                    logger.debug(f"加载角色配置: {role_config.type} - {role_config.name}")
                except Exception as e:
                    logger.error(f"加载角色配置失败 {yaml_file}: {e}")
                    continue
            
            if not self.roles:
                logger.warning("未加载到任何角色配置")
            
        except Exception as e:
            logger.error(f"加载角色配置失败: {e}")
    
    def get_role(self, role_type: str) -> Optional[RoleConfig]:
        """
        获取指定角色配置
        
        Args:
            role_type: 角色类型标识
            
        Returns:
            Optional[RoleConfig]: 角色配置对象，如果不存在则返回None
        """
        role = self.roles.get(role_type)
        
        if not role:
            logger.warning(f"角色配置不存在: {role_type}")
            # 返回默认通用助手配置
            return self._get_default_role()
        
        return role
    
    def _get_default_role(self) -> RoleConfig:
        """
        获取默认角色配置（通用助手）
        """
        return RoleConfig(
            name="默认助手",
            type="default",
            description="默认通用助手",
            system_prompt="你是一个智能助手，请帮助用户解决问题。",
            allowed_tools=["*"],
            memory_strategy={
                "short_term": True,
                "long_term": True,
                "knowledge_graph": True,
                "user_isolated": True,
                "rag_enabled": False,
                "retention_days": 90
            }
        )
    
    def list_roles(self) -> List[Dict[str, str]]:
        """
        列出所有可用角色
        
        Returns:
            List[Dict[str, str]]: 角色信息列表
        """
        return [
            {
                "type": role.type,
                "name": role.name,
                "description": role.description
            }
            for role in self.roles.values()
        ]
    
    def filter_tools(self, role_type: str, all_tools: List) -> List:
        """
        根据角色权限过滤工具
        
        Args:
            role_type: 角色类型
            all_tools: 所有可用工具列表
            
        Returns:
            List: 过滤后的工具列表
        """
        role = self.get_role(role_type)
        
        if not role:
            return all_tools
        
        # 如果允许所有工具
        if "*" in role.allowed_tools:
            return all_tools
        
        # 过滤工具
        filtered_tools = []
        for tool in all_tools:
            tool_name = getattr(tool, 'name', str(tool))
            if role.is_tool_allowed(tool_name):
                filtered_tools.append(tool)
        
        logger.debug(f"角色 {role_type} 工具过滤: {len(all_tools)} -> {len(filtered_tools)}")
        return filtered_tools
    
    def get_memory_strategy(self, role_type: str) -> Dict[str, Any]:
        """
        获取角色的记忆策略
        
        Args:
            role_type: 角色类型
            
        Returns:
            Dict[str, Any]: 记忆策略配置
        """
        role = self.get_role(role_type)
        
        if not role:
            return {}
        
        return role.memory_strategy.model_dump()
    
    def get_system_prompt(self, role_type: str) -> str:
        """
        获取角色的系统提示词
        
        Args:
            role_type: 角色类型
            
        Returns:
            str: 系统提示词
        """
        role = self.get_role(role_type)
        
        if not role:
            return ""
        
        return role.system_prompt
    
    def reload_roles(self):
        """
        重新加载所有角色配置（支持热加载）
        """
        logger.info("重新加载角色配置...")
        self.roles.clear()
        self._load_all_roles()
        logger.info(f"角色配置重新加载完成，当前有 {len(self.roles)} 个角色")


# 创建全局单例
role_manager = RoleManager()
