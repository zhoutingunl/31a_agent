"""
自我纠错器 - 根据批评反馈生成改进建议

功能：
- 根据批评反馈生成改进建议
- 生成新的执行计划
- 管理重试逻辑
- 优化执行策略
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.core.reflection.schemas import (
    CriticFeedback, CorrectionSuggestion, ExecutionContext, ReflectionConfig
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SelfCorrector:
    """
    自我纠错器
    
    功能：
    - 根据批评反馈生成改进建议
    - 生成新的执行计划
    - 管理重试逻辑
    - 优化执行策略
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化自我纠错器
        
        参数:
            llm: LLM实例
        """
        self.llm = llm
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # 自我纠错提示词
        self.corrector_prompt = """你是一个自我纠错专家，负责根据批评反馈改进Agent的输出。

原始任务: {task_description}
期望目标: {expected_goal}
之前的输出: {previous_output}
批评反馈: {critic_feedback}
发现的问题: {issues}
约束条件: {constraints}

请分析问题并提供具体的改进建议。请以JSON格式返回：

{{
    "correction_suggestions": [
        {{
            "issue": "具体问题描述",
            "suggestion": "详细的改进建议",
            "priority": 5,
            "expected_improvement": "预期改进效果"
        }}
    ],
    "retry_strategy": {{
        "approach": "新的执行策略",
        "focus_areas": ["重点改进领域1", "重点改进领域2"],
        "avoid_previous_mistakes": true,
        "additional_considerations": "其他需要考虑的因素"
    }},
    "should_retry": true,
    "confidence": 0.8,
    "estimated_improvement": 0.2
}}

