"""
文件名: config.py
功能: 配置管理相关的 Pydantic Schema 定义
映射 config.yaml 的所有配置项，用于 API 数据验证和序列化
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator, ConfigDict
from enum import Enum


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """日志格式枚举"""
    SIMPLE = "simple"
    DETAILED = "detailed"


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    QIANFAN = "qianfan"
    TONGYI = "tongyi"


class ModuleType(str, Enum):
    """LLM 模块类型枚举"""
    ORCHESTRATOR = "orchestrator"
    PLANNER = "planner"
    REFLECTION = "reflection"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    TOOLS = "tools"
    ROUTER = "router"


# ==================== 应用配置 ====================
class AppConfigSchema(BaseModel):
    """应用配置 Schema"""
    name: str = Field(..., description="应用名称")
    version: str = Field(..., description="应用版本")
    host: str = Field(..., description="服务器主机地址")
    port: int = Field(..., ge=1, le=65535, description="服务器端口")
    debug: bool = Field(..., description="调试模式")


# ==================== 数据库配置 ====================
class MySQLConfigSchema(BaseModel):
    """MySQL 数据库配置 Schema"""
    host: str = Field(..., description="数据库主机")
    port: int = Field(3306, ge=1, le=65535, description="数据库端口")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")
    pool_size: int = Field(10, ge=1, le=100, description="连接池大小")
    pool_recycle: int = Field(3600, ge=60, description="连接回收时间（秒）")
    echo: bool = Field(False, description="是否打印 SQL")


class ChromaConfigSchema(BaseModel):
    """Chroma 向量数据库配置 Schema"""
    persist_directory: str = Field(..., description="持久化目录")
    collection_name: str = Field(..., description="集合名称")


class DatabaseConfigSchema(BaseModel):
    """数据库配置 Schema"""
    mysql: MySQLConfigSchema = Field(..., description="MySQL 配置")
    chroma: Optional[ChromaConfigSchema] = Field(None, description="Chroma 配置")


# ==================== LLM 配置 ====================
class LLMProviderConfigSchema(BaseModel):
    """LLM 提供商配置 Schema"""
    api_key: Optional[str] = Field(None, description="API 密钥")
    base_url: Optional[str] = Field(None, description="API 基础地址")
    model: Optional[str] = Field(None, description="模型名称")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="最大 Token 数")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="超时时间（秒）")
    secret_key: Optional[str] = Field(None, description="密钥（千帆专用）")


class LLMModuleConfigSchema(BaseModel):
    """模块级 LLM 配置 Schema"""
    provider: LLMProvider = Field(..., description="提供商")
    model: str = Field(..., description="模型名称")
    temperature: float = Field(..., ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(..., ge=1, le=8192, description="最大 Token 数")


class LLMConfigSchema(BaseModel):
    """LLM 配置 Schema"""
    default_provider: LLMProvider = Field(..., description="默认提供商")
    module_configs: Dict[ModuleType, LLMModuleConfigSchema] = Field(..., description="模块级配置")
    providers: Dict[LLMProvider, LLMProviderConfigSchema] = Field(..., description="提供商配置")


# ==================== 记忆管理配置 ====================
class MemoryConfigSchema(BaseModel):
    """记忆管理配置 Schema"""
    max_recent_messages: int = Field(..., ge=1, le=1000, description="保留最近消息数")
    compression_threshold: int = Field(..., ge=1, le=1000, description="压缩阈值")
    summary_interval: int = Field(..., ge=1, le=100, description="摘要间隔")


# ==================== 工具配置 ====================
class PowerShellConfigSchema(BaseModel):
    """PowerShell 工具配置 Schema"""
    security_level: int = Field(..., ge=0, le=3, description="安全等级：0=禁用, 1=只读, 2=文件操作, 3=完全权限")
    timeout: int = Field(..., ge=1, le=300, description="执行超时（秒）")


class DatabaseToolConfigSchema(BaseModel):
    """数据库工具配置 Schema"""
    max_rows: int = Field(..., ge=1, le=10000, description="最多返回行数")
    timeout: int = Field(..., ge=1, le=60, description="超时时间（秒）")


class FileToolConfigSchema(BaseModel):
    """文件工具配置 Schema"""
    max_size: int = Field(..., ge=1024, le=104857600, description="最大文件大小（字节）")
    allowed_extensions: List[str] = Field(..., description="允许的文件扩展名")


class RetryConfigSchema(BaseModel):
    """重试配置 Schema"""
    max_attempts: int = Field(..., ge=1, le=10, description="最大重试次数")
    delay: int = Field(..., ge=1, le=60, description="重试延迟（秒）")


class ToolsConfigSchema(BaseModel):
    """工具配置 Schema"""
    powershell: PowerShellConfigSchema = Field(..., description="PowerShell 配置")
    database: DatabaseToolConfigSchema = Field(..., description="数据库工具配置")
    file: FileToolConfigSchema = Field(..., description="文件工具配置")
    retry: RetryConfigSchema = Field(..., description="重试配置")


# ==================== 文件上传配置 ====================
class UploadConfigSchema(BaseModel):
    """文件上传配置 Schema"""
    max_size: int = Field(..., ge=1024, le=1073741824, description="最大文件大小（字节）")
    allowed_types: List[str] = Field(..., description="允许的文件类型")
    storage_path: str = Field(..., description="存储路径")


# ==================== 日志配置 ====================
class LogFileConfigSchema(BaseModel):
    """日志文件配置 Schema"""
    enabled: bool = Field(..., description="是否启用文件日志")
    path: str = Field(..., description="日志文件路径")
    max_size: int = Field(..., ge=1024, le=1073741824, description="最大文件大小（字节）")
    backup_count: int = Field(..., ge=1, le=100, description="备份文件数量")


class LogConsoleConfigSchema(BaseModel):
    """控制台日志配置 Schema"""
    enabled: bool = Field(..., description="是否启用控制台日志")
    colorize: bool = Field(..., description="是否彩色输出")


class LoggingConfigSchema(BaseModel):
    """日志配置 Schema"""
    level: LogLevel = Field(..., description="日志级别")
    format: LogFormat = Field(..., description="日志格式")
    file: LogFileConfigSchema = Field(..., description="文件日志配置")
    console: LogConsoleConfigSchema = Field(..., description="控制台日志配置")


# ==================== 提示词文件配置 ====================
class PromptFileSchema(BaseModel):
    """提示词文件 Schema"""
    filename: str = Field(..., description="文件名")
    content: str = Field(..., description="文件内容")
    category: Optional[str] = Field(None, description="文件分类")
    description: Optional[str] = Field(None, description="文件描述")


# ==================== 角色配置 ====================
class MemoryStrategySchema(BaseModel):
    """记忆策略配置 Schema"""
    short_term: bool = Field(..., description="启用短期记忆")
    long_term: bool = Field(..., description="启用长期记忆")
    knowledge_graph: bool = Field(..., description="启用知识图谱")
    user_isolated: bool = Field(..., description="用户隔离")
    rag_enabled: bool = Field(..., description="启用 RAG")
    retention_days: int = Field(..., ge=1, le=365, description="记忆保留天数")


class ModelConfigSchema(BaseModel):
    """模型配置 Schema"""
    provider: LLMProvider = Field(..., description="提供商")
    model: str = Field(..., description="模型名称")
    temperature: float = Field(..., ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(..., ge=1, le=8192, description="最大 Token 数")


class SecurityConfigSchema(BaseModel):
    """安全配置 Schema"""
    powershell_mode: Optional[str] = Field(None, description="PowerShell 模式")
    powershell_whitelist: Optional[List[str]] = Field(None, description="PowerShell 白名单")


class RoleConfigSchema(BaseModel):
    """角色配置 Schema"""
    model_config = ConfigDict(extra='ignore')
    
    name: str = Field(..., description="角色名称")
    type: str = Field(..., description="角色类型")
    description: str = Field(..., description="角色描述")
    system_prompt: str = Field("", description="系统提示词")
    allowed_tools: List[str] = Field(..., description="允许的工具")
    memory_strategy: MemoryStrategySchema = Field(..., description="记忆策略")
    llm_config: Optional[ModelConfigSchema] = Field(None, description="模型配置")
    security_config: Optional[SecurityConfigSchema] = Field(None, description="安全配置")


# ==================== 完整配置响应 ====================
class ConfigResponse(BaseModel):
    """完整配置响应 Schema"""
    app: AppConfigSchema = Field(..., description="应用配置")
    database: DatabaseConfigSchema = Field(..., description="数据库配置")
    llm: LLMConfigSchema = Field(..., description="LLM 配置")
    memory: MemoryConfigSchema = Field(..., description="记忆配置")
    tools: ToolsConfigSchema = Field(..., description="工具配置")
    upload: UploadConfigSchema = Field(..., description="上传配置")
    logging: LoggingConfigSchema = Field(..., description="日志配置")


# ==================== 配置更新请求 ====================
class ConfigUpdateRequest(BaseModel):
    """配置更新请求 Schema"""
    app: Optional[AppConfigSchema] = None
    database: Optional[DatabaseConfigSchema] = None
    llm: Optional[LLMConfigSchema] = None
    memory: Optional[MemoryConfigSchema] = None
    tools: Optional[ToolsConfigSchema] = None
    upload: Optional[UploadConfigSchema] = None
    logging: Optional[LoggingConfigSchema] = None


# ==================== 配置重载响应 ====================
class ReloadRequirementSchema(BaseModel):
    """重载需求 Schema"""
    section: str = Field(..., description="配置节")
    requires_restart: bool = Field(..., description="是否需要重启")
    reason: str = Field(..., description="原因说明")


class ConfigReloadResponse(BaseModel):
    """配置重载响应 Schema"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    reloaded_sections: List[str] = Field(..., description="已重载的配置节")
    requires_restart: List[ReloadRequirementSchema] = Field(..., description="需要重启的配置")


# ==================== 提示词管理 ====================
class PromptUpdateRequest(BaseModel):
    """提示词更新请求 Schema"""
    content: str = Field(..., description="提示词内容")


class PromptListResponse(BaseModel):
    """提示词列表响应 Schema"""
    prompts: List[PromptFileSchema] = Field(..., description="提示词文件列表")


# ==================== 角色管理 ====================
class RoleListResponse(BaseModel):
    """角色列表响应 Schema"""
    roles: List[RoleConfigSchema] = Field(..., description="角色配置列表")
