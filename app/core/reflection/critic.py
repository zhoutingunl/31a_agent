"""
批评者模块 - 评估Agent输出质量

功能：
- 使用LLM评估Agent输出
- 识别错误和问题
- 提供建设性反馈
- 判断是否需要纠错
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.core.reflection.schemas import (
    CriticFeedback, ExecutionContext, QualityDimension, QualityScore
)
from app.core.reflection.quality_scorer import QualityScorer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Critic:
    """
    批评者
    
    功能：
    - 使用LLM评估Agent输出
    - 识别错误和问题
    - 提供建设性反馈
    - 判断是否需要纠错
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化批评者
        
        参数:
            llm: LLM实例
        """
        self.llm = llm
        self.quality_scorer = QualityScorer(llm)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # 批评者提示词
        self.critic_prompt = """你是一个严格的批评者，负责评估AI Agent的输出质量。

任务描述: {task_description}
期望目标: {expected_goal}
Agent输出: {agent_output}
约束条件: {constraints}

请从以下维度严格评估输出质量：

1. **正确性 (Correctness)**: 
   - 输出是否正确解决了问题？
   - 是否包含逻辑错误、语法错误或事实错误？
   - 是否遵循了最佳实践？

2. **完整性 (Completeness)**:
   - 是否涵盖了所有要求？
   - 是否遗漏了重要信息或步骤？
   - 是否提供了完整的解决方案？

3. **效率 (Efficiency)**:
   - 解决方案是否高效？
   - 是否使用了最优的方法？
   - 是否有不必要的冗余？

4. **清晰度 (Clarity)**:
   - 输出是否易于理解？
   - 结构是否清晰？
   - 语言是否准确？

请以JSON格式返回详细的评估结果：
{{
    "overall_score": 0.75,
    "dimension_scores": [
        {{
            "dimension": "correctness",
            "score": 0.8,
            "explanation": "基本正确，但存在一个小错误..."
        }},
        {{
            "dimension": "completeness",
            "score": 0.7,
            "explanation": "涵盖了主要要求，但缺少..."
        }},
        {{
            "dimension": "efficiency", 
            "score": 0.8,
            "explanation": "解决方案合理，但可以优化..."
        }},
        {{
            "dimension": "clarity",
            "score": 0.7,
            "explanation": "结构清晰，但某些部分可以更简洁..."
        }}
    ],
    "issues": [
        "具体问题1：描述问题详情",
        "具体问题2：描述问题详情"
    ],
    "strengths": [
        "优点1：做得好的地方",
        "优点2：做得好的地方"
    ],
    "needs_correction": true,
    "correction_priority": "high|medium|low",
    "detailed_feedback": "详细的反馈文本，包括具体的改进建议"
}}