请确保：
1. 建议具体可操作，不要泛泛而谈
2. 优先级设置合理（1-5，5最高）
3. 预期改进效果明确
4. 新的执行策略针对性强
5. 避免重复之前的错误"""

    async def generate_corrections(self, 
                                 feedback: CriticFeedback,
                                 context: ExecutionContext,
                                 previous_output: str,
                                 retry_count: int = 0) -> List[CorrectionSuggestion]:
        """
        生成纠错建议
        
        参数:
            feedback: 批评反馈
            context: 执行上下文
            previous_output: 之前的输出
            retry_count: 重试次数
            
        返回:
            List[CorrectionSuggestion]: 纠错建议列表
        """
        try:
            self.logger.info(f"开始生成纠错建议，重试次数: {retry_count}")
            
            # 1. 使用LLM生成改进建议
            llm_suggestions = await self._llm_generate_suggestions(
                feedback, context, previous_output, retry_count
            )
            
            # 2. 基于规则生成补充建议
            rule_suggestions = self._rule_based_suggestions(feedback, context, retry_count)
            
            # 3. 合并和优化建议
            all_suggestions = self._merge_and_optimize_suggestions(
                llm_suggestions, rule_suggestions, feedback, retry_count
            )
            
            self.logger.info(f"生成纠错建议完成，共{len(all_suggestions)}条建议")
            return all_suggestions
            
        except Exception as e:
            self.logger.error(f"生成纠错建议失败: {e}")
            return self._create_fallback_suggestions(feedback, context, str(e))

    async def _llm_generate_suggestions(self,
                                      feedback: CriticFeedback,
                                      context: ExecutionContext,
                                      previous_output: str,
                                      retry_count: int) -> List[CorrectionSuggestion]:
        """
        使用LLM生成改进建议
        
        参数:
            feedback: 批评反馈
            context: 执行上下文
            previous_output: 之前的输出
            retry_count: 重试次数
            
        返回:
            List[CorrectionSuggestion]: LLM生成的建议
        """
        try:
            # 构建提示词
            prompt = self.corrector_prompt.format(
                task_description=context.task_description,
                expected_goal=context.expected_goal,
                previous_output=previous_output[:1000],  # 限制长度
                critic_feedback=feedback.feedback_text,
                issues=", ".join(feedback.issues),
                constraints=", ".join(context.constraints) if context.constraints else "无"
            )
            
            # 调用LLM
            response = await self.llm.achat(prompt)
            
            # 解析JSON响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError("无法解析LLM响应为JSON")
            
            # 转换为CorrectionSuggestion对象
            suggestions = []
            if "correction_suggestions" in result:
                for suggestion_data in result["correction_suggestions"]:
                    try:
                        suggestion = CorrectionSuggestion(
                            issue=suggestion_data.get("issue", ""),
                            suggestion=suggestion_data.get("suggestion", ""),
                            priority=suggestion_data.get("priority", 3),
                            expected_improvement=suggestion_data.get("expected_improvement", "")
                        )
                        suggestions.append(suggestion)
                    except Exception as e:
                        self.logger.warning(f"解析建议失败: {e}")
                        continue
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"LLM生成建议失败: {e}")
            return []

    def _rule_based_suggestions(self,
                              feedback: CriticFeedback,
                              context: ExecutionContext,
                              retry_count: int) -> List[CorrectionSuggestion]:
        """
        基于规则生成补充建议
        
        参数:
            feedback: 批评反馈
            context: 执行上下文
            retry_count: 重试次数
            
        返回:
            List[CorrectionSuggestion]: 规则生成的建议
        """
        suggestions = []
        
        # 基于评分生成建议
        for score in feedback.dimension_scores:
            if score.score < 0.6:  # 低分维度
                suggestion = self._generate_dimension_suggestion(score, retry_count)
                if suggestion:
                    suggestions.append(suggestion)
        
        # 基于重试次数生成建议
        if retry_count > 0:
            suggestions.append(CorrectionSuggestion(
                issue=f"第{retry_count + 1}次重试，需要更仔细地分析问题",
                suggestion="请仔细阅读任务要求，确保理解正确，避免重复之前的错误",
                priority=4,
                expected_improvement="提高输出准确性和完整性"
            ))
        
        # 基于问题类型生成建议
        for issue in feedback.issues:
            if "错误" in issue or "error" in issue.lower():
                suggestions.append(CorrectionSuggestion(
                    issue="输出中存在错误",
                    suggestion="请仔细检查输出内容，确保没有语法错误、逻辑错误或事实错误",
                    priority=5,
                    expected_improvement="消除输出中的错误"
                ))
            elif "不完整" in issue or "缺少" in issue:
                suggestions.append(CorrectionSuggestion(
                    issue="输出不完整",
                    suggestion="请确保输出涵盖了所有要求，补充遗漏的重要内容",
                    priority=4,
                    expected_improvement="提高输出完整性"
                ))
            elif "不清晰" in issue or "混乱" in issue:
                suggestions.append(CorrectionSuggestion(
                    issue="输出不够清晰",
                    suggestion="请重新组织输出结构，使用更清晰的语言和格式",
                    priority=3,
                    expected_improvement="提高输出清晰度"
                ))
        
        return suggestions

    def _generate_dimension_suggestion(self, score, retry_count: int) -> Optional[CorrectionSuggestion]:
        """为特定维度生成建议"""
        dimension_suggestions = {
            "correctness": {
                "issue": "正确性不足",
                "suggestion": "请仔细验证输出内容的正确性，确保没有错误",
                "priority": 5,
                "expected_improvement": "提高输出正确性"
            },
            "completeness": {
                "issue": "完整性不足",
                "suggestion": "请确保输出涵盖了所有要求，补充遗漏的内容",
                "priority": 4,
                "expected_improvement": "提高输出完整性"
            },
            "efficiency": {
                "issue": "效率不高",
                "suggestion": "请优化解决方案，使用更高效的方法",
                "priority": 3,
                "expected_improvement": "提高解决方案效率"
            },
            "clarity": {
                "issue": "清晰度不足",
                "suggestion": "请重新组织输出结构，使用更清晰的语言",
                "priority": 3,
                "expected_improvement": "提高输出清晰度"
            }
        }
        
        if score.dimension.value in dimension_suggestions:
            suggestion_data = dimension_suggestions[score.dimension.value]
            return CorrectionSuggestion(
                issue=suggestion_data["issue"],
                suggestion=suggestion_data["suggestion"],
                priority=suggestion_data["priority"],
                expected_improvement=suggestion_data["expected_improvement"]
            )
        
        return None

    def _merge_and_optimize_suggestions(self,
                                      llm_suggestions: List[CorrectionSuggestion],
                                      rule_suggestions: List[CorrectionSuggestion],
                                      feedback: CriticFeedback,
                                      retry_count: int) -> List[CorrectionSuggestion]:
        """
        合并和优化建议
        
        参数:
            llm_suggestions: LLM生成的建议
            rule_suggestions: 规则生成的建议
            feedback: 批评反馈
            retry_count: 重试次数
            
        返回:
            List[CorrectionSuggestion]: 优化后的建议列表
        """
        # 合并所有建议
        all_suggestions = llm_suggestions + rule_suggestions
        
        # 去重（基于问题描述）
        unique_suggestions = []
        seen_issues = set()
        
        for suggestion in all_suggestions:
            issue_key = suggestion.issue.lower().strip()
            if issue_key not in seen_issues:
                seen_issues.add(issue_key)
                unique_suggestions.append(suggestion)
        
        # 按优先级排序
        unique_suggestions.sort(key=lambda x: x.priority, reverse=True)
        
        # 限制建议数量（避免过多建议）
        max_suggestions = min(5, len(unique_suggestions))
        optimized_suggestions = unique_suggestions[:max_suggestions]
        
        # 根据重试次数调整优先级
        if retry_count > 1:
            for suggestion in optimized_suggestions:
                suggestion.priority = min(5, suggestion.priority + 1)
        
        return optimized_suggestions

    def create_retry_plan(self,
                         suggestions: List[CorrectionSuggestion],
                         context: ExecutionContext,
                         retry_count: int) -> Dict[str, Any]:
        """
        创建重试计划
        
        参数:
            suggestions: 纠错建议
            context: 执行上下文
            retry_count: 重试次数
            
        返回:
            Dict[str, Any]: 重试计划
        """
        # 按优先级分组建议
        high_priority = [s for s in suggestions if s.priority >= 4]
        medium_priority = [s for s in suggestions if s.priority == 3]
        low_priority = [s for s in suggestions if s.priority <= 2]
        
        # 生成重试策略
        strategy = self._generate_retry_strategy(suggestions, retry_count)
        
        return {
            "retry_count": retry_count + 1,
            "strategy": strategy,
            "high_priority_fixes": [s.issue for s in high_priority],
            "medium_priority_fixes": [s.issue for s in medium_priority],
            "low_priority_fixes": [s.issue for s in low_priority],
            "all_suggestions": suggestions,
            "estimated_improvement": self._estimate_improvement(suggestions),
            "focus_areas": self._identify_focus_areas(suggestions)
        }

    def _generate_retry_strategy(self,
                               suggestions: List[CorrectionSuggestion],
                               retry_count: int) -> str:
        """生成重试策略"""
        if retry_count == 0:
            return "首次重试：重点关注高优先级问题，确保基本正确性"
        elif retry_count == 1:
            return "第二次重试：在保证正确性的基础上，提高完整性和清晰度"
        else:
            return "多次重试：全面检查所有问题，采用更保守和仔细的方法"

    def _estimate_improvement(self, suggestions: List[CorrectionSuggestion]) -> float:
        """估算改进效果"""
        if not suggestions:
            return 0.0
        
        # 基于优先级和数量估算改进
        total_priority = sum(s.priority for s in suggestions)
        max_possible_priority = len(suggestions) * 5
        improvement_ratio = total_priority / max_possible_priority if max_possible_priority > 0 else 0
        
        # 转换为0-1的改进分数
        return min(0.5, improvement_ratio * 0.5)

    def _identify_focus_areas(self, suggestions: List[CorrectionSuggestion]) -> List[str]:
        """识别重点改进领域"""
        focus_areas = []
        
        for suggestion in suggestions:
            if suggestion.priority >= 4:
                if "正确" in suggestion.issue or "错误" in suggestion.issue:
                    focus_areas.append("正确性")
                elif "完整" in suggestion.issue or "缺少" in suggestion.issue:
                    focus_areas.append("完整性")
                elif "清晰" in suggestion.issue or "混乱" in suggestion.issue:
                    focus_areas.append("清晰度")
                elif "效率" in suggestion.issue:
                    focus_areas.append("效率")
        
        # 去重
        return list(set(focus_areas))

    def should_retry(self,
                    feedback: CriticFeedback,
                    retry_count: int,
                    config: ReflectionConfig) -> bool:
        """
        判断是否应该重试
        
        参数:
            feedback: 批评反馈
            retry_count: 当前重试次数
            config: 反思配置
            
        返回:
            bool: 是否应该重试
        """
        # 检查是否达到最大重试次数
        if retry_count >= config.max_retries:
            return False
        
        # 检查是否启用自动纠错
        if not config.enable_auto_correction:
            return False
        
        # 检查质量是否达到阈值
        if feedback.overall_score >= config.quality_threshold:
            return False
        
        # 检查是否需要纠错
        if not feedback.needs_correction:
            return False
        
        # 检查是否有可改进的问题
        if not feedback.issues:
            return False
        
        return True

    def _create_fallback_suggestions(self,
                                   feedback: CriticFeedback,
                                   context: ExecutionContext,
                                   error: str) -> List[CorrectionSuggestion]:
        """创建备用建议（当生成失败时）"""
        return [
            CorrectionSuggestion(
                issue=f"纠错建议生成失败: {error}",
                suggestion="请仔细检查输出内容，确保符合任务要求",
                priority=3,
                expected_improvement="提高输出质量"
            )
        ]

    def analyze_correction_effectiveness(self,
                                       before_feedback: CriticFeedback,
                                       after_feedback: CriticFeedback) -> Dict[str, Any]:
        """
        分析纠错效果
        
        参数:
            before_feedback: 纠错前的反馈
            after_feedback: 纠错后的反馈
            
        返回:
            Dict[str, Any]: 纠错效果分析
        """
        # 计算总体改进
        overall_improvement = after_feedback.overall_score - before_feedback.overall_score
        
        # 计算各维度改进
        dimension_improvements = {}
        for after_score in after_feedback.dimension_scores:
            dimension = after_score.dimension.value
            before_score = None
            
            for before_score_obj in before_feedback.dimension_scores:
                if before_score_obj.dimension.value == dimension:
                    before_score = before_score_obj.score
                    break
            
            if before_score is not None:
                dimension_improvements[dimension] = after_score.score - before_score
        
        # 分析问题解决情况
        resolved_issues = []
        remaining_issues = []
        
        for issue in before_feedback.issues:
            # 简单检查问题是否仍然存在
            issue_resolved = True
            for after_issue in after_feedback.issues:
                if issue.lower() in after_issue.lower() or after_issue.lower() in issue.lower():
                    issue_resolved = False
                    break
            
            if issue_resolved:
                resolved_issues.append(issue)
            else:
                remaining_issues.append(issue)
        
        return {
            "overall_improvement": overall_improvement,
            "dimension_improvements": dimension_improvements,
            "resolved_issues": resolved_issues,
            "remaining_issues": remaining_issues,
            "effectiveness_score": self._calculate_effectiveness_score(
                overall_improvement, len(resolved_issues), len(before_feedback.issues)
            )
        }

    def _calculate_effectiveness_score(self,
                                     overall_improvement: float,
                                     resolved_count: int,
                                     total_issues: int) -> float:
        """计算纠错效果分数"""
        if total_issues == 0:
            return 1.0 if overall_improvement > 0 else 0.0
        
        resolution_ratio = resolved_count / total_issues
        improvement_score = max(0, min(1, overall_improvement + 0.5))
        
        return (resolution_ratio * 0.6 + improvement_score * 0.4)
