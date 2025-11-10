"""
文件名: base.py
功能: 工具基类，定义统一的工具接口（基于 LangChain Tool）
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool as LangChainBaseTool

from app.utils.logger import get_logger
from app.utils.exceptions import ToolExecutionError

logger = get_logger(__name__)


class ToolInput(BaseModel):
    """
    工具输入基类
    
    所有工具的输入都应继承此类，定义工具参数的 Pydantic 模型。
    """
    pass


class AgentTool(LangChainBaseTool):
    """
    Agent 工具基类
    
    基于 LangChain 的 BaseTool，提供统一的工具接口。
    所有自定义工具都应继承此类。
    
    属性:
        name (str): 工具名称
        description (str): 工具描述
        args_schema (Type[BaseModel]): 参数 Schema
    """
    
    # 工具元信息（子类需要设置）
    name: str = "base_tool"
    description: str = "基础工具"
    args_schema: Type[BaseModel] = ToolInput
    
    # Pydantic 配置：允许额外属性
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"
    
    def __init__(self, **kwargs):
        """初始化工具"""
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 验证
        object.__setattr__(self, 'logger', get_logger(f"{__name__}.{self.name}"))
    
    def _run(self, **kwargs: Any) -> Any:
        """
        同步执行工具（必须实现）
        
        参数:
            **kwargs: 工具参数
        
        返回:
            Any: 工具执行结果
        """
        try:
            self.logger.info(
                "工具开始执行",
                tool=self.name,
                params=kwargs
            )
            
            # 调用实际的执行逻辑
            result = self.execute(**kwargs)
            
            self.logger.info(
                "工具执行成功",
                tool=self.name,
                result_type=type(result).__name__
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "工具执行失败",
                tool=self.name,
                error=str(e),
                exc_info=True
            )
            raise ToolExecutionError(
                f"工具 {self.name} 执行失败: {str(e)}",
                tool_name=self.name,
                details={"params": kwargs, "error": str(e)}
            )
    
    async def _arun(self, **kwargs: Any) -> Any:
        """
        异步执行工具（可选实现）
        
        默认调用同步方法。如果工具支持异步，可以重写此方法。
        """
        return self._run(**kwargs)
    
    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        工具执行逻辑（抽象方法，子类必须实现）
        
        参数:
            **kwargs: 工具参数
        
        返回:
            Any: 执行结果
        """
        pass
    
    def get_tool_info(self) -> Dict[str, Any]:
        """
        获取工具信息
        
        返回:
            Dict[str, Any]: 工具信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema() if self.args_schema else {}
        }

