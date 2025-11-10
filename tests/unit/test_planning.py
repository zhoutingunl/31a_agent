"""
Planning module unit tests.

This module contains unit tests for the planning components including
task decomposition, workflow engine, and planning agents.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.core.planning.schemas import (
    TaskPlan, TaskDefinition, TaskType, Condition, ConditionOperator,
    DAG, ExecutionResult, WorkflowContext
)
from app.core.planning.task_decomposer import TaskDecomposer
from app.core.planning.workflow_engine import WorkflowEngine
from app.core.planning.loop_executor import LoopExecutor
from app.core.planning.parallel_executor import ParallelExecutor
from app.core.planning.dynamic_planner import DynamicPlanner


class TestTaskDecomposer:
    """测试任务分解器"""
    
    def test_init(self):
        """测试初始化"""
        decomposer = TaskDecomposer()
        assert decomposer is not None
        assert decomposer.llm is not None
    
    @patch('app.core.planning.task_decomposer.ChatOpenAI')
    def test_decompose_simple_request(self, mock_llm):
        """测试简单请求分解"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '''
        {
            "name": "测试计划",
            "description": "测试任务分解",
            "tasks": [
                {
                    "name": "任务1",
                    "description": "第一个任务",
                    "task_type": "plan",
                    "priority": 5
                },
                {
                    "name": "任务2", 
                    "description": "第二个任务",
                    "task_type": "execute",
                    "priority": 3
                }
            ],
            "dependencies": {
                "任务2": ["任务1"]
            },
            "metadata": {}
        }
        '''
        mock_llm.return_value.invoke.return_value = mock_response
        
        decomposer = TaskDecomposer()
        plan = decomposer.decompose("帮我写一个简单的Python脚本")
        
        assert plan.name == "测试计划"
        assert len(plan.tasks) == 2
        assert plan.tasks[0].name == "任务1"
        assert plan.tasks[1].name == "任务2"
        assert "任务2" in plan.dependencies
        assert "任务1" in plan.dependencies["任务2"]
    
    def test_analyze_dependencies(self):
        """测试依赖关系分析"""
        decomposer = TaskDecomposer()
        
        tasks = [
            TaskDefinition(
                name="plan_task",
                description="规划任务",
                task_type=TaskType.PLAN,
                priority=5
            ),
            TaskDefinition(
                name="execute_task",
                description="执行任务",
                task_type=TaskType.EXECUTE,
                priority=3
            )
        ]
        
        dependencies = decomposer.analyze_dependencies(tasks)
        
        # 执行任务应该依赖规划任务
        assert "execute_task" in dependencies
        assert "plan_task" in dependencies["execute_task"]


class TestDAG:
    """测试有向无环图"""
    
    def test_add_nodes_and_edges(self):
        """测试添加节点和边"""
        dag = DAG()
        
        # 添加节点
        dag.add_node(1, "task1")
        dag.add_node(2, "task2")
        dag.add_node(3, "task3")
        
        assert 1 in dag.nodes
        assert 2 in dag.nodes
        assert 3 in dag.nodes
        
        # 添加边
        dag.add_edge(1, 2)
        dag.add_edge(2, 3)
        
        assert 2 in dag.get_children(1)
        assert 3 in dag.get_children(2)
        assert 1 in dag.get_parents(2)
        assert 2 in dag.get_parents(3)
    
    def test_topological_sort(self):
        """测试拓扑排序"""
        dag = DAG()
        
        # 构建简单的DAG: 1 -> 2 -> 3
        dag.add_node(1, "task1")
        dag.add_node(2, "task2")
        dag.add_node(3, "task3")
        dag.add_edge(1, 2)
        dag.add_edge(2, 3)
        
        sorted_order = dag.topological_sort()
        assert sorted_order == [1, 2, 3]
    
    def test_detect_cycle(self):
        """测试环检测"""
        dag = DAG()
        
        # 构建有环的图: 1 -> 2 -> 3 -> 1
        dag.add_node(1, "task1")
        dag.add_node(2, "task2")
        dag.add_node(3, "task3")
        dag.add_edge(1, 2)
        dag.add_edge(2, 3)
        dag.add_edge(3, 1)  # 形成环
        
        assert dag.detect_cycle() == True
    
    def test_get_execution_levels(self):
        """测试获取执行层级"""
        dag = DAG()
        
        # 构建DAG: 1 -> 2,3 -> 4
        dag.add_node(1, "task1")
        dag.add_node(2, "task2")
        dag.add_node(3, "task3")
        dag.add_node(4, "task4")
        dag.add_edge(1, 2)
        dag.add_edge(1, 3)
        dag.add_edge(2, 4)
        dag.add_edge(3, 4)
        
        levels = dag.get_execution_levels()
        assert len(levels) == 3
        assert levels[0] == [1]  # 第一层：只有任务1
        assert set(levels[1]) == {2, 3}  # 第二层：任务2和3可以并行
        assert levels[2] == [4]  # 第三层：任务4


class TestCondition:
    """测试执行条件"""
    
    def test_equals_condition(self):
        """测试等于条件"""
        condition = Condition(
            field="status",
            operator=ConditionOperator.EQUALS,
            value="completed"
        )
        
        context = {"status": "completed"}
        assert condition.evaluate(context) == True
        
        context = {"status": "failed"}
        assert condition.evaluate(context) == False
    
    def test_nested_field_condition(self):
        """测试嵌套字段条件"""
        condition = Condition(
            field="result.status",
            operator=ConditionOperator.EQUALS,
            value="success"
        )
        
        context = {"result": {"status": "success"}}
        assert condition.evaluate(context) == True
        
        context = {"result": {"status": "error"}}
        assert condition.evaluate(context) == False
    
    def test_contains_condition(self):
        """测试包含条件"""
        condition = Condition(
            field="message",
            operator=ConditionOperator.CONTAINS,
            value="error"
        )
        
        context = {"message": "An error occurred"}
        assert condition.evaluate(context) == True
        
        context = {"message": "Success"}
        assert condition.evaluate(context) == False


class TestLoopExecutor:
    """测试循环执行器"""
    
    def test_init(self):
        """测试初始化"""
        executor = LoopExecutor()
        assert executor is not None
        assert executor.active_loops == {}
    
    @pytest.mark.asyncio
    async def test_execute_for_loop(self):
        """测试for循环执行"""
        executor = LoopExecutor()
        
        # Mock任务执行函数
        async def mock_task_executor(task, context, extra_context):
            return {"success": True, "message": f"执行了 {task.name}"}
        
        tasks = [
            TaskDefinition(
                name="test_task",
                description="测试任务",
                task_type=TaskType.EXECUTE,
                priority=5
            )
        ]
        
        items = ["item1", "item2", "item3"]
        context = WorkflowContext(conversation_id=1, user_id=1)
        
        results = await executor.execute_for_loop(
            tasks, items, "test_loop", context, mock_task_executor
        )
        
        assert len(results) == 3
        assert all(result["success"] for result in results)
        assert results[0]["item"] == "item1"
        assert results[1]["item"] == "item2"
        assert results[2]["item"] == "item3"


class TestParallelExecutor:
    """测试并行执行器"""
    
    def test_init(self):
        """测试初始化"""
        executor = ParallelExecutor(max_workers=5)
        assert executor is not None
        assert executor.max_workers == 5
        assert executor.active_executions == {}
    
    def test_identify_parallel_tasks(self):
        """测试识别并行任务"""
        executor = ParallelExecutor()
        
        # 构建DAG
        dag = DAG()
        dag.add_node(1, "task1")
        dag.add_node(2, "task2")
        dag.add_node(3, "task3")
        dag.add_node(4, "task4")
        dag.add_edge(1, 2)
        dag.add_edge(1, 3)
        dag.add_edge(2, 4)
        dag.add_edge(3, 4)
        
        parallel_levels = executor.identify_parallel_tasks(dag)
        
        assert len(parallel_levels) == 1  # 只有一层可以并行
        assert set(parallel_levels[0]) == {2, 3}  # 任务2和3可以并行
    
    def test_analyze_parallel_potential(self):
        """测试分析并行潜力"""
        executor = ParallelExecutor()
        
        tasks = [
            TaskDefinition(
                name="task1",
                description="任务1",
                task_type=TaskType.EXECUTE,
                priority=5
            ),
            TaskDefinition(
                name="task2",
                description="任务2",
                task_type=TaskType.EXECUTE,
                priority=3
            ),
            TaskDefinition(
                name="task3",
                description="任务3",
                task_type=TaskType.EXECUTE,
                priority=4
            )
        ]
        
        dependencies = {
            "task2": ["task1"],
            "task3": ["task1"]
        }
        
        analysis = executor.analyze_parallel_potential(tasks, dependencies)
        
        assert analysis["total_tasks"] == 3
        assert analysis["execution_levels"] == 2
        assert analysis["parallel_levels"] == 1
        assert analysis["max_parallel_tasks"] == 2


class TestDynamicPlanner:
    """测试动态计划修改器"""
    
    def test_init(self):
        """测试初始化"""
        planner = DynamicPlanner()
        assert planner is not None
        assert planner.active_modifications == {}
    
    def test_add_task_runtime(self):
        """测试运行时添加任务"""
        planner = DynamicPlanner()
        
        # 创建基础计划
        plan = TaskPlan(
            name="测试计划",
            description="测试计划描述",
            tasks=[
                TaskDefinition(
                    name="parent_task",
                    description="父任务",
                    task_type=TaskType.EXECUTE,
                    priority=5
                )
            ],
            dependencies={}
        )
        
        # 创建新任务
        new_task = TaskDefinition(
            name="new_task",
            description="新任务",
            task_type=TaskType.EXECUTE,
            priority=3
        )
        
        context = WorkflowContext(conversation_id=1, user_id=1)
        
        # 模拟添加任务
        modified_plan = planner.add_task_runtime(1, new_task, plan, context)
        
        assert len(modified_plan.tasks) == 2
        assert "new_task" in [task.name for task in modified_plan.tasks]
        assert "new_task" in modified_plan.dependencies
        assert "parent_task" in modified_plan.dependencies["new_task"]
    
    def test_select_optimal_path(self):
        """测试选择最优路径"""
        planner = DynamicPlanner()
        
        plan = TaskPlan(
            name="测试计划",
            description="测试计划描述",
            tasks=[
                TaskDefinition(
                    name="task1",
                    description="任务1",
                    task_type=TaskType.EXECUTE,
                    priority=5,
                    metadata={"estimated_time": 300}
                ),
                TaskDefinition(
                    name="task2",
                    description="任务2",
                    task_type=TaskType.EXECUTE,
                    priority=3,
                    metadata={"estimated_time": 60}
                )
            ],
            dependencies={}
        )
        
        context = WorkflowContext(conversation_id=1, user_id=1)
        constraints = {"max_time": 600}
        
        optimized_plan = planner.select_optimal_path(plan, context, constraints)
        
        # 快速任务应该优先级更高
        task2 = next(task for task in optimized_plan.tasks if task.name == "task2")
        assert task2.priority > 3  # 优先级应该被提高


if __name__ == "__main__":
    pytest.main([__file__])
