"""
Planner Agent for intelligent task planning and execution.

This module provides a unified interface for task planning,
integrating task decomposition and workflow execution.
"""

from typing import Dict, Any, Optional, AsyncGenerator, List, Union, Iterator
from datetime import datetime

from app.core.agent.base import BaseAgent
from app.core.llm.base import BaseLLM
from app.core.planning.task_decomposer import TaskDecomposer
from app.core.planning.workflow_engine import WorkflowEngine
from app.core.planning.schemas import TaskPlan, ExecutionResult
from app.dao.task_dao import TaskDAO
from app.tools.manager import ToolManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlannerAgent(BaseAgent):
    """
    规划Agent
    
    功能：
    - 整合任务分解器和工作流引擎
    - 提供统一的规划接口
    - 管理任务执行生命周期
    - 支持流式执行进度反馈
    """
    
    def __init__(self, task_dao: TaskDAO, tool_manager: ToolManager, llm: Optional[BaseLLM] = None, llm_model: str = "deepseek-chat"):
        """
        初始化规划Agent
        
        参数:
            task_dao: 任务数据访问对象
            tool_manager: 工具管理器
            llm: LLM实例（可选，用于直接LLM调用）
            llm_model: LLM模型名称（用于TaskDecomposer）
        """
        super().__init__(llm)
        self.task_dao = task_dao
        self.tool_manager = tool_manager
        self.decomposer = TaskDecomposer(llm_model)
        self.workflow_engine = WorkflowEngine(task_dao, tool_manager)
    
    async def plan_and_execute(self, 
                             request: str, 
                             conversation_id: int, 
                             user_id: int,
                             context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        规划并执行任务
        
        参数:
            request: 用户请求
            conversation_id: 会话ID
            user_id: 用户ID
            context: 上下文信息
        
        返回:
            ExecutionResult: 执行结果
        """
        try:
            logger.info(f"开始规划任务: {request[:100]}...")
            
            # 1. 分解任务
            plan = self.decomposer.decompose(request, context or {})
            logger.info(f"任务分解完成，共 {len(plan.tasks)} 个任务")
            
            # 2. 执行工作流
            result = await self.workflow_engine.execute_plan(plan, conversation_id, user_id)
            
            logger.info(f"任务执行完成: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"规划执行失败: {str(e)}")
            return ExecutionResult(
                success=False,
                message=f"规划执行失败: {str(e)}",
                task_results={},
                execution_time=0.0,
                metadata={"error": str(e)}
            )
    
    async def plan_and_execute_stream(self, 
                                    request: str, 
                                    conversation_id: int, 
                                    user_id: int,
                                    context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式规划并执行任务
        
        参数:
            request: 用户请求
            conversation_id: 会话ID
            user_id: 用户ID
            context: 上下文信息
        
        返回:
            AsyncGenerator[Dict[str, Any], None]: 流式执行进度
        """
        try:
            # 发送开始消息
            yield {
                "type": "start",
                "message": "开始分析任务...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 1. 分解任务
            yield {
                "type": "decomposing",
                "message": "正在分解任务...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            plan = self.decomposer.decompose(request, context or {})
            
            yield {
                "type": "decomposed",
                "message": f"任务分解完成，共 {len(plan.tasks)} 个任务",
                "data": {
                    "plan_name": plan.name,
                    "total_tasks": len(plan.tasks),
                    "tasks": [
                        {
                            "name": task.name,
                            "description": task.description,
                            "type": task.task_type.value,
                            "priority": task.priority
                        }
                        for task in plan.tasks
                    ]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 2. 开始执行
            yield {
                "type": "executing",
                "message": "开始执行任务...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 执行工作流并流式返回进度
            async for progress in self._execute_with_progress(plan, conversation_id, user_id):
                yield progress
            
        except Exception as e:
            logger.error(f"流式规划执行失败: {str(e)}")
            yield {
                "type": "error",
                "message": f"执行失败: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _execute_with_progress(self, 
                                   plan: TaskPlan, 
                                   conversation_id: int, 
                                   user_id: int) -> AsyncGenerator[Dict[str, Any], None]:
        """
        带进度的执行工作流
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
            user_id: 用户ID
        
        返回:
            AsyncGenerator[Dict[str, Any], None]: 执行进度流
        """
        try:
            # 创建任务记录
            task_records = await self.workflow_engine._create_task_records(plan, conversation_id)
            
            # 构建DAG
            dag = self.workflow_engine._build_dag(plan, task_records)
            
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            total_levels = len(execution_levels)
            completed_levels = 0
            
            for level_idx, level in enumerate(execution_levels):
                level_name = f"第 {level_idx + 1} 层"
                level_tasks = [dag.node_data[task_id].name for task_id in level]
                
                yield {
                    "type": "level_start",
                    "message": f"开始执行 {level_name}",
                    "data": {
                        "level": level_idx + 1,
                        "total_levels": total_levels,
                        "tasks": level_tasks
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 执行当前层级
                level_results = await self.workflow_engine._execute_level(
                    level, dag, 
                    self.workflow_engine.execution_contexts.get(conversation_id), 
                    task_records
                )
                
                # 发送任务结果
                for result in level_results:
                    task_name = dag.node_data[result["task_id"]].name
                    yield {
                        "type": "task_completed",
                        "message": f"任务 {task_name} 执行{'成功' if result['success'] else '失败'}",
                        "data": {
                            "task_name": task_name,
                            "success": result["success"],
                            "message": result["message"]
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                completed_levels += 1
                
                yield {
                    "type": "level_completed",
                    "message": f"{level_name} 执行完成",
                    "data": {
                        "level": level_idx + 1,
                        "total_levels": total_levels,
                        "progress": completed_levels / total_levels
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # 发送完成消息
            yield {
                "type": "completed",
                "message": "所有任务执行完成",
                "data": {
                    "total_levels": total_levels,
                    "total_tasks": len(task_records)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"带进度执行失败: {str(e)}")
            yield {
                "type": "error",
                "message": f"执行失败: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_execution_status(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Optional[Dict[str, Any]]: 执行状态
        """
        return self.workflow_engine.get_execution_status(conversation_id)
    
    async def cancel_execution(self, conversation_id: int) -> bool:
        """
        取消执行
        
        参数:
            conversation_id: 会话ID
        
        返回:
            bool: 是否成功取消
        """
        return self.workflow_engine.cancel_execution(conversation_id)
    
    async def get_task_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Dict[str, Any]: 任务统计信息
        """
        return self.task_dao.get_task_statistics(conversation_id)
    
    async def suggest_optimization(self, conversation_id: int) -> Dict[str, Any]:
        """
        建议优化方案
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Dict[str, Any]: 优化建议
        """
        try:
            # 获取任务统计
            stats = await self.get_task_statistics(conversation_id)
            
            # 获取任务列表
            tasks = self.task_dao.get_tasks_by_conversation_simple(conversation_id)
            
            suggestions = []
            
            # 分析执行时间
            if stats["failed"] > 0:
                suggestions.append({
                    "type": "error_handling",
                    "message": f"有 {stats['failed']} 个任务失败，建议检查错误处理机制",
                    "priority": "high"
                })
            
            # 分析任务类型分布
            task_types = {}
            for task in tasks:
                task_type = task.task_type
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            if task_types.get("plan", 0) == 0:
                suggestions.append({
                    "type": "planning",
                    "message": "缺少规划类任务，建议增加前期分析",
                    "priority": "medium"
                })
            
            if task_types.get("reflect", 0) == 0:
                suggestions.append({
                    "type": "reflection",
                    "message": "缺少反思类任务，建议增加结果验证",
                    "priority": "medium"
                })
            
            # 分析并行执行机会
            parallel_opportunities = self._analyze_parallel_opportunities(tasks)
            if parallel_opportunities:
                suggestions.append({
                    "type": "parallelization",
                    "message": f"发现 {len(parallel_opportunities)} 个并行执行机会",
                    "data": parallel_opportunities,
                    "priority": "low"
                })
            
            return {
                "suggestions": suggestions,
                "statistics": stats,
                "task_types": task_types
            }
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {str(e)}")
            return {
                "suggestions": [],
                "error": str(e)
            }
    
    def _analyze_parallel_opportunities(self, tasks) -> List[Dict[str, Any]]:
        """
        分析并行执行机会
        
        参数:
            tasks: 任务列表
        
        返回:
            List[Dict[str, Any]]: 并行执行机会列表
        """
        opportunities = []
        
        # 简单的启发式分析
        # 1. 相同类型的独立任务
        task_groups = {}
        for task in tasks:
            if task.task_type not in task_groups:
                task_groups[task.task_type] = []
            task_groups[task.task_type].append(task)
        
        for task_type, task_list in task_groups.items():
            if len(task_list) > 1:
                # 检查是否都是独立任务（没有依赖）
                independent_tasks = [t for t in task_list if not t.dependencies]
                if len(independent_tasks) > 1:
                    opportunities.append({
                        "type": "same_type_independent",
                        "task_type": task_type,
                        "tasks": [t.description for t in independent_tasks],
                        "potential_speedup": len(independent_tasks)
                    })
        
        return opportunities

    def run(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """
        运行 Agent（实现抽象方法）
        
        参数:
            messages: 消息列表
            stream: 是否流式输出
            **kwargs: 其他参数
            
        返回:
            Union[str, Iterator[str]]: 回复内容或流式迭代器
        """
        # 对于PlannerAgent，我们使用plan_and_execute方法
        # 这里简化实现，实际使用时应该根据消息内容决定是否进行规划
        if not messages:
            return "没有收到消息"
        
        last_message = messages[-1]
        request = last_message.get("content", "")
        
        # 同步调用异步方法（简化处理）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 使用默认参数
        conversation_id = kwargs.get("conversation_id", 1)
        user_id = kwargs.get("user_id", 1)
        
        result = loop.run_until_complete(
            self.plan_and_execute(request, conversation_id, user_id)
        )
        
        if result.success:
            return result.message
        else:
            return f"规划执行失败: {result.message}"
