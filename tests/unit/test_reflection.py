"""
反思模块单元测试

测试反思与自我纠错系统的核心组件
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.core.reflection.schemas import (
    QualityDimension, QualityScore, CriticFeedback, CorrectionSuggestion,
    ExecutionContext, ReflectionConfig
)
from app.core.reflection.quality_scorer import QualityScorer
from app.core.reflection.critic import Critic
from app.core.reflection.self_corrector import SelfCorrector


class TestQualityScorer:
    """测试质量评分器"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def quality_scorer(self, mock_llm):
        """质量评分器实例"""
        return QualityScorer(mock_llm)
    
    @pytest.fixture
    def sample_context(self):
        """示例执行上下文"""
        return ExecutionContext(
            task_description="生成一个排序函数",
            expected_goal="创建一个高效的排序算法",
            constraints=["使用Python", "时间复杂度O(n log n)"],
            context_info={"language": "python"}
        )
    
    def test_init(self, mock_llm):
        """测试初始化"""
        scorer = QualityScorer(mock_llm)
        assert scorer.llm == mock_llm
        assert scorer.logger is not None
    
    def test_rule_based_scoring_correctness(self, quality_scorer, sample_context):
        """测试基于规则的正确性评分"""
        # 测试正确输出
        correct_output = "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)"
        
        scores = quality_scorer._rule_based_scoring(correct_output, sample_context)
        assert "correctness" in scores
        assert 0.0 <= scores["correctness"] <= 1.0
        
        # 测试包含错误的输出
        error_output = "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)\n    error: undefined variable"
        
        error_scores = quality_scorer._rule_based_scoring(error_output, sample_context)
        assert error_scores["correctness"] < scores["correctness"]
    
    def test_rule_based_scoring_completeness(self, quality_scorer, sample_context):
        """测试基于规则的完整性评分"""
        # 测试完整输出
        complete_output = "这是一个完整的排序函数实现，包含详细说明和示例。"
        
        scores = quality_scorer._rule_based_scoring(complete_output, sample_context)
        assert "completeness" in scores
        assert 0.0 <= scores["completeness"] <= 1.0
        
        # 测试不完整输出
        incomplete_output = "def sort():"
        
        incomplete_scores = quality_scorer._rule_based_scoring(incomplete_output, sample_context)
        assert incomplete_scores["completeness"] < scores["completeness"]
    
    def test_rule_based_scoring_efficiency(self, quality_scorer, sample_context):
        """测试基于规则的效率评分"""
        # 测试高效输出
        efficient_output = "def quick_sort(arr):\n    return sorted(arr)"
        
        scores = quality_scorer._rule_based_scoring(efficient_output, sample_context)
        assert "efficiency" in scores
        assert 0.0 <= scores["efficiency"] <= 1.0
    
    def test_rule_based_scoring_clarity(self, quality_scorer, sample_context):
        """测试基于规则的清晰度评分"""
        # 测试清晰输出
        clear_output = "# 快速排序算法\n# 时间复杂度: O(n log n)\n# 空间复杂度: O(log n)\n\ndef quick_sort(arr):\n    \"\"\"\n    快速排序函数\n    \n    参数:\n        arr: 待排序的列表\n    \n    返回:\n        排序后的列表\n    \"\"\"\n    if len(arr) <= 1:\n        return arr\n    # 选择中间元素作为基准\n    pivot = arr[len(arr)//2]\n    # 分割数组\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    # 递归排序并合并\n    return quick_sort(left) + middle + quick_sort(right)"
        
        scores = quality_scorer._rule_based_scoring(clear_output, sample_context)
        assert "clarity" in scores
        assert 0.0 <= scores["clarity"] <= 1.0
        
        # 测试不清晰输出
        unclear_output = "def qs(a):\n    if len(a)<=1:return a\n    p=a[len(a)//2]\n    l=[x for x in a if x<p]\n    m=[x for x in a if x==p]\n    r=[x for x in a if x>p]\n    return qs(l)+m+qs(r)"
        
        unclear_scores = quality_scorer._rule_based_scoring(unclear_output, sample_context)
        assert unclear_scores["clarity"] < scores["clarity"]
    
    @pytest.mark.asyncio
    async def test_score_output_success(self, quality_scorer, sample_context, mock_llm):
        """测试成功评分输出"""
        # Mock LLM响应
        mock_llm.achat.return_value = '''{
            "overall_score": 0.85,
            "dimension_scores": [
                {"dimension": "correctness", "score": 0.9, "explanation": "输出正确"},
                {"dimension": "completeness", "score": 0.8, "explanation": "基本完整"},
                {"dimension": "efficiency", "score": 0.85, "explanation": "效率良好"},
                {"dimension": "clarity", "score": 0.8, "explanation": "结构清晰"}
            ],
            "issues": ["缺少注释"],
            "strengths": ["算法正确", "结构清晰"],
            "needs_correction": false
        }'''
        
        output = "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)"
        
        result = await quality_scorer.score_output(output, sample_context)
        
        assert isinstance(result, CriticFeedback)
        assert result.overall_score > 0
        assert len(result.dimension_scores) == 4
        assert len(result.issues) >= 0
        assert len(result.strengths) >= 0
        assert isinstance(result.needs_correction, bool)
    
    @pytest.mark.asyncio
    async def test_score_output_llm_failure(self, quality_scorer, sample_context, mock_llm):
        """测试LLM失败时的评分"""
        # Mock LLM失败
        mock_llm.achat.side_effect = Exception("LLM服务不可用")
        
        output = "def quick_sort(arr):\n    return sorted(arr)"
        
        result = await quality_scorer.score_output(output, sample_context)
        
        assert isinstance(result, CriticFeedback)
        assert result.overall_score == 0.3  # 默认低分
        assert "评估失败" in result.feedback_text