请确保：
1. 评分客观公正，基于事实而非主观判断
2. 问题描述具体明确，便于改进
3. 提供建设性的改进建议
4. 识别输出中的真正问题，避免过度批评"""

    async def evaluate(self, 
                      output: str, 
                      context: ExecutionContext) -> CriticFeedback:
        """
        评估Agent输出
        
        参数:
            output: Agent输出内容
            context: 执行上下文
            
        返回:
            CriticFeedback: 批评反馈
        """
        try:
            self.logger.info(f"开始批评评估，任务: {context.task_description[:50]}...")
            
            # 1. 使用质量评分器进行基础评估
            quality_feedback = await self.quality_scorer.score_output(output, context)
            
            # 2. 使用LLM进行深度批评评估
            critic_feedback = await self._llm_critic_evaluation(output, context)
            
            # 3. 综合两种评估结果
            final_feedback = self._combine_evaluations(quality_feedback, critic_feedback, output, context)
            
            self.logger.info(f"批评评估完成，总分: {final_feedback.overall_score:.2f}, 需要纠错: {final_feedback.needs_correction}")
            return final_feedback
            
        except Exception as e:
            self.logger.error(f"批评评估失败: {e}")
            return self._create_error_feedback(output, context, str(e))

    async def _llm_critic_evaluation(self, 
                                   output: str, 
                                   context: ExecutionContext) -> Dict[str, Any]:
        """
        使用LLM进行批评评估
        
        参数:
            output: 输出内容
            context: 执行上下文
            
        返回:
            Dict[str, Any]: LLM评估结果
        """
        try:
            # 构建提示词
            prompt = self.critic_prompt.format(
                task_description=context.task_description,
                expected_goal=context.expected_goal,
                agent_output=output,
                constraints=", ".join(context.constraints) if context.constraints else "无"
            )
            
            # 调用LLM
            response = await self.llm.achat(prompt)
            
            # 解析JSON响应
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
                else:
                    raise ValueError("无法解析LLM响应为JSON")
                    
        except Exception as e:
            self.logger.error(f"LLM批评评估失败: {e}")
            return self._create_fallback_critic_result()

    def _combine_evaluations(self, 
                           quality_feedback: CriticFeedback,
                           critic_result: Dict[str, Any],
                           output: str,
                           context: ExecutionContext) -> CriticFeedback:
        """
        综合质量评分和批评评估
        
        参数:
            quality_feedback: 质量评分反馈
            critic_result: 批评评估结果
            output: 输出内容
            context: 执行上下文
            
        返回:
            CriticFeedback: 综合反馈
        """
        # 提取批评评估的维度评分
        critic_dimension_scores = []
        if "dimension_scores" in critic_result:
            for dim_score in critic_result["dimension_scores"]:
                dimension = dim_score.get("dimension", "")
                score = dim_score.get("score", 0.5)
                explanation = dim_score.get("explanation", "")
                
                try:
                    critic_dimension_scores.append(QualityScore(
                        dimension=QualityDimension(dimension),
                        score=score,
                        explanation=explanation
                    ))
                except ValueError:
                    # 如果维度名称无效，跳过
                    continue
        
        # 综合评分（质量评分权重0.4，批评评估权重0.6）
        final_dimension_scores = []
        for quality_score in quality_feedback.dimension_scores:
            # 查找对应的批评评分
            critic_score = None
            for cs in critic_dimension_scores:
                if cs.dimension == quality_score.dimension:
                    critic_score = cs
                    break
            
            if critic_score:
                # 综合评分
                final_score = quality_score.score * 0.4 + critic_score.score * 0.6
                final_explanation = f"质量评分: {quality_score.score:.2f}, 批评评分: {critic_score.score:.2f}. {critic_score.explanation}"
            else:
                # 如果没有批评评分，使用质量评分
                final_score = quality_score.score
                final_explanation = quality_score.explanation
            
            final_dimension_scores.append(QualityScore(
                dimension=quality_score.dimension,
                score=final_score,
                explanation=final_explanation
            ))
        
        # 计算总体评分
        overall_score = sum(score.score for score in final_dimension_scores) / len(final_dimension_scores)
        
        # 合并问题和优点
        issues = list(set(quality_feedback.issues + critic_result.get("issues", [])))
        strengths = list(set(quality_feedback.strengths + critic_result.get("strengths", [])))
        
        # 判断是否需要纠错
        needs_correction = (
            quality_feedback.needs_correction or 
            critic_result.get("needs_correction", False) or
            overall_score < 0.8
        )
        
        # 生成综合反馈文本
        feedback_text = self._generate_comprehensive_feedback(
            overall_score, final_dimension_scores, issues, strengths, critic_result
        )
        
        return CriticFeedback(
            overall_score=overall_score,
            dimension_scores=final_dimension_scores,
            issues=issues,
            strengths=strengths,
            needs_correction=needs_correction,
            feedback_text=feedback_text
        )

    def _generate_comprehensive_feedback(self,
                                       overall_score: float,
                                       dimension_scores: List[QualityScore],
                                       issues: List[str],
                                       strengths: List[str],
                                       critic_result: Dict[str, Any]) -> str:
        """生成综合反馈文本"""
        feedback_parts = []
        
        # 总体评分
        feedback_parts.append(f"📊 总体评分: {overall_score:.2f}/1.0")
        
        # 各维度评分
        feedback_parts.append("\n📈 各维度评分:")
        for score in dimension_scores:
            emoji = self._get_dimension_emoji(score.dimension)
            feedback_parts.append(f"{emoji} {score.dimension.value}: {score.score:.2f} - {score.explanation}")
        
        # 优点
        if strengths:
            feedback_parts.append(f"\n✅ 优点:")
            for strength in strengths:
                feedback_parts.append(f"  • {strength}")
        
        # 问题
        if issues:
            feedback_parts.append(f"\n❌ 需要改进的问题:")
            for issue in issues:
                feedback_parts.append(f"  • {issue}")
        
        # 详细反馈
        if "detailed_feedback" in critic_result:
            feedback_parts.append(f"\n💡 详细建议:")
            feedback_parts.append(critic_result["detailed_feedback"])
        
        # 纠错优先级
        if "correction_priority" in critic_result:
            priority = critic_result["correction_priority"]
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
            feedback_parts.append(f"\n{priority_emoji} 纠错优先级: {priority}")
        
        return "\n".join(feedback_parts)

    def _get_dimension_emoji(self, dimension: QualityDimension) -> str:
        """获取维度对应的emoji"""
        emoji_map = {
            QualityDimension.CORRECTNESS: "🎯",
            QualityDimension.COMPLETENESS: "📋",
            QualityDimension.EFFICIENCY: "⚡",
            QualityDimension.CLARITY: "💡"
        }
        return emoji_map.get(dimension, "📊")

    def _create_error_feedback(self, output: str, context: ExecutionContext, error: str) -> CriticFeedback:
        """创建错误反馈（当评估失败时）"""
        return CriticFeedback(
            overall_score=0.2,
            dimension_scores=[
                QualityScore(
                    dimension=QualityDimension.CORRECTNESS,
                    score=0.2,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.COMPLETENESS,
                    score=0.2,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.EFFICIENCY,
                    score=0.2,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.CLARITY,
                    score=0.2,
                    explanation=f"评估失败: {error}"
                )
            ],
            issues=[f"批评评估失败: {error}"],
            strengths=[],
            needs_correction=True,
            feedback_text=f"由于批评评估过程出错，无法准确评估输出质量。错误: {error}"
        )

    def _create_fallback_critic_result(self) -> Dict[str, Any]:
        """创建批评评估的备用结果"""
        return {
            "overall_score": 0.5,
            "dimension_scores": [
                {"dimension": "correctness", "score": 0.5, "explanation": "LLM批评评估失败，使用默认评分"},
                {"dimension": "completeness", "score": 0.5, "explanation": "LLM批评评估失败，使用默认评分"},
                {"dimension": "efficiency", "score": 0.5, "explanation": "LLM批评评估失败，使用默认评分"},
                {"dimension": "clarity", "score": 0.5, "explanation": "LLM批评评估失败，使用默认评分"}
            ],
            "issues": ["LLM批评评估失败"],
            "strengths": [],
            "needs_correction": True,
            "correction_priority": "medium",
            "detailed_feedback": "由于LLM评估失败，无法提供详细的批评反馈。"
        }

    async def quick_evaluate(self, output: str, context: ExecutionContext) -> bool:
        """
        快速评估是否需要纠错
        
        参数:
            output: 输出内容
            context: 执行上下文
            
        返回:
            bool: 是否需要纠错
        """
        try:
            # 使用简化的快速评估
            quick_prompt = f"""请快速评估以下输出是否需要纠错：

任务: {context.task_description}
输出: {output[:500]}...

请只回答 "YES" 或 "NO"，如果需要纠错回答YES，否则回答NO。"""
            
            response = await self.llm.achat(quick_prompt)
            return "YES" in response.upper()
            
        except Exception as e:
            self.logger.error(f"快速评估失败: {e}")
            return True  # 默认需要纠错

    def analyze_improvement_trend(self, 
                                history: List[CriticFeedback]) -> Dict[str, Any]:
        """
        分析改进趋势
        
        参数:
            history: 历史反馈列表
            
        返回:
            Dict[str, Any]: 改进趋势分析
        """
        if len(history) < 2:
            return {"trend": "insufficient_data", "improvement": 0.0}
        
        # 计算评分趋势
        scores = [feedback.overall_score for feedback in history]
        improvement = scores[-1] - scores[0]
        
        # 判断趋势
        if improvement > 0.1:
            trend = "improving"
        elif improvement < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "improvement": improvement,
            "current_score": scores[-1],
            "initial_score": scores[0],
            "score_history": scores
        }
