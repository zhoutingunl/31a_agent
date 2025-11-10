"""
反思模块 - 实现Agent的自我评估与纠错能力

这个模块提供了：
- 质量评分器：多维度评估输出质量
- 批评者：识别输出中的问题
- 自我纠错器：生成改进建议
- 反思循环：迭代优化执行结果
"""

from .schemas import (
    QualityDimension,
    QualityScore,
    CriticFeedback,
    CorrectionSuggestion,
    ReflectionResult
)

from .quality_scorer import QualityScorer
from .critic import Critic
from .self_corrector import SelfCorrector

__all__ = [
    # 数据结构
    "QualityDimension",
    "QualityScore", 
    "CriticFeedback",
    "CorrectionSuggestion",
    "ReflectionResult",
    
    # 核心组件
    "QualityScorer",
    "Critic",
    "SelfCorrector",
]