class TestCritic:
    """测试批评者"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def critic(self, mock_llm):
        """批评者实例"""
        return Critic(mock_llm)
    
    @pytest.fixture
    def sample_context(self):
        """示例执行上下文"""
        return ExecutionContext(
            task_description="生成一个排序函数",
            expected_goal="创建一个高效的排序算法",
            constraints=["使用Python", "时间复杂度O(n log n)"],
            context_info={"language": "python"}
        )
    
    def test_init(self, mock_llm):
        """测试初始化"""
        critic = Critic(mock_llm)
        assert critic.llm == mock_llm
        assert critic.quality_scorer is not None
        assert critic.logger is not None
    
    @pytest.mark.asyncio
    async def test_evaluate_success(self, critic, sample_context, mock_llm):
        """测试成功评估"""
        # Mock LLM响应
        mock_llm.achat.return_value = '''{
            "overall_score": 0.75,
            "dimension_scores": [
                {"dimension": "correctness", "score": 0.8, "explanation": "基本正确"},
                {"dimension": "completeness", "score": 0.7, "explanation": "缺少注释"},
                {"dimension": "efficiency", "score": 0.8, "explanation": "效率良好"},
                {"dimension": "clarity", "score": 0.7, "explanation": "可以更清晰"}
            ],
            "issues": ["缺少注释", "变量命名不够清晰"],
            "strengths": ["算法正确", "逻辑清晰"],
            "needs_correction": true,
            "correction_priority": "medium",
            "detailed_feedback": "整体实现正确，但需要改进代码可读性"
        }'''
        
        output = "def qs(a):\n    if len(a)<=1:return a\n    p=a[len(a)//2]\n    l=[x for x in a if x<p]\n    m=[x for x in a if x==p]\n    r=[x for x in a if x>p]\n    return qs(l)+m+qs(r)"
        
        result = await critic.evaluate(output, sample_context)
        
        assert isinstance(result, CriticFeedback)
        assert result.overall_score > 0
        assert len(result.dimension_scores) == 4
        assert len(result.issues) > 0
        assert len(result.strengths) > 0
        assert result.needs_correction is True
    
    @pytest.mark.asyncio
    async def test_quick_evaluate(self, critic, sample_context, mock_llm):
        """测试快速评估"""
        # Mock LLM响应
        mock_llm.achat.return_value = "YES"
        
        output = "def quick_sort(arr):\n    return sorted(arr)"
        
        result = await critic.quick_evaluate(output, sample_context)
        
        assert isinstance(result, bool)
        assert result is True
    
    def test_analyze_improvement_trend(self, critic):
        """测试改进趋势分析"""
        # 创建模拟反馈历史
        feedback1 = CriticFeedback(
            overall_score=0.6,
            dimension_scores=[],
            issues=["缺少注释"],
            strengths=["算法正确"],
            needs_correction=True,
            feedback_text="需要改进"
        )
        
        feedback2 = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["算法正确", "注释完整"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        history = [feedback1, feedback2]
        
        result = critic.analyze_improvement_trend(history)
        
        assert result["trend"] == "improving"
        assert result["improvement"] > 0
        assert result["current_score"] == 0.8
        assert result["initial_score"] == 0.6


class TestSelfCorrector:
    """测试自我纠错器"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def self_corrector(self, mock_llm):
        """自我纠错器实例"""
        return SelfCorrector(mock_llm)
    
    @pytest.fixture
    def sample_feedback(self):
        """示例批评反馈"""
        return CriticFeedback(
            overall_score=0.6,
            dimension_scores=[
                QualityScore(
                    dimension=QualityDimension.CORRECTNESS,
                    score=0.7,
                    explanation="基本正确"
                ),
                QualityScore(
                    dimension=QualityDimension.COMPLETENESS,
                    score=0.5,
                    explanation="缺少注释"
                ),
                QualityScore(
                    dimension=QualityDimension.EFFICIENCY,
                    score=0.8,
                    explanation="效率良好"
                ),
                QualityScore(
                    dimension=QualityDimension.CLARITY,
                    score=0.4,
                    explanation="不够清晰"
                )
            ],
            issues=["缺少注释", "变量命名不清晰"],
            strengths=["算法正确"],
            needs_correction=True,
            feedback_text="需要改进代码可读性"
        )
    
    @pytest.fixture
    def sample_context(self):
        """示例执行上下文"""
        return ExecutionContext(
            task_description="生成一个排序函数",
            expected_goal="创建一个高效的排序算法",
            constraints=["使用Python", "时间复杂度O(n log n)"],
            context_info={"language": "python"}
        )
    
    def test_init(self, mock_llm):
        """测试初始化"""
        corrector = SelfCorrector(mock_llm)
        assert corrector.llm == mock_llm
        assert corrector.logger is not None
    
    @pytest.mark.asyncio
    async def test_generate_corrections_success(self, self_corrector, sample_feedback, sample_context, mock_llm):
        """测试成功生成纠错建议"""
        # Mock LLM响应
        mock_llm.achat.return_value = '''{
            "correction_suggestions": [
                {
                    "issue": "缺少注释",
                    "suggestion": "添加详细的函数和参数说明",
                    "priority": 4,
                    "expected_improvement": "提高代码可读性"
                },
                {
                    "issue": "变量命名不清晰",
                    "suggestion": "使用更有意义的变量名",
                    "priority": 3,
                    "expected_improvement": "提高代码可维护性"
                }
            ],
            "retry_strategy": {
                "approach": "重新组织代码结构",
                "focus_areas": ["代码注释", "变量命名"],
                "avoid_previous_mistakes": true,
                "additional_considerations": "保持算法正确性"
            },
            "should_retry": true,
            "confidence": 0.8,
            "estimated_improvement": 0.2
        }'''
        
        previous_output = "def qs(a):\n    if len(a)<=1:return a\n    p=a[len(a)//2]\n    l=[x for x in a if x<p]\n    m=[x for x in a if x==p]\n    r=[x for x in a if x>p]\n    return qs(l)+m+qs(r)"
        
        result = await self_corrector.generate_corrections(
            sample_feedback, sample_context, previous_output, 0
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(s, CorrectionSuggestion) for s in result)
        
        # 检查建议内容
        for suggestion in result:
            assert suggestion.issue
            assert suggestion.suggestion
            assert 1 <= suggestion.priority <= 5
            assert suggestion.expected_improvement
    
    def test_rule_based_suggestions(self, self_corrector, sample_feedback, sample_context):
        """测试基于规则的纠错建议"""
        result = self_corrector._rule_based_suggestions(sample_feedback, sample_context, 0)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(s, CorrectionSuggestion) for s in result)
    
    def test_create_retry_plan(self, self_corrector, sample_context):
        """测试创建重试计划"""
        suggestions = [
            CorrectionSuggestion(
                issue="缺少注释",
                suggestion="添加详细注释",
                priority=4,
                expected_improvement="提高可读性"
            ),
            CorrectionSuggestion(
                issue="变量命名不清晰",
                suggestion="使用有意义的变量名",
                priority=3,
                expected_improvement="提高可维护性"
            )
        ]
        
        result = self_corrector.create_retry_plan(suggestions, sample_context, 0)
        
        assert isinstance(result, dict)
        assert "retry_count" in result
        assert "strategy" in result
        assert "high_priority_fixes" in result
        assert "medium_priority_fixes" in result
        assert "low_priority_fixes" in result
        assert "all_suggestions" in result
        assert "estimated_improvement" in result
        assert "focus_areas" in result
    
    def test_should_retry(self, self_corrector, sample_feedback):
        """测试是否应该重试"""
        config = ReflectionConfig()
        
        # 测试应该重试的情况
        assert self_corrector.should_retry(sample_feedback, 0, config) is True
        
        # 测试不应该重试的情况（达到最大重试次数）
        assert self_corrector.should_retry(sample_feedback, 3, config) is False
        
        # 测试不应该重试的情况（质量达到阈值）
        high_quality_feedback = CriticFeedback(
            overall_score=0.9,
            dimension_scores=[],
            issues=[],
            strengths=["质量很好"],
            needs_correction=False,
            feedback_text="质量很好"
        )
        assert self_corrector.should_retry(high_quality_feedback, 0, config) is False
    
    def test_analyze_correction_effectiveness(self, self_corrector):
        """测试纠错效果分析"""
        before_feedback = CriticFeedback(
            overall_score=0.6,
            dimension_scores=[],
            issues=["缺少注释", "变量命名不清晰"],
            strengths=["算法正确"],
            needs_correction=True,
            feedback_text="需要改进"
        )
        
        after_feedback = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=["变量命名可以更好"],
            strengths=["算法正确", "注释完整"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        result = self_corrector.analyze_correction_effectiveness(before_feedback, after_feedback)
        
        assert isinstance(result, dict)
        assert "overall_improvement" in result
        assert "dimension_improvements" in result
        assert "resolved_issues" in result
        assert "remaining_issues" in result
        assert "effectiveness_score" in result
        
        assert result["overall_improvement"] > 0
        assert len(result["resolved_issues"]) > 0
        assert result["effectiveness_score"] > 0


class TestReflectionSchemas:
    """测试反思相关数据结构"""
    
    def test_quality_dimension_enum(self):
        """测试质量维度枚举"""
        assert QualityDimension.CORRECTNESS == "correctness"
        assert QualityDimension.COMPLETENESS == "completeness"
        assert QualityDimension.EFFICIENCY == "efficiency"
        assert QualityDimension.CLARITY == "clarity"
    
    def test_quality_score_validation(self):
        """测试质量评分验证"""
        # 测试有效评分
        score = QualityScore(
            dimension=QualityDimension.CORRECTNESS,
            score=0.8,
            explanation="基本正确"
        )
        assert score.score == 0.8
        assert score.dimension == QualityDimension.CORRECTNESS
        
        # 测试无效评分
        with pytest.raises(ValueError):
            QualityScore(
                dimension=QualityDimension.CORRECTNESS,
                score=1.5,  # 超出范围
                explanation="无效评分"
            )
    
    def test_critic_feedback_validation(self):
        """测试批评反馈验证"""
        feedback = CriticFeedback(
            overall_score=0.75,
            dimension_scores=[],
            issues=["缺少注释"],
            strengths=["算法正确"],
            needs_correction=True,
            feedback_text="需要改进"
        )
        assert feedback.overall_score == 0.75
        assert feedback.needs_correction is True
        
        # 测试无效总体评分
        with pytest.raises(ValueError):
            CriticFeedback(
                overall_score=1.5,  # 超出范围
                dimension_scores=[],
                issues=[],
                strengths=[],
                needs_correction=False,
                feedback_text="无效"
            )
    
    def test_correction_suggestion_validation(self):
        """测试纠错建议验证"""
        suggestion = CorrectionSuggestion(
            issue="缺少注释",
            suggestion="添加详细注释",
            priority=4,
            expected_improvement="提高可读性"
        )
        assert suggestion.priority == 4
        
        # 测试无效优先级
        with pytest.raises(ValueError):
            CorrectionSuggestion(
                issue="测试",
                suggestion="测试建议",
                priority=6,  # 超出范围
                expected_improvement="测试改进"
            )
    
    def test_execution_context(self):
        """测试执行上下文"""
        context = ExecutionContext(
            task_description="生成排序函数",
            expected_goal="创建高效算法",
            constraints=["使用Python"],
            context_info={"language": "python"}
        )
        assert context.task_description == "生成排序函数"
        assert context.expected_goal == "创建高效算法"
        assert "使用Python" in context.constraints
        assert context.context_info["language"] == "python"
    
    def test_reflection_config(self):
        """测试反思配置"""
        config = ReflectionConfig()
        assert config.max_retries == 3
        assert config.quality_threshold == 0.8
        assert config.enable_auto_correction is True
        
        # 测试自定义配置
        custom_config = ReflectionConfig(
            max_retries=5,
            quality_threshold=0.9,
            enable_auto_correction=False
        )
        assert custom_config.max_retries == 5
        assert custom_config.quality_threshold == 0.9
        assert custom_config.enable_auto_correction is False
