"""
反思模块集成测试

测试反思与自我纠错系统的端到端功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.core.reflection.schemas import (
    ExecutionContext, ReflectionConfig, CriticFeedback, QualityDimension, QualityScore
)
from app.core.reflection.critic import Critic
from app.core.reflection.self_corrector import SelfCorrector
from app.core.agent.executor_agent import ExecutorAgent
from app.services.reflection_service import ReflectionService
from app.tools.manager import ToolManager


class TestReflectionIntegration:
    """反思系统集成测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_db(self):
        """Mock数据库会话"""
        return Mock()
    
    @pytest.fixture
    def mock_tool_manager(self):
        """Mock工具管理器"""
        return Mock(spec=ToolManager)
    
    @pytest.fixture
    def reflection_service(self, mock_db, mock_llm, mock_tool_manager):
        """反思服务实例"""
        return ReflectionService(mock_db, mock_llm, mock_tool_manager)
    
    @pytest.fixture
    def sample_context(self):
        """示例执行上下文"""
        return ExecutionContext(
            task_description="生成一个Python排序函数",
            expected_goal="创建一个高效的快速排序算法",
            constraints=["使用Python", "时间复杂度O(n log n)", "包含详细注释"],
            context_info={"language": "python", "complexity": "medium"}
        )
    
    @pytest.mark.asyncio
    async def test_complete_reflection_cycle_success(self, reflection_service, sample_context, mock_llm):
        """测试完整的反思循环（成功场景）"""
        # Mock LLM响应序列
        mock_responses = [
            # 第一次执行
            "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr)//2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)",
            
            # 第一次评估
            '''{
                "overall_score": 0.6,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.8, "explanation": "算法正确"},
                    {"dimension": "completeness", "score": 0.4, "explanation": "缺少注释"},
                    {"dimension": "efficiency", "score": 0.8, "explanation": "效率良好"},
                    {"dimension": "clarity", "score": 0.4, "explanation": "不够清晰"}
                ],
                "issues": ["缺少注释", "变量命名不清晰"],
                "strengths": ["算法正确", "逻辑清晰"],
                "needs_correction": true
            }''',
            
            # 纠错建议
            '''{
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
            }''',
            
            # 第二次执行
            '''def quick_sort(arr):
    """
    快速排序算法
    
    参数:
        arr: 待排序的列表
    
    返回:
        排序后的列表
    
    时间复杂度: O(n log n)
    空间复杂度: O(log n)
    """
    if len(arr) <= 1:
        return arr
    
    # 选择中间元素作为基准
    pivot = arr[len(arr) // 2]
    
    # 分割数组
    left_part = [x for x in arr if x < pivot]
    middle_part = [x for x in arr if x == pivot]
    right_part = [x for x in arr if x > pivot]
    
    # 递归排序并合并
    return quick_sort(left_part) + middle_part + quick_sort(right_part)''',
            
            # 第二次评估
            '''{
                "overall_score": 0.9,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.9, "explanation": "算法正确"},
                    {"dimension": "completeness", "score": 0.9, "explanation": "注释完整"},
                    {"dimension": "efficiency", "score": 0.9, "explanation": "效率良好"},
                    {"dimension": "clarity", "score": 0.9, "explanation": "结构清晰"}
                ],
                "issues": [],
                "strengths": ["算法正确", "注释完整", "结构清晰", "变量命名清晰"],
                "needs_correction": false
            }'''
        ]
        
        # 设置Mock响应
        mock_llm.achat.side_effect = mock_responses
        
        # 执行反思任务
        result = await reflection_service.execute_with_reflection(
            task=sample_context.task_description,
            conversation_id=1,
            user_id=1,
            max_retries=3
        )
        
        # 验证结果
        assert result["success"] is True
        assert result["retry_count"] == 1  # 重试了1次
        assert result["reflection_enabled"] is True
        assert "快速排序算法" in result["output"]
        assert "时间复杂度" in result["output"]
        assert result["final_feedback"]["overall_score"] >= 0.8
    
    @pytest.mark.asyncio
    async def test_reflection_cycle_max_retries(self, reflection_service, sample_context, mock_llm):
        """测试达到最大重试次数的场景"""
        # Mock LLM响应（始终返回低质量输出）
        mock_responses = [
            # 执行输出（始终相同）
            "def sort(arr):\n    return sorted(arr)",
            
            # 评估（始终需要纠错）
            '''{
                "overall_score": 0.5,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.6, "explanation": "基本正确"},
                    {"dimension": "completeness", "score": 0.4, "explanation": "不完整"},
                    {"dimension": "efficiency", "score": 0.5, "explanation": "效率一般"},
                    {"dimension": "clarity", "score": 0.5, "explanation": "不够清晰"}
                ],
                "issues": ["不满足要求", "缺少实现"],
                "strengths": ["基本正确"],
                "needs_correction": true
            }''',
            
            # 纠错建议
            '''{
                "correction_suggestions": [
                    {
                        "issue": "不满足要求",
                        "suggestion": "实现快速排序算法",
                        "priority": 5,
                        "expected_improvement": "满足任务要求"
                    }
                ],
                "should_retry": true
            }'''
        ]
        
        # 设置Mock响应（循环使用）
        mock_llm.achat.side_effect = mock_responses * 10  # 确保有足够的响应
        
        # 执行反思任务（最大重试2次）
        result = await reflection_service.execute_with_reflection(
            task=sample_context.task_description,
            conversation_id=2,
            user_id=1,
            max_retries=2
        )
        
        # 验证结果
        assert result["success"] is False
        assert result["retry_count"] == 2  # 达到最大重试次数
        assert result["max_retries_reached"] is True
        assert result["reflection_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_reflection_stream_execution(self, reflection_service, sample_context, mock_llm):
        """测试流式反思执行"""
        # Mock LLM响应
        mock_responses = [
            # 第一次执行
            "def quick_sort(arr):\n    return sorted(arr)",
            
            # 第一次评估
            '''{
                "overall_score": 0.6,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.7, "explanation": "基本正确"},
                    {"dimension": "completeness", "score": 0.5, "explanation": "不完整"},
                    {"dimension": "efficiency", "score": 0.6, "explanation": "效率一般"},
                    {"dimension": "clarity", "score": 0.6, "explanation": "不够清晰"}
                ],
                "issues": ["不满足要求"],
                "strengths": ["基本正确"],
                "needs_correction": true
            }''',
            
            # 纠错建议
            '''{
                "correction_suggestions": [
                    {
                        "issue": "不满足要求",
                        "suggestion": "实现快速排序算法",
                        "priority": 5,
                        "expected_improvement": "满足任务要求"
                    }
                ],
                "should_retry": true
            }''',
            
            # 第二次执行
            '''def quick_sort(arr):
    """
    快速排序算法
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)''',
            
            # 第二次评估
            '''{
                "overall_score": 0.85,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.9, "explanation": "算法正确"},
                    {"dimension": "completeness", "score": 0.8, "explanation": "基本完整"},
                    {"dimension": "efficiency", "score": 0.9, "explanation": "效率良好"},
                    {"dimension": "clarity", "score": 0.8, "explanation": "结构清晰"}
                ],
                "issues": [],
                "strengths": ["算法正确", "结构清晰"],
                "needs_correction": false
            }'''
        ]
        
        mock_llm.achat.side_effect = mock_responses
        
        # 收集流式响应
        chunks = []
        async for chunk in reflection_service.execute_with_reflection_stream(
            task=sample_context.task_description,
            conversation_id=3,
            user_id=1,
            max_retries=3
        ):
            chunks.append(chunk)
        
        # 验证流式响应
        assert len(chunks) > 0
        
        # 检查响应类型
        chunk_types = [chunk.get("type") for chunk in chunks]
        assert "start" in chunk_types
        assert "execution" in chunk_types
        assert "evaluation" in chunk_types
        assert "correction" in chunk_types
        assert "complete" in chunk_types
        
        # 检查最终结果
        complete_chunks = [chunk for chunk in chunks if chunk.get("type") == "complete"]
        assert len(complete_chunks) > 0
        assert complete_chunks[0]["success"] is True
    
    @pytest.mark.asyncio
    async def test_reflection_with_tools(self, reflection_service, sample_context, mock_llm, mock_tool_manager):
        """测试带工具的反思执行"""
        # Mock工具管理器
        mock_tool_manager.get_all_tools.return_value = []
        
        # Mock LLM响应
        mock_llm.achat.return_value = '''def quick_sort(arr):
    """
    快速排序算法实现
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)'''
        
        # 执行带工具的反思任务
        result = await reflection_service.executor_agent.execute_with_tools(
            context=sample_context,
            tool_names=["code_generator"]
        )
        
        # 验证结果
        assert result["success"] is True
        assert "快速排序" in result["output"]
    
    def test_reflection_history_management(self, reflection_service):
        """测试反思历史管理"""
        # 清空历史
        reflection_service.clear_history()
        assert len(reflection_service.reflection_history) == 0
        
        # 添加模拟历史记录
        from app.core.reflection.schemas import ReflectionHistory, CriticFeedback
        
        feedback = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["质量良好"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        history = ReflectionHistory(
            task_id=1,
            iteration=1,
            output="测试输出",
            feedback=feedback,
            suggestions=[],
            improvement_score=0.2
        )
        
        reflection_service.reflection_history.append(history)
        
        # 获取历史记录
        retrieved_history = reflection_service.get_reflection_history(task_id=1)
        assert len(retrieved_history) == 1
        assert retrieved_history[0].task_id == 1
    
    def test_improvement_analysis(self, reflection_service):
        """测试改进效果分析"""
        # 添加模拟历史记录
        from app.core.reflection.schemas import ReflectionHistory, CriticFeedback
        
        # 第一次迭代
        feedback1 = CriticFeedback(
            overall_score=0.6,
            dimension_scores=[],
            issues=["缺少注释"],
            strengths=["算法正确"],
            needs_correction=True,
            feedback_text="需要改进"
        )
        
        history1 = ReflectionHistory(
            task_id=1,
            iteration=1,
            output="第一次输出",
            feedback=feedback1,
            suggestions=[],
            improvement_score=None
        )
        
        # 第二次迭代
        feedback2 = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["算法正确", "注释完整"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        history2 = ReflectionHistory(
            task_id=1,
            iteration=2,
            output="第二次输出",
            feedback=feedback2,
            suggestions=[],
            improvement_score=0.2
        )
        
        reflection_service.reflection_history = [history1, history2]
        
        # 分析改进效果
        analysis = reflection_service.analyze_improvement(task_id=1)
        
        assert analysis["task_id"] == 1
        assert analysis["total_iterations"] == 2
        assert analysis["initial_score"] == 0.6
        assert analysis["final_score"] == 0.8
        assert analysis["overall_improvement"] > 0
        assert analysis["effectiveness_score"] > 0
    
    def test_performance_stats(self, reflection_service):
        """测试性能统计"""
        # 添加模拟历史记录
        from app.core.reflection.schemas import ReflectionHistory, CriticFeedback
        
        feedback = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["质量良好"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        history = ReflectionHistory(
            task_id=1,
            iteration=1,
            output="测试输出",
            feedback=feedback,
            suggestions=[],
            improvement_score=0.2
        )
        
        reflection_service.reflection_history = [history]
        
        # 获取性能统计
        stats = reflection_service.get_performance_stats()
        
        assert "agent_stats" in stats
        assert "reflection_stats" in stats
        assert stats["reflection_stats"]["total_reflections"] == 1
        assert stats["reflection_stats"]["successful_reflections"] == 1
        assert stats["reflection_stats"]["success_rate"] == 1.0
    
    def test_export_reflection_data(self, reflection_service):
        """测试导出反思数据"""
        # 添加模拟历史记录
        from app.core.reflection.schemas import ReflectionHistory, CriticFeedback
        
        feedback = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["质量良好"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        history = ReflectionHistory(
            task_id=1,
            iteration=1,
            output="测试输出",
            feedback=feedback,
            suggestions=[],
            improvement_score=0.2
        )
        
        reflection_service.reflection_history = [history]
        
        # 导出数据
        export_data = reflection_service.export_reflection_data(task_id=1)
        
        assert "export_time" in export_data
        assert "task_id" in export_data
        assert "total_records" in export_data
        assert "reflection_history" in export_data
        assert "performance_stats" in export_data
        assert export_data["total_records"] == 1


class TestExecutorAgentIntegration:
    """执行Agent集成测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_tool_manager(self):
        """Mock工具管理器"""
        return Mock(spec=ToolManager)
    
    @pytest.fixture
    def executor_agent(self, mock_llm, mock_tool_manager):
        """执行Agent实例"""
        return ExecutorAgent(
            llm=mock_llm,
            tool_manager=mock_tool_manager
        )
    
    @pytest.fixture
    def sample_context(self):
        """示例执行上下文"""
        return ExecutionContext(
            task_description="生成一个排序函数",
            expected_goal="创建高效的排序算法",
            constraints=["使用Python"],
            context_info={"language": "python"}
        )
    
    @pytest.mark.asyncio
    async def test_executor_agent_without_reflection(self, executor_agent, sample_context, mock_llm):
        """测试执行Agent（不启用反思）"""
        # Mock LLM响应
        mock_llm.achat.return_value = "def quick_sort(arr):\n    return sorted(arr)"
        
        # 执行任务（不启用反思）
        result = await executor_agent.execute_with_reflection(
            context=sample_context,
            enable_reflection=False
        )
        
        # 验证结果
        assert result["success"] is True
        assert result["reflection_enabled"] is False
        assert "quick_sort" in result["output"]
        assert result["retry_count"] == 0
    
    @pytest.mark.asyncio
    async def test_executor_agent_with_reflection(self, executor_agent, sample_context, mock_llm):
        """测试执行Agent（启用反思）"""
        # Mock LLM响应序列
        mock_responses = [
            # 第一次执行
            "def sort(arr):\n    return sorted(arr)",
            
            # 评估
            '''{
                "overall_score": 0.6,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.7, "explanation": "基本正确"},
                    {"dimension": "completeness", "score": 0.5, "explanation": "不完整"},
                    {"dimension": "efficiency", "score": 0.6, "explanation": "效率一般"},
                    {"dimension": "clarity", "score": 0.6, "explanation": "不够清晰"}
                ],
                "issues": ["不满足要求"],
                "strengths": ["基本正确"],
                "needs_correction": true
            }''',
            
            # 纠错建议
            '''{
                "correction_suggestions": [
                    {
                        "issue": "不满足要求",
                        "suggestion": "实现快速排序算法",
                        "priority": 5,
                        "expected_improvement": "满足任务要求"
                    }
                ],
                "should_retry": true
            }''',
            
            # 第二次执行
            '''def quick_sort(arr):
    """
    快速排序算法
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)''',
            
            # 第二次评估
            '''{
                "overall_score": 0.9,
                "dimension_scores": [
                    {"dimension": "correctness", "score": 0.9, "explanation": "算法正确"},
                    {"dimension": "completeness", "score": 0.9, "explanation": "注释完整"},
                    {"dimension": "efficiency", "score": 0.9, "explanation": "效率良好"},
                    {"dimension": "clarity", "score": 0.9, "explanation": "结构清晰"}
                ],
                "issues": [],
                "strengths": ["算法正确", "注释完整", "结构清晰"],
                "needs_correction": false
            }'''
        ]
        
        mock_llm.achat.side_effect = mock_responses
        
        # 执行任务（启用反思）
        result = await executor_agent.execute_with_reflection(
            context=sample_context,
            enable_reflection=True,
            max_retries=3
        )
        
        # 验证结果
        assert result["success"] is True
        assert result["reflection_enabled"] is True
        assert result["retry_count"] == 1
        assert "快速排序" in result["output"]
        assert result["final_feedback"]["overall_score"] >= 0.8
    
    def test_executor_agent_performance_stats(self, executor_agent):
        """测试执行Agent性能统计"""
        # 获取初始统计
        stats = executor_agent.get_performance_stats()
        assert stats["total_executions"] == 0
        
        # 添加模拟执行历史
        from app.core.reflection.schemas import CriticFeedback
        
        feedback = CriticFeedback(
            overall_score=0.8,
            dimension_scores=[],
            issues=[],
            strengths=["质量良好"],
            needs_correction=False,
            feedback_text="质量良好"
        )
        
        executor_agent.execution_history.append({
            "retry_count": 0,
            "output": "测试输出",
            "feedback": feedback,
            "timestamp": datetime.utcnow()
        })
        
        # 获取更新后的统计
        updated_stats = executor_agent.get_performance_stats()
        assert updated_stats["total_executions"] == 1
        assert updated_stats["successful_executions"] == 1
        assert updated_stats["success_rate"] == 1.0
        assert updated_stats["average_score"] == 0.8
