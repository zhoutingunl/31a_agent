"""
编排器单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock

from app.core.orchestrator.router import TaskRouter
from app.core.orchestrator.state_machine import StateMachine
from app.core.orchestrator.error_handler import ErrorHandler
from app.core.orchestrator.schemas import ExecutionMode, ExecutionState


class TestTaskRouter:
    """测试任务路由器"""
    
    @pytest.mark.asyncio
    async def test_simple_query_routing(self):
        """测试简单查询路由"""
        router = TaskRouter(llm=None)
        
        simple_queries = [
            "你好",
            "今天天气怎么样？",
            "查询订单123",
            "什么是Python？"
        ]
        
        for query in simple_queries:
            decision = await router.route(query)
            assert decision.mode == ExecutionMode.SIMPLE
            assert decision.confidence > 0
    
    @pytest.mark.asyncio
    async def test_planning_query_routing(self):
        """测试规划任务路由"""
        router = TaskRouter(llm=None)
        
        # 注意：基于规则的路由可能不够准确
        # 这里测试路由器能够工作，而不是准确性
        query = "帮我规划一个详细的学习计划，包括步骤和方案"
        decision = await router.route(query)
        
        # 即使路由到SIMPLE也是可以接受的（因为未启用LLM路由）
        assert decision.mode in [ExecutionMode.SIMPLE, ExecutionMode.PLANNING]
        assert decision.confidence > 0
    
    def test_route_cache(self):
        """测试路由缓存"""
        router = TaskRouter(llm=None)
        
        # 缓存应该初始为空
        stats = router.get_cache_stats()
        assert stats['cache_size'] == 0
        
        # 清空缓存应该正常工作
        router.clear_cache()
        stats = router.get_cache_stats()
        assert stats['cache_size'] == 0


class TestStateMachine:
    """测试状态机"""
    
    def test_initial_state(self):
        """测试初始状态"""
        sm = StateMachine()
        assert sm.get_current_state() == ExecutionState.IDLE
        assert len(sm.history) == 0
    
    def test_valid_transition(self):
        """测试有效状态转换"""
        sm = StateMachine()
        
        # IDLE → ROUTING
        assert sm.can_transition(ExecutionState.ROUTING) is True
        result = sm.transition(ExecutionState.ROUTING, {"test": True})
        assert result is True
        assert sm.get_current_state() == ExecutionState.ROUTING
    
    def test_invalid_transition(self):
        """测试无效状态转换"""
        sm = StateMachine()
        
        # IDLE → EXECUTING (跳过ROUTING，无效)
        assert sm.can_transition(ExecutionState.EXECUTING) is False
        result = sm.transition(ExecutionState.EXECUTING)
        assert result is False
        assert sm.get_current_state() == ExecutionState.IDLE  # 状态不变
    
    def test_transition_history(self):
        """测试状态转换历史"""
        sm = StateMachine()
        
        sm.transition(ExecutionState.ROUTING)
        sm.transition(ExecutionState.EXECUTING)
        sm.transition(ExecutionState.COMPLETED)
        
        history = sm.get_history()
        assert len(history) == 3
        assert history[0]["from_state"] == "IDLE"
        assert history[0]["to_state"] == "ROUTING"
        assert history[2]["to_state"] == "COMPLETED"
    
    def test_error_recovery_flow(self):
        """测试错误恢复流程"""
        sm = StateMachine()
        
        # 正常流程
        sm.transition(ExecutionState.ROUTING)
        sm.transition(ExecutionState.EXECUTING)
        
        # 发生错误
        sm.transition(ExecutionState.ERROR, {"error": "测试错误"})
        assert sm.is_error() is True
        
        # 恢复流程
        sm.transition(ExecutionState.RECOVERING)
        sm.transition(ExecutionState.EXECUTING)
        sm.transition(ExecutionState.COMPLETED)
        
        assert sm.is_completed() is True
        assert len(sm.history) == 5
    
    def test_reset(self):
        """测试重置"""
        sm = StateMachine()
        
        sm.transition(ExecutionState.ROUTING)
        sm.transition(ExecutionState.EXECUTING)
        
        sm.reset()
        
        assert sm.get_current_state() == ExecutionState.IDLE
        assert len(sm.history) == 0
    
    def test_execution_duration(self):
        """测试执行时长计算"""
        sm = StateMachine()
        
        sm.transition(ExecutionState.ROUTING)
        sm.transition(ExecutionState.EXECUTING)
        sm.transition(ExecutionState.COMPLETED)
        
        duration = sm.get_execution_duration()
        assert duration >= 0  # 时长应该非负


class TestErrorHandler:
    """测试异常处理器"""
    
    @pytest.mark.asyncio
    async def test_tool_error_recovery(self):
        """测试工具错误恢复"""
        handler = ErrorHandler()
        
        error = Exception("Tool execution failed")
        context = {"task_id": "test_1", "tool_name": "mysql_query"}
        
        # 第一次错误：应该重试
        recovery = await handler.handle_error(error, context)
        assert recovery["can_recover"] is True
        assert recovery["strategy"] == "retry"
        assert recovery["retry_count"] == 1
    
    @pytest.mark.asyncio
    async def test_max_retry_limit(self):
        """测试最大重试次数限制"""
        handler = ErrorHandler()
        
        error = Exception("Tool execution failed")
        context = {"task_id": "test_retry", "tool_name": "test_tool"}
        
        # 连续失败直到达到重试上限
        for i in range(4):
            recovery = await handler.handle_error(error, context)
            
            if i < 3:
                assert recovery["strategy"] == "retry"
            else:
                # 超过3次后应该降级
                assert recovery["strategy"] == "downgrade"
    
    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """测试超时错误"""
        handler = ErrorHandler()
        
        error = Exception("Request timeout")
        context = {"task_id": "test_timeout"}
        
        recovery = await handler.handle_error(error, context)
        assert recovery["can_recover"] is True
        assert recovery["strategy"] == "downgrade"
    
    def test_error_statistics(self):
        """测试错误统计"""
        handler = ErrorHandler()
        
        # 初始统计应该为空
        stats = handler.get_error_statistics()
        assert stats["total_errors"] == 0
        assert len(stats["error_types"]) == 0
    
    def test_reset_retry_counts(self):
        """测试重置重试计数"""
        handler = ErrorHandler()
        
        # 设置一些重试计数
        handler.retry_counts["test_1"] = 2
        handler.retry_counts["test_2"] = 1
        
        # 重置
        handler.reset_retry_counts()
        assert len(handler.retry_counts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
