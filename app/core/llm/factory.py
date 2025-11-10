"""
文件名: factory.py
功能: LLM 工厂类，根据配置创建对应的 LLM 实例
"""

from typing import Optional

from app.core.llm.base import BaseLLM
from app.core.llm.deepseek import DeepSeekLLM
from app.utils.config import config
from app.utils.logger import get_logger
from app.utils.exceptions import ConfigError

logger = get_logger(__name__)


def create_llm(provider: Optional[str] = None, module: Optional[str] = None, 
                model: Optional[str] = None, temperature: Optional[float] = None,
                max_tokens: Optional[int] = None) -> BaseLLM:
    """
    创建 LLM 实例（工厂函数）
    
    根据配置文件中的设置，创建对应的 LLM 实例。
    支持多种 LLM 提供商：DeepSeek、Ollama、千帆、通义等。
    支持模块级配置，不同模块可以使用不同的模型参数。
    
    参数:
        provider (str, optional): LLM 提供商名称，默认使用配置中的默认提供商
        module (str, optional): 模块名称，用于获取模块特定的配置
        model (str, optional): 模型名称，覆盖配置中的模型
        temperature (float, optional): 温度参数，覆盖配置中的温度
        max_tokens (int, optional): 最大token数，覆盖配置中的max_tokens
    
    返回:
        BaseLLM: LLM 实例
    
    异常:
        ConfigError: 配置缺失或提供商不支持时抛出
    
    示例:
        >>> llm = create_llm()  # 使用默认提供商
        >>> llm = create_llm("deepseek")  # 指定使用 DeepSeek
        >>> llm = create_llm(module="planner")  # 使用规划模块的配置
    """
    # 获取模块配置
    module_config = None
    if module:
        module_config = config.get(f"llm.module_configs.{module}")
        if module_config:
            logger.info(f"使用模块配置: {module}")
    
    # 获取提供商名称
    if provider is None:
        if module_config:
            provider = module_config.get("provider")
        if not provider:
            provider = config.get("llm.default_provider")
    
    if not provider:
        raise ConfigError(
            "未配置 LLM 提供商",
            details={"config_key": "llm.default_provider"}
        )
    
    # 获取模型参数
    if model is None and module_config:
        model = module_config.get("model")
    if temperature is None and module_config:
        temperature = module_config.get("temperature")
    if max_tokens is None and module_config:
        max_tokens = module_config.get("max_tokens")
    
    logger.info("正在创建 LLM 实例", provider=provider, module=module, model=model)
    
    # 根据提供商创建对应的 LLM
    if provider == "deepseek":
        return _create_deepseek_llm(model=model, temperature=temperature, max_tokens=max_tokens)
    elif provider == "ollama":
        raise ConfigError(
            "Ollama 支持暂未实现",
            details={"provider": provider}
        )
    elif provider == "qianfan":
        raise ConfigError(
            "百度千帆支持暂未实现",
            details={"provider": provider}
        )
    elif provider == "tongyi":
        raise ConfigError(
            "阿里通义支持暂未实现",
            details={"provider": provider}
        )
    else:
        raise ConfigError(
            f"不支持的 LLM 提供商: {provider}",
            details={
                "provider": provider,
                "supported": ["deepseek", "ollama", "qianfan", "tongyi"]
            }
        )


def _create_deepseek_llm(model: Optional[str] = None, temperature: Optional[float] = None,
                        max_tokens: Optional[int] = None) -> DeepSeekLLM:
    """
    创建 DeepSeek LLM 实例（内部函数）
    
    参数:
        model: 模型名称，覆盖配置中的模型
        temperature: 温度参数，覆盖配置中的温度
        max_tokens: 最大token数，覆盖配置中的max_tokens
    
    返回:
        DeepSeekLLM: DeepSeek LLM 实例
    
    异常:
        ConfigError: DeepSeek 配置缺失时抛出
    """
    # 获取 DeepSeek 配置
    api_key = config.get("llm.providers.deepseek.api_key")
    base_url = config.get("llm.providers.deepseek.base_url", "https://api.deepseek.com")
    timeout = config.get("llm.providers.deepseek.timeout", 60)
    
    # 使用传入参数或默认配置
    model_name = model or config.get("llm.providers.deepseek.model", "deepseek-chat")
    temp = temperature if temperature is not None else config.get("llm.providers.deepseek.temperature", 0.7)
    tokens = max_tokens or config.get("llm.providers.deepseek.max_tokens", 4096)
    
    # 验证必需配置
    if not api_key:
        raise ConfigError(
            "DeepSeek API Key 未配置",
            details={"config_key": "llm.providers.deepseek.api_key"}
        )
    
    # 创建 DeepSeek LLM
    llm = DeepSeekLLM(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=temp,
        max_tokens=tokens,
        timeout=timeout
    )
    
    logger.info(
        "DeepSeek LLM 创建成功",
        model=model_name,
        temperature=temp,
        max_tokens=tokens
    )
    
    return llm

