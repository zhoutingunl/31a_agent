"""
角色配置类

定义角色配置的数据结构和加载逻辑
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryStrategy(BaseModel):
    """
    记忆策略配置
    
    定义角色的记忆使用策略
    """
    short_term: bool = Field(True, description="是否启用短期记忆")
    long_term: bool = Field(True, description="是否启用长期记忆")
    knowledge_graph: bool = Field(True, description="是否启用知识图谱")
    user_isolated: bool = Field(True, description="是否用户隔离")
    rag_enabled: bool = Field(False, description="是否启用RAG知识库")
    retention_days: int = Field(90, description="记忆保留天数")


class ModelConfig(BaseModel):
    """
    模型配置
    
    定义角色使用的模型配置
    """
    provider: str = Field("deepseek", description="模型提供商")
    model: str = Field("deepseek-chat", description="模型名称")
    temperature: float = Field(0.7, description="温度参数")
    max_tokens: int = Field(4096, description="最大token数")


class PromptConfig(BaseModel):
    """
    提示词配置
    
    定义角色使用的各种提示词
    """
    system: str = Field("", description="系统提示词")
    planner: str = Field("", description="规划模块提示词")
    reflection: str = Field("", description="反思模块提示词")
    memory: str = Field("", description="记忆模块提示词")
    knowledge: str = Field("", description="知识模块提示词")
    tools: str = Field("", description="工具模块提示词")
    router: str = Field("", description="路由模块提示词")


class SecurityConfig(BaseModel):
    """
    安全配置
    
    定义角色的安全策略
    """
    powershell_whitelist: List[str] = Field(default_factory=list, description="PowerShell 命令白名单")
    powershell_mode: str = Field("restricted", description="PowerShell 安全模式：restricted（限制危险命令）或 whitelist（仅白名单）")


class RoleConfig(BaseModel):
    """
    角色配置
    
    包含角色的所有配置信息
    """
    name: str = Field(..., description="角色名称")
    type: str = Field(..., description="角色类型标识")
    description: str = Field("", description="角色描述")
    system_prompt: str = Field("", description="系统提示词（兼容性字段）")
    allowed_tools: List[str] = Field(default_factory=lambda: ["*"], description="允许的工具列表")
    memory_strategy: MemoryStrategy = Field(default_factory=MemoryStrategy, description="记忆策略")
    
    # 新增配置
    model_config: Optional[ModelConfig] = Field(None, description="模型配置")
    prompt_config: Optional[PromptConfig] = Field(None, description="提示词配置")
    security_config: Optional[SecurityConfig] = Field(None, description="安全配置")
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "RoleConfig":
        """
        从YAML文件加载角色配置
        
        Args:
            yaml_path: YAML文件路径
            
        Returns:
            RoleConfig: 角色配置对象
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 处理memory_strategy
            if 'memory_strategy' in data and isinstance(data['memory_strategy'], dict):
                data['memory_strategy'] = MemoryStrategy(**data['memory_strategy'])
            
            # 处理model_config
            if 'model_config' in data and isinstance(data['model_config'], dict):
                data['model_config'] = ModelConfig(**data['model_config'])
            
            # 处理prompt_config
            if 'prompt_config' in data and isinstance(data['prompt_config'], dict):
                data['prompt_config'] = PromptConfig(**data['prompt_config'])
            
            # 加载提示词文件
            cls._load_prompts_from_files(data, yaml_path)
            
            config = cls(**data)
            logger.info(f"角色配置加载成功: {config.name} ({config.type})")
            return config
            
        except FileNotFoundError:
            logger.error(f"角色配置文件不存在: {yaml_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML解析失败: {e}")
            raise
        except Exception as e:
            logger.error(f"加载角色配置失败: {e}")
            raise
    
    @classmethod
    def _load_prompts_from_files(cls, data: dict, yaml_path: str):
        """
        从提示词文件加载提示词内容
        
        Args:
            data: 配置数据字典
            yaml_path: YAML文件路径
        """
        try:
            from pathlib import Path
            
            # 获取角色类型
            role_type = data.get('type', 'general')
            # 提示词文件在项目根目录的 config/prompts/ 目录下
            # 从 app/core/roles/configs/xxx.yaml 到 config/prompts/
            # 需要回到项目根目录
            project_root = Path(yaml_path).parent.parent.parent.parent.parent
            config_dir = project_root / "config" / "prompts"
            
            # 提示词文件映射
            prompt_files = {
                'system': f"{role_type}_system.txt",
                'planner': f"{role_type}_planner.txt", 
                'reflection': f"{role_type}_reflection.txt",
                'memory': f"{role_type}_memory.txt",
                'knowledge': f"{role_type}_knowledge.txt",
                'tools': f"{role_type}_tools.txt",
                'router': f"{role_type}_router.txt"
            }
            
            # 加载提示词文件
            loaded_prompts = {}
            logger.debug(f"提示词目录: {config_dir}")
            for prompt_type, filename in prompt_files.items():
                prompt_file = config_dir / filename
                logger.debug(f"检查提示词文件: {prompt_file}")
                if prompt_file.exists():
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        loaded_prompts[prompt_type] = f.read().strip()
                        logger.info(f"加载提示词文件成功: {filename}")
                else:
                    logger.debug(f"提示词文件不存在: {filename}")
            
            # 更新配置数据
            if loaded_prompts:
                if 'prompt_config' not in data or data['prompt_config'] is None:
                    data['prompt_config'] = {}
                data['prompt_config'].update(loaded_prompts)
                
                # 兼容性：如果system_prompt为空，使用system提示词
                if not data.get('system_prompt') and 'system' in loaded_prompts:
                    data['system_prompt'] = loaded_prompts['system']
                    
        except Exception as e:
            logger.warning(f"加载提示词文件失败: {e}")
            # 不影响主配置加载
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否被允许使用
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否允许
        """
        # 如果包含通配符，允许所有工具
        if "*" in self.allowed_tools:
            return True
        
        # 检查完全匹配
        if tool_name in self.allowed_tools:
            return True
        
        # 检查前缀匹配（如 mysql_* 匹配 mysql_query）
        for pattern in self.allowed_tools:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if tool_name.startswith(prefix):
                    return True
        
        return False
    
    def get_prompt(self, module: str) -> str:
        """
        获取指定模块的提示词
        
        Args:
            module: 模块名称 (system, planner, reflection, memory, knowledge, tools, router)
            
        Returns:
            str: 提示词内容
        """
        if self.prompt_config:
            return getattr(self.prompt_config, module, "")
        
        # 兼容性：返回系统提示词
        if module == "system":
            return self.system_prompt
        
        return ""
    
    def get_model_config(self, module: str) -> Optional[ModelConfig]:
        """
        获取指定模块的模型配置
        
        Args:
            module: 模块名称
            
        Returns:
            Optional[ModelConfig]: 模型配置，如果未配置则返回None
        """
        return self.model_config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return self.model_dump()
    
    model_config = {"extra": "allow"}  # 允许额外字段
