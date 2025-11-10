"""
文件名: config_service.py
功能: 配置管理服务层
处理配置相关的业务逻辑，包括配置验证、更新、重载等
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

from app.dao.config_dao import ConfigDAO
from app.schemas.config import (
    ConfigResponse, ConfigUpdateRequest, ConfigReloadResponse,
    PromptListResponse, PromptUpdateRequest, RoleListResponse,
    ReloadRequirementSchema
)
from app.utils.logger import get_logger
from app.utils.exceptions import ConfigError
from app.utils.config import get_config

logger = get_logger(__name__)


class ConfigService:
    """
    配置管理服务
    
    功能：
    - 配置的读取、更新、验证
    - 配置热重载
    - 提示词文件管理
    - 角色配置管理
    """
    
    def __init__(self):
        """初始化配置服务"""
        self.dao = ConfigDAO()
        self._config_instance = None  # 缓存配置实例
    
    def get_config(self) -> ConfigResponse:
        """
        获取完整配置
        
        返回:
            ConfigResponse: 完整配置响应
            
        异常:
            ConfigError: 配置读取失败时抛出
        """
        try:
            config_data = self.dao.read_yaml_config()
            
            # 验证配置结构
            if not self.dao.validate_config_structure(config_data):
                raise ConfigError("配置结构验证失败")
            
            # 转换为响应格式
            response = ConfigResponse(**config_data)
            
            logger.info("成功获取配置")
            return response
            
        except Exception as e:
            logger.error("获取配置失败", error=str(e))
            raise ConfigError(f"获取配置失败: {str(e)}")
    
    def update_config(self, update_request: ConfigUpdateRequest) -> ConfigResponse:
        """
        更新配置
        
        参数:
            update_request (ConfigUpdateRequest): 配置更新请求
            
        返回:
            ConfigResponse: 更新后的配置
            
        异常:
            ConfigError: 配置更新失败时抛出
        """
        try:
            # 读取当前配置
            current_config = self.dao.read_yaml_config()
            
            # 备份当前配置
            backup_path = self.dao.backup_config()
            logger.info("已备份配置文件", backup_path=backup_path)
            
            # 应用更新
            update_dict = update_request.dict(exclude_unset=True)
            for section, section_data in update_dict.items():
                if section_data is not None:
                    current_config[section] = section_data.dict(exclude_unset=True)
            
            # 验证更新后的配置
            if not self.dao.validate_config_structure(current_config):
                raise ConfigError("更新后的配置结构验证失败")
            
            # 写入配置文件
            self.dao.write_yaml_config(current_config)
            
            # 返回更新后的配置
            response = ConfigResponse(**current_config)
            
            logger.info("成功更新配置")
            return response
            
        except Exception as e:
            logger.error("更新配置失败", error=str(e))
            raise ConfigError(f"更新配置失败: {str(e)}")
    
    def reload_config(self) -> ConfigReloadResponse:
        """
        尝试热重载配置
        
        返回:
            ConfigReloadResponse: 重载结果
            
        异常:
            ConfigError: 重载失败时抛出
        """
        try:
            reloaded_sections = []
            requires_restart = []
            
            # 重新读取配置文件
            config_data = self.dao.read_yaml_config()
            
            # 尝试重新加载全局配置实例
            try:
                # 这里需要重新实例化配置对象
                # 由于 config 是全局单例，我们需要特殊处理
                global_config = get_config()
                
                # 更新配置实例的内部数据
                global_config._config = config_data
                
                reloaded_sections.append("config")
                logger.info("成功重载配置实例")
                
            except Exception as e:
                logger.warning("重载配置实例失败", error=str(e))
                requires_restart.append(ReloadRequirementSchema(
                    section="config",
                    requires_restart=True,
                    reason=f"配置实例重载失败: {str(e)}"
                ))
            
            # 检查哪些配置项需要重启服务
            restart_requirements = self._get_restart_requirements(config_data)
            requires_restart.extend(restart_requirements)
            
            response = ConfigReloadResponse(
                success=len(reloaded_sections) > 0,
                message=f"重载完成，{len(reloaded_sections)} 个配置节已生效",
                reloaded_sections=reloaded_sections,
                requires_restart=requires_restart
            )
            
            logger.info("配置重载完成", 
                       reloaded=len(reloaded_sections),
                       restart_required=len(requires_restart))
            
            return response
            
        except Exception as e:
            logger.error("配置重载失败", error=str(e))
            raise ConfigError(f"配置重载失败: {str(e)}")
    
    def _get_restart_requirements(self, config_data: Dict[str, Any]) -> List[ReloadRequirementSchema]:
        """
        获取需要重启的配置项
        
        参数:
            config_data (Dict[str, Any]): 配置数据
            
        返回:
            List[ReloadRequirementSchema]: 重启需求列表
        """
        requirements = []
        
        # 应用配置需要重启
        if "app" in config_data:
            requirements.append(ReloadRequirementSchema(
                section="app",
                requires_restart=True,
                reason="应用配置（host、port、debug）需要重启服务"
            ))
        
        # 数据库配置需要重启
        if "database" in config_data:
            requirements.append(ReloadRequirementSchema(
                section="database",
                requires_restart=True,
                reason="数据库连接池已初始化，需要重启服务"
            ))
        
        # LLM 模块配置可能需要重启（取决于实现）
        if "llm" in config_data:
            requirements.append(ReloadRequirementSchema(
                section="llm",
                requires_restart=True,
                reason="LLM 模块配置可能需要重新初始化 Agent"
            ))
        
        # 日志配置需要重启
        if "logging" in config_data:
            requirements.append(ReloadRequirementSchema(
                section="logging",
                requires_restart=True,
                reason="日志模块启动时初始化，需要重启服务"
            ))
        
        # 工具配置可能需要重启
        if "tools" in config_data:
            requirements.append(ReloadRequirementSchema(
                section="tools",
                requires_restart=True,
                reason="工具配置可能需要重新注册"
            ))
        
        return requirements
    
    def get_prompts(self) -> PromptListResponse:
        """
        获取所有提示词文件
        
        返回:
            PromptListResponse: 提示词列表响应
        """
        try:
            prompt_files = self.dao.list_prompt_files()
            prompts = []
            
            for file_info in prompt_files:
                try:
                    content = self.dao.read_prompt_file(file_info["filename"])
                    prompts.append({
                        "filename": file_info["filename"],
                        "content": content,
                        "category": file_info["category"],
                        "description": file_info["description"]
                    })
                except Exception as e:
                    logger.warning("读取提示词文件失败", 
                                 filename=file_info["filename"], 
                                 error=str(e))
                    continue
            
            response = PromptListResponse(prompts=prompts)
            
            logger.info("成功获取提示词列表", count=len(prompts))
            return response
            
        except Exception as e:
            logger.error("获取提示词列表失败", error=str(e))
            raise ConfigError(f"获取提示词列表失败: {str(e)}")
    
    def update_prompt(self, filename: str, update_request: PromptUpdateRequest) -> None:
        """
        更新提示词文件
        
        参数:
            filename (str): 文件名
            update_request (PromptUpdateRequest): 更新请求
            
        异常:
            ConfigError: 更新失败时抛出
        """
        try:
            # 验证文件名
            if not filename.endswith('.txt'):
                raise ConfigError("提示词文件必须是 .txt 格式")
            
            # 写入文件
            self.dao.write_prompt_file(filename, update_request.content)
            
            logger.info("成功更新提示词文件", filename=filename)
            
        except Exception as e:
            logger.error("更新提示词文件失败", filename=filename, error=str(e))
            raise ConfigError(f"更新提示词文件失败: {str(e)}")
    
    def get_roles(self) -> RoleListResponse:
        """
        获取角色配置列表
        
        返回:
            RoleListResponse: 角色列表响应
        """
        try:
            role_configs = self.dao.read_role_configs()
            
            response = RoleListResponse(roles=role_configs)
            
            logger.info("成功获取角色配置列表", count=len(role_configs))
            return response
            
        except Exception as e:
            logger.error("获取角色配置列表失败", error=str(e))
            raise ConfigError(f"获取角色配置列表失败: {str(e)}")
    
    def validate_config(self, config_data: Dict[str, Any]) -> bool:
        """
        验证配置有效性
        
        参数:
            config_data (Dict[str, Any]): 配置数据
            
        返回:
            bool: 是否有效
        """
        try:
            # 结构验证
            if not self.dao.validate_config_structure(config_data):
                return False
            
            # 业务逻辑验证
            return self._validate_business_logic(config_data)
            
        except Exception as e:
            logger.error("配置验证失败", error=str(e))
            return False
    
    def _validate_business_logic(self, config_data: Dict[str, Any]) -> bool:
        """
        验证配置的业务逻辑
        
        参数:
            config_data (Dict[str, Any]): 配置数据
            
        返回:
            bool: 是否有效
        """
        try:
            # 验证应用配置
            app_config = config_data.get("app", {})
            if app_config.get("port", 0) <= 0 or app_config.get("port", 0) > 65535:
                logger.error("应用端口配置无效", port=app_config.get("port"))
                return False
            
            # 验证数据库配置
            db_config = config_data.get("database", {}).get("mysql", {})
            if db_config.get("pool_size", 0) <= 0:
                logger.error("数据库连接池大小无效", pool_size=db_config.get("pool_size"))
                return False
            
            # 验证 LLM 配置
            llm_config = config_data.get("llm", {})
            default_provider = llm_config.get("default_provider")
            providers = llm_config.get("providers", {})
            
            if default_provider not in providers:
                logger.error("默认 LLM 提供商未配置", provider=default_provider)
                return False
            
            # 验证模块配置
            module_configs = llm_config.get("module_configs", {})
            for module_name, module_config in module_configs.items():
                provider = module_config.get("provider")
                if provider not in providers:
                    logger.error("模块 LLM 提供商未配置", 
                               module=module_name, 
                               provider=provider)
                    return False
            
            # 验证记忆配置
            memory_config = config_data.get("memory", {})
            if memory_config.get("max_recent_messages", 0) <= 0:
                logger.error("最大消息数配置无效", 
                           max_messages=memory_config.get("max_recent_messages"))
                return False
            
            logger.info("配置业务逻辑验证通过")
            return True
            
        except Exception as e:
            logger.error("配置业务逻辑验证失败", error=str(e))
            return False
    
    def get_reload_requirements(self) -> List[ReloadRequirementSchema]:
        """
        获取配置重载需求信息
        
        返回:
            List[ReloadRequirementSchema]: 重载需求列表
        """
        try:
            config_data = self.dao.read_yaml_config()
            return self._get_restart_requirements(config_data)
            
        except Exception as e:
            logger.error("获取重载需求失败", error=str(e))
            return []
