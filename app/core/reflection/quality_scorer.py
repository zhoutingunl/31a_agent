"""
质量评分器 - 多维度评估输出质量

功能：
- 基于规则和LLM的多维度质量评估
- 生成详细的评分报告
- 支持不同任务类型的定制化评估
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.core.reflection.schemas import (
    QualityDimension, QualityScore, CriticFeedback, ExecutionContext
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QualityScorer:
    """
    质量评分器
    
    功能：
    - 多维度评估输出质量
    - 结合规则引擎和LLM评估
    - 生成详细的评分报告
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化质量评分器
        
        参数:
            llm: LLM实例
        """
        self.llm = llm
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # 质量评估提示词
        self.quality_prompt = """你是一个专业的质量评估专家，负责评估AI Agent的输出质量。

任务描述: {task_description}
期望目标: {expected_goal}
Agent输出: {agent_output}
约束条件: {constraints}

请从以下四个维度评估输出质量，每个维度给出0-1的评分和详细说明：

1. **正确性 (Correctness)**: 输出是否正确解决了问题？是否包含错误？
2. **完整性 (Completeness)**: 是否涵盖了所有要求？是否遗漏了重要内容？
3. **效率 (Efficiency)**: 解决方案是否高效？是否使用了最佳实践？
4. **清晰度 (Clarity)**: 输出是否易于理解？结构是否清晰？

