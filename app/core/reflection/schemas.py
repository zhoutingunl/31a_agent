"""
反思模块的数据结构定义

定义了反思与自我纠错过程中使用的所有数据模型
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class QualityDimension(str, Enum):
    """质量评估维度"""
    CORRECTNESS = "correctness"  # 正确性
    COMPLETENESS = "completeness"  # 完整性
    EFFICIENCY = "efficiency"  # 效率
    CLARITY = "clarity"  # 清晰度


class QualityScore(BaseModel):
    """质量评分"""
    dimension: QualityDimension
    score: float = Field(ge=0.0, le=1.0, description="评分，范围0-1")
    explanation: str = Field(description="评分说明")
    
    @validator('score')
    def validate_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('评分必须在0-1之间')
        return v


class CriticFeedback(BaseModel):
    """批评者反馈"""
    overall_score: float = Field(ge=0.0, le=1.0, description="总体评分")
    dimension_scores: List[QualityScore] = Field(description="各维度评分")
    issues: List[str] = Field(default_factory=list, description="发现的问题")
    strengths: List[str] = Field(default_factory=list, description="做得好的地方")
    needs_correction: bool = Field(description="是否需要纠错")
    feedback_text: str = Field(description="详细反馈文本")
    
    @validator('overall_score')
    def validate_overall_score(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('总体评分必须在0-1之间')
        return v


class CorrectionSuggestion(BaseModel):
    """纠错建议"""
    issue: str = Field(description="问题描述")
    suggestion: str = Field(description="改进建议")
    priority: int = Field(ge=1, le=5, description="优先级，1-5，5最高")
    expected_improvement: str = Field(description="预期改进效果")
    
    @validator('priority')
    def validate_priority(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('优先级必须在1-5之间')
        return v


class ReflectionResult(BaseModel):
    """反思结果"""
    task_id: int = Field(description="任务ID")
    feedback: CriticFeedback = Field(description="批评反馈")
    suggestions: List[CorrectionSuggestion] = Field(description="纠错建议")
    should_retry: bool = Field(description="是否应该重试")
    retry_count: int = Field(ge=0, description="当前重试次数")
    max_retries: int = Field(ge=1, description="最大重试次数")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    @validator('retry_count')
    def validate_retry_count(cls, v):
        if v < 0:
            raise ValueError('重试次数不能为负数')
        return v


class ExecutionContext(BaseModel):
    """执行上下文"""
    task_description: str = Field(description="任务描述")
    expected_goal: str = Field(description="期望目标")
    constraints: List[str] = Field(default_factory=list, description="约束条件")
    context_info: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class ReflectionHistory(BaseModel):
    """反思历史记录"""
    task_id: int = Field(description="任务ID")
    iteration: int = Field(ge=1, description="迭代次数")
    output: str = Field(description="输出内容")
    feedback: CriticFeedback = Field(description="反馈")
    suggestions: List[CorrectionSuggestion] = Field(description="建议")
    improvement_score: Optional[float] = Field(description="改进评分")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class ReflectionConfig(BaseModel):
    """反思配置"""
    max_retries: int = Field(default=3, ge=1, le=10, description="最大重试次数")
    quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="质量阈值")
    enable_auto_correction: bool = Field(default=True, description="是否启用自动纠错")
    critic_model: str = Field(default="deepseek", description="批评者使用的模型")
    corrector_model: str = Field(default="deepseek", description="纠错器使用的模型")
    
    @validator('quality_threshold')
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('质量阈值必须在0-1之间')
        return v
