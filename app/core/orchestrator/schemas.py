"""
编排器数据结构

定义编排器相关的数据模型和枚举类型
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """
    执行模式枚举
    
    定义Agent的执行模式
    """
    SIMPLE = "simple"           # 简单对话模式（ToolAgent）
    PLANNING = "planning"       # 规划模式（PlannerAgent）
    REFLECTION = "reflection"   # 反思模式（ExecutorAgent）


class ExecutionState(str, Enum):
    """
    执行状态枚举
    
    定义任务执行的状态
    """
    IDLE = "IDLE"               # 空闲
    ROUTING = "ROUTING"         # 路由中
    EXECUTING = "EXECUTING"     # 执行中
    COMPLETED = "COMPLETED"     # 已完成
    ERROR = "ERROR"             # 错误
    RECOVERING = "RECOVERING"   # 恢复中


class OrchestratorRequest(BaseModel):
    """
    编排器请求
    
    封装用户请求和执行参数
    """
    content: str = Field(..., description="用户请求内容")
    conversation_id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    mode: Optional[ExecutionMode] = Field(None, description="执行模式（可选，不指定则自动路由）")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    
    class Config:
        """Pydantic配置"""
        use_enum_values = True


class RouteDecision(BaseModel):
    """
    路由决策结果
    
    记录路由决策的详细信息
    """
    mode: ExecutionMode = Field(..., description="选择的执行模式")
    confidence: float = Field(..., description="决策置信度")
    reason: str = Field(..., description="决策原因")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="分析详情")


class OrchestratorResponse(BaseModel):
    """
    编排器响应
    
    封装执行结果和元数据
    """
    success: bool = Field(..., description="是否成功")
    content: str = Field(..., description="响应内容")
    mode: ExecutionMode = Field(..., description="使用的执行模式")
    execution_time: float = Field(..., description="执行耗时（秒）")
    state_history: List[Dict[str, Any]] = Field(default_factory=list, description="状态转换历史")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        """Pydantic配置"""
        use_enum_values = True


class StateTransition(BaseModel):
    """
    状态转换记录
    
    记录状态机的转换历史
    """
    from_state: ExecutionState = Field(..., description="源状态")
    to_state: ExecutionState = Field(..., description="目标状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="转换时间")
    context: Dict[str, Any] = Field(default_factory=dict, description="转换上下文")
    
    class Config:
        """Pydantic配置"""
        use_enum_values = True