请以JSON格式返回评估结果：
{{
    "overall_score": 0.85,
    "dimension_scores": [
        {{
            "dimension": "correctness",
            "score": 0.9,
            "explanation": "输出正确解决了问题，没有明显错误"
        }},
        {{
            "dimension": "completeness", 
            "score": 0.8,
            "explanation": "涵盖了主要要求，但缺少一些细节"
        }},
        {{
            "dimension": "efficiency",
            "score": 0.85,
            "explanation": "解决方案合理，但可以进一步优化"
        }},
        {{
            "dimension": "clarity",
            "score": 0.8,
            "explanation": "结构清晰，但某些部分可以更简洁"
        }}
    ],
    "issues": ["问题1", "问题2"],
    "strengths": ["优点1", "优点2"],
    "needs_correction": true
}}"""

    async def score_output(self, 
                          output: str, 
                          context: ExecutionContext) -> CriticFeedback:
        """
        评估输出质量
        
        参数:
            output: Agent输出内容
            context: 执行上下文
            
        返回:
            CriticFeedback: 质量评估反馈
        """
        try:
            self.logger.info(f"开始评估输出质量，任务: {context.task_description[:50]}...")
            
            # 1. 规则引擎预评估
            rule_scores = self._rule_based_scoring(output, context)
            
            # 2. LLM深度评估
            llm_scores = await self._llm_based_scoring(output, context)
            
            # 3. 综合评分
            final_feedback = self._combine_scores(rule_scores, llm_scores, output, context)
            
            self.logger.info(f"质量评估完成，总分: {final_feedback.overall_score:.2f}")
            return final_feedback
            
        except Exception as e:
            self.logger.error(f"质量评估失败: {e}")
            # 返回默认的低分反馈
            return self._create_default_feedback(output, context, str(e))

    def _rule_based_scoring(self, output: str, context: ExecutionContext) -> Dict[str, float]:
        """
        基于规则的评分
        
        参数:
            output: 输出内容
            context: 执行上下文
            
        返回:
            Dict[str, float]: 各维度评分
        """
        scores = {}
        
        # 正确性评估
        scores["correctness"] = self._score_correctness(output, context)
        
        # 完整性评估
        scores["completeness"] = self._score_completeness(output, context)
        
        # 效率评估
        scores["efficiency"] = self._score_efficiency(output, context)
        
        # 清晰度评估
        scores["clarity"] = self._score_clarity(output, context)
        
        return scores

    def _score_correctness(self, output: str, context: ExecutionContext) -> float:
        """评估正确性"""
        score = 1.0
        
        # 检查常见错误模式
        error_patterns = [
            r"error|Error|ERROR",
            r"exception|Exception",
            r"undefined|Undefined",
            r"null|None|null",
            r"failed|Failed|FAILED"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, output):
                score -= 0.2
        
        # 检查代码语法错误（如果是代码输出）
        if self._is_code_output(output):
            if self._has_syntax_errors(output):
                score -= 0.3
        
        return max(0.0, score)

    def _score_completeness(self, output: str, context: ExecutionContext) -> float:
        """评估完整性"""
        score = 1.0
        
        # 检查输出长度
        if len(output.strip()) < 50:
            score -= 0.3
        
        # 检查是否包含关键信息
        task_keywords = self._extract_keywords(context.task_description)
        found_keywords = 0
        
        for keyword in task_keywords:
            if keyword.lower() in output.lower():
                found_keywords += 1
        
        if task_keywords:
            completeness_ratio = found_keywords / len(task_keywords)
            score = min(score, completeness_ratio + 0.3)
        
        return max(0.0, score)

    def _score_efficiency(self, output: str, context: ExecutionContext) -> float:
        """评估效率"""
        score = 1.0
        
        # 检查是否有冗余内容
        lines = output.split('\n')
        if len(lines) > 100:  # 输出过长可能效率不高
            score -= 0.1
        
        # 检查是否有重复内容
        if self._has_redundant_content(output):
            score -= 0.2
        
        return max(0.0, score)

    def _score_clarity(self, output: str, context: ExecutionContext) -> float:
        """评估清晰度"""
        score = 1.0
        
        # 检查结构清晰度
        if not self._has_clear_structure(output):
            score -= 0.2
        
        # 检查语言清晰度
        if self._has_unclear_language(output):
            score -= 0.2
        
        return max(0.0, score)

    async def _llm_based_scoring(self, output: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        基于LLM的评分
        
        参数:
            output: 输出内容
            context: 执行上下文
            
        返回:
            Dict[str, Any]: LLM评估结果
        """
        try:
            # 构建提示词
            prompt = self.quality_prompt.format(
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
                # 如果JSON解析失败，尝试提取JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
                else:
                    raise ValueError("无法解析LLM响应为JSON")
                    
        except Exception as e:
            self.logger.error(f"LLM评分失败: {e}")
            return self._create_fallback_llm_result()

    def _combine_scores(self, 
                       rule_scores: Dict[str, float], 
                       llm_result: Dict[str, Any],
                       output: str,
                       context: ExecutionContext) -> CriticFeedback:
        """
        综合规则评分和LLM评分
        
        参数:
            rule_scores: 规则评分
            llm_result: LLM评估结果
            output: 输出内容
            context: 执行上下文
            
        返回:
            CriticFeedback: 综合反馈
        """
        # 提取LLM评分
        llm_scores = {}
        dimension_scores = []
        
        if "dimension_scores" in llm_result:
            for dim_score in llm_result["dimension_scores"]:
                dimension = dim_score.get("dimension", "")
                score = dim_score.get("score", 0.5)
                explanation = dim_score.get("explanation", "")
                
                llm_scores[dimension] = score
                dimension_scores.append(QualityScore(
                    dimension=QualityDimension(dimension),
                    score=score,
                    explanation=explanation
                ))
        
        # 综合评分（规则评分权重0.3，LLM评分权重0.7）
        final_scores = {}
        for dimension in ["correctness", "completeness", "efficiency", "clarity"]:
            rule_score = rule_scores.get(dimension, 0.5)
            llm_score = llm_scores.get(dimension, 0.5)
            final_score = rule_score * 0.3 + llm_score * 0.7
            final_scores[dimension] = final_score
        
        # 计算总体评分
        overall_score = sum(final_scores.values()) / len(final_scores)
        
        # 提取问题和优点
        issues = llm_result.get("issues", [])
        strengths = llm_result.get("strengths", [])
        
        # 判断是否需要纠错
        needs_correction = llm_result.get("needs_correction", overall_score < 0.8)
        
        # 生成反馈文本
        feedback_text = self._generate_feedback_text(
            overall_score, dimension_scores, issues, strengths
        )
        
        return CriticFeedback(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=issues,
            strengths=strengths,
            needs_correction=needs_correction,
            feedback_text=feedback_text
        )

    def _create_default_feedback(self, output: str, context: ExecutionContext, error: str) -> CriticFeedback:
        """创建默认反馈（当评估失败时）"""
        return CriticFeedback(
            overall_score=0.3,
            dimension_scores=[
                QualityScore(
                    dimension=QualityDimension.CORRECTNESS,
                    score=0.3,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.COMPLETENESS,
                    score=0.3,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.EFFICIENCY,
                    score=0.3,
                    explanation=f"评估失败: {error}"
                ),
                QualityScore(
                    dimension=QualityDimension.CLARITY,
                    score=0.3,
                    explanation=f"评估失败: {error}"
                )
            ],
            issues=[f"质量评估失败: {error}"],
            strengths=[],
            needs_correction=True,
            feedback_text=f"由于评估过程出错，无法准确评估输出质量。错误: {error}"
        )

    def _create_fallback_llm_result(self) -> Dict[str, Any]:
        """创建LLM评估的备用结果"""
        return {
            "overall_score": 0.5,
            "dimension_scores": [
                {"dimension": "correctness", "score": 0.5, "explanation": "LLM评估失败，使用默认评分"},
                {"dimension": "completeness", "score": 0.5, "explanation": "LLM评估失败，使用默认评分"},
                {"dimension": "efficiency", "score": 0.5, "explanation": "LLM评估失败，使用默认评分"},
                {"dimension": "clarity", "score": 0.5, "explanation": "LLM评估失败，使用默认评分"}
            ],
            "issues": ["LLM评估失败"],
            "strengths": [],
            "needs_correction": True
        }

    def _generate_feedback_text(self, 
                               overall_score: float,
                               dimension_scores: List[QualityScore],
                               issues: List[str],
                               strengths: List[str]) -> str:
        """生成反馈文本"""
        feedback_parts = []
        
        # 总体评分
        feedback_parts.append(f"总体评分: {overall_score:.2f}/1.0")
        
        # 各维度评分
        feedback_parts.append("\n各维度评分:")
        for score in dimension_scores:
            feedback_parts.append(f"- {score.dimension.value}: {score.score:.2f} - {score.explanation}")
        
        # 优点
        if strengths:
            feedback_parts.append(f"\n优点:")
            for strength in strengths:
                feedback_parts.append(f"- {strength}")
        
        # 问题
        if issues:
            feedback_parts.append(f"\n需要改进的问题:")
            for issue in issues:
                feedback_parts.append(f"- {issue}")
        
        return "\n".join(feedback_parts)

    # 辅助方法
    def _is_code_output(self, output: str) -> bool:
        """判断是否为代码输出"""
        code_indicators = ["def ", "class ", "import ", "function", "var ", "let ", "const "]
        return any(indicator in output for indicator in code_indicators)

    def _has_syntax_errors(self, output: str) -> bool:
        """检查是否有语法错误"""
        # 简单的语法错误检查
        error_patterns = [
            r"SyntaxError",
            r"IndentationError", 
            r"NameError",
            r"TypeError"
        ]
        return any(re.search(pattern, output) for pattern in error_patterns)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b\w+\b', text.lower())
        # 过滤掉常见停用词
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        return keywords[:10]  # 返回前10个关键词

    def _has_redundant_content(self, output: str) -> bool:
        """检查是否有冗余内容"""
        lines = output.split('\n')
        if len(lines) < 5:
            return False
        
        # 检查重复行
        unique_lines = set(lines)
        return len(unique_lines) < len(lines) * 0.8

    def _has_clear_structure(self, output: str) -> bool:
        """检查是否有清晰的结构"""
        structure_indicators = ["#", "##", "1.", "2.", "-", "*", "```"]
        return any(indicator in output for indicator in structure_indicators)

    def _has_unclear_language(self, output: str) -> bool:
        """检查是否有不清晰的语言"""
        unclear_patterns = [
            r"maybe|perhaps|might|could be",
            r"not sure|unclear|confusing",
            r"etc\.|and so on|and more"
        ]
        return any(re.search(pattern, output, re.IGNORECASE) for pattern in unclear_patterns)
