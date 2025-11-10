"""
Workflow engine for task execution with DAG support.

This module provides functionality to execute task plans with support for:
- DAG-based task execution
- Conditional branching
- Task state management
- Error handling and retry
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from app.core.planning.schemas import (
    TaskPlan, TaskDefinition, DAG, ExecutionResult, WorkflowContext,
    TaskStatus, TaskType, Condition, LoopConfig, ParallelGroup
)
from app.core.planning.loop_executor import LoopExecutor
from app.core.planning.parallel_executor import ParallelExecutor
from app.dao.task_dao import TaskDAO
from app.tools.manager import ToolManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowEngine:
    """
    工作流引擎
    
    功能：
    - 管理任务队列和执行状态
    - 实现DAG拓扑排序执行
    - 支持条件分支执行
    - 处理任务失败和重试
    - 管理任务执行上下文
    """
    
    def __init__(self, task_dao: TaskDAO, tool_manager: ToolManager):
        """
        初始化工作流引擎
        
        参数:
            task_dao: 任务数据访问对象
            tool_manager: 工具管理器
        """
        self.task_dao = task_dao
        self.tool_manager = tool_manager
        self.execution_contexts: Dict[int, WorkflowContext] = {}
        self.loop_executor = LoopExecutor()
        self.parallel_executor = ParallelExecutor()
    
    async def execute_plan(self, plan: TaskPlan, conversation_id: int, user_id: int) -> ExecutionResult:
        """
        执行任务计划
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
            user_id: 用户ID
        
        返回:
            ExecutionResult: 执行结果
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"开始执行任务计划: {plan.name}")
            
            # 创建执行上下文
            context = WorkflowContext(
                conversation_id=conversation_id,
                user_id=user_id,
                metadata={"plan_name": plan.name}
            )
            self.execution_contexts[conversation_id] = context
            
            # 创建任务记录
            task_records = await self._create_task_records(plan, conversation_id)
            
            # 构建DAG
            dag = self._build_dag(plan, task_records)
            
            # 执行工作流
            result = await self._execute_dag(dag, context, task_records)
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 构建执行结果
            execution_result = ExecutionResult(
                success=result["success"],
                message=result["message"],
                task_results=context.task_results,
                execution_time=execution_time,
                metadata={
                    "plan_name": plan.name,
                    "total_tasks": len(task_records),
                    "completed_tasks": result["completed_count"],
                    "failed_tasks": result["failed_count"]
                }
            )
            
            logger.info(f"任务计划执行完成: {plan.name}, 耗时: {execution_time:.2f}秒")
            return execution_result
            
        except Exception as e:
            logger.error(f"执行任务计划失败: {str(e)}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExecutionResult(
                success=False,
                message=f"执行失败: {str(e)}",
                task_results=context.task_results if 'context' in locals() else {},
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
        finally:
            # 清理执行上下文
            if conversation_id in self.execution_contexts:
                del self.execution_contexts[conversation_id]
    
    async def _create_task_records(self, plan: TaskPlan, conversation_id: int) -> Dict[str, int]:
        """
        创建任务记录
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
        
        返回:
            Dict[str, int]: 任务名称到任务ID的映射
        """
        task_records = {}
        
        for task_def in plan.tasks:
            # 创建任务记录
            task = self.task_dao.create_task(
                conversation_id=conversation_id,
                task_type=task_def.task_type.value,
                description=task_def.description,
                priority=task_def.priority,
                metadata={
                    "name": task_def.name,
                    "conditions": [cond.dict() for cond in task_def.conditions] if task_def.conditions else None,
                    "tool_name": task_def.tool_name,
                    "tool_params": task_def.tool_params,
                    "original_metadata": task_def.metadata
                }
            )
            
            task_records[task_def.name] = task.id
            logger.debug(f"创建任务记录: {task_def.name} -> {task.id}")
        
        return task_records
    
    def _build_dag(self, plan: TaskPlan, task_records: Dict[str, int]) -> DAG:
        """
        构建任务依赖DAG
        
        参数:
            plan: 任务计划
            task_records: 任务记录映射
        
        返回:
            DAG: 任务依赖图
        """
        dag = DAG()
        
        # 添加节点
        for task_def in plan.tasks:
            task_id = task_records[task_def.name]
            dag.add_node(task_id, task_def)
        
        # 添加边（依赖关系）
        for task_name, deps in plan.dependencies.items():
            task_id = task_records[task_name]
            for dep_name in deps:
                dep_id = task_records[dep_name]
                dag.add_edge(dep_id, task_id)
        
        # 验证DAG
        if dag.detect_cycle():
            raise ValueError("任务依赖图中存在环")
        
        return dag
    
    async def _execute_dag(self, dag: DAG, context: WorkflowContext, task_records: Dict[str, int]) -> Dict[str, Any]:
        """
        执行DAG中的任务
        
        参数:
            dag: 任务依赖图
            context: 执行上下文
            task_records: 任务记录映射
        
        返回:
            Dict[str, Any]: 执行结果统计
        """
        completed_count = 0
        failed_count = 0
        success = True
        
        try:
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            for level in execution_levels:
                logger.info(f"执行层级: {[dag.node_data[task_id].name for task_id in level]}")
                
                # 并行执行当前层级的所有任务
                level_results = await self._execute_level(level, dag, context, task_records)
                
                # 统计结果
                for result in level_results:
                    if result["success"]:
                        completed_count += 1
                    else:
                        failed_count += 1
                        success = False
                
                # 如果当前层级有失败的任务，决定是否继续
                if not success and not self._should_continue_on_failure(level_results):
                    logger.warning("检测到失败任务，停止执行")
                    break
            
            return {
                "success": success,
                "message": f"执行完成，成功: {completed_count}, 失败: {failed_count}",
                "completed_count": completed_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"执行DAG失败: {str(e)}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "completed_count": completed_count,
                "failed_count": failed_count + 1
            }
    
    async def _execute_level(self, level: List[int], dag: DAG, context: WorkflowContext, task_records: Dict[str, int]) -> List[Dict[str, Any]]:
        """
        执行同一层级的任务
        
        参数:
            level: 任务ID列表
            dag: 任务依赖图
            context: 执行上下文
            task_records: 任务记录映射
        
        返回:
            List[Dict[str, Any]]: 执行结果列表
        """
        # 创建执行任务
        tasks = []
        for task_id in level:
            task_def = dag.node_data[task_id]
            task = self._create_execution_task(task_id, task_def, context, task_records)
            tasks.append(task)
        
        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "message": str(result),
                    "task_id": level[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _create_execution_task(self, task_id: int, task_def: TaskDefinition, context: WorkflowContext, task_records: Dict[str, int]):
        """
        创建执行任务
        
        参数:
            task_id: 任务ID
            task_def: 任务定义
            context: 执行上下文
            task_records: 任务记录映射
        
        返回:
            Coroutine: 执行任务协程
        """
        async def execute_single_task():
            try:
                # 检查执行条件
                if not self._check_execution_conditions(task_def, context):
                    logger.info(f"任务 {task_def.name} 跳过执行（条件不满足）")
                    self.task_dao.update_task_status(task_id, TaskStatus.SKIPPED.value)
                    return {
                        "success": True,
                        "message": "条件不满足，跳过执行",
                        "task_id": task_id
                    }
                
                # 开始执行
                logger.info(f"开始执行任务: {task_def.name}")
                self.task_dao.update_task_status(task_id, TaskStatus.RUNNING.value)
                
                # 执行任务
                result = await self._execute_task(task_def, context)
                
                # 更新任务状态
                if result["success"]:
                    self.task_dao.update_task_status(
                        task_id, 
                        TaskStatus.COMPLETED.value, 
                        result=result["message"]
                    )
                    context.set_task_result(task_def.name, result["data"])
                    logger.info(f"任务执行成功: {task_def.name}")
                else:
                    self.task_dao.update_task_status(
                        task_id,
                        TaskStatus.FAILED.value,
                        error_message=result["message"]
                    )
                    logger.error(f"任务执行失败: {task_def.name} - {result['message']}")
                
                return {
                    "success": result["success"],
                    "message": result["message"],
                    "task_id": task_id,
                    "data": result.get("data")
                }
                
            except Exception as e:
                logger.error(f"任务执行异常: {task_def.name} - {str(e)}")
                self.task_dao.update_task_status(
                    task_id,
                    TaskStatus.FAILED.value,
                    error_message=str(e)
                )
                return {
                    "success": False,
                    "message": str(e),
                    "task_id": task_id
                }
        
        return execute_single_task()
    
    def _check_execution_conditions(self, task_def: TaskDefinition, context: WorkflowContext) -> bool:
        """
        检查任务执行条件
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            bool: 是否满足执行条件
        """
        if not task_def.conditions:
            return True
        
        for condition in task_def.conditions:
            if not condition.evaluate(context.variables):
                logger.debug(f"条件不满足: {condition.field} {condition.operator} {condition.value}")
                return False
        
        return True
    
    async def _execute_task(self, task_def: TaskDefinition, context: WorkflowContext) -> Dict[str, Any]:
        """
        执行单个任务
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        try:
            if task_def.task_type == TaskType.TOOL_CALL:
                return await self._execute_tool_task(task_def, context)
            elif task_def.task_type == TaskType.PLAN:
                return await self._execute_plan_task(task_def, context)
            elif task_def.task_type == TaskType.EXECUTE:
                return await self._execute_execute_task(task_def, context)
            elif task_def.task_type == TaskType.REFLECT:
                return await self._execute_reflect_task(task_def, context)
            else:
                return {
                    "success": False,
                    "message": f"不支持的任务类型: {task_def.task_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"任务执行异常: {str(e)}"
            }
    
    async def _execute_tool_task(self, task_def: TaskDefinition, context: WorkflowContext) -> Dict[str, Any]:
        """
        执行工具调用任务
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        if not task_def.tool_name:
            return {
                "success": False,
                "message": "工具调用任务缺少工具名称"
            }
        
        try:
            # 获取工具
            tool = self.tool_manager.get_tool(task_def.tool_name)
            if not tool:
                return {
                    "success": False,
                    "message": f"工具不存在: {task_def.tool_name}"
                }
            
            # 准备工具参数
            params = task_def.tool_params or {}
            
            # 执行工具
            result = await tool.execute(**params)
            
            return {
                "success": True,
                "message": f"工具 {task_def.tool_name} 执行成功",
                "data": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"工具执行失败: {str(e)}"
            }
    
    async def _execute_plan_task(self, task_def: TaskDefinition, context: WorkflowContext) -> Dict[str, Any]:
        """
        执行规划任务
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        # 规划任务通常是分析和设计类任务
        # 这里可以集成更多的规划逻辑
        
        return {
            "success": True,
            "message": f"规划任务 {task_def.name} 执行完成",
            "data": {
                "task_type": "plan",
                "description": task_def.description,
                "metadata": task_def.metadata
            }
        }
    
    async def _execute_execute_task(self, task_def: TaskDefinition, context: WorkflowContext) -> Dict[str, Any]:
        """
        执行执行任务
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        # 执行任务通常是具体的操作任务
        # 这里可以集成更多的执行逻辑
        
        return {
            "success": True,
            "message": f"执行任务 {task_def.name} 执行完成",
            "data": {
                "task_type": "execute",
                "description": task_def.description,
                "metadata": task_def.metadata
            }
        }
    
    async def _execute_reflect_task(self, task_def: TaskDefinition, context: WorkflowContext) -> Dict[str, Any]:
        """
        执行反思任务
        
        参数:
            task_def: 任务定义
            context: 执行上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        # 反思任务通常是检查和验证类任务
        # 这里可以集成更多的反思逻辑
        
        return {
            "success": True,
            "message": f"反思任务 {task_def.name} 执行完成",
            "data": {
                "task_type": "reflect",
                "description": task_def.description,
                "metadata": task_def.metadata
            }
        }
    
    def _should_continue_on_failure(self, level_results: List[Dict[str, Any]]) -> bool:
        """
        判断在任务失败时是否应该继续执行
        
        参数:
            level_results: 层级执行结果
        
        返回:
            bool: 是否应该继续执行
        """
        # 简单的策略：如果失败任务数量超过一半，则停止执行
        failed_count = sum(1 for result in level_results if not result["success"])
        total_count = len(level_results)
        
        return failed_count < total_count / 2
    
    def get_execution_status(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Optional[Dict[str, Any]]: 执行状态信息
        """
        if conversation_id not in self.execution_contexts:
            return None
        
        context = self.execution_contexts[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "user_id": context.user_id,
            "variables": context.variables,
            "task_results": context.task_results,
            "created_at": context.created_at,
            "updated_at": context.updated_at
        }
    
    def cancel_execution(self, conversation_id: int) -> bool:
        """
        取消执行
        
        参数:
            conversation_id: 会话ID
        
        返回:
            bool: 是否成功取消
        """
        if conversation_id in self.execution_contexts:
            # 这里可以实现更复杂的取消逻辑
            del self.execution_contexts[conversation_id]
            logger.info(f"取消执行: {conversation_id}")
            return True
        
        return False
    
    async def execute_with_loop(self, 
                               plan: TaskPlan, 
                               conversation_id: int, 
                               user_id: int,
                               loop_configs: Dict[str, LoopConfig]) -> ExecutionResult:
        """
        支持循环执行的工作流
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
            user_id: 用户ID
            loop_configs: 循环配置映射
        
        返回:
            ExecutionResult: 执行结果
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"开始执行带循环的工作流: {plan.name}")
            
            # 创建执行上下文
            context = WorkflowContext(
                conversation_id=conversation_id,
                user_id=user_id,
                metadata={"plan_name": plan.name, "loop_configs": loop_configs}
            )
            self.execution_contexts[conversation_id] = context
            
            # 创建任务记录
            task_records = await self._create_task_records(plan, conversation_id)
            
            # 构建DAG
            dag = self._build_dag(plan, task_records)
            
            # 执行带循环的工作流
            result = await self._execute_dag_with_loops(dag, context, task_records, loop_configs)
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 构建执行结果
            execution_result = ExecutionResult(
                success=result["success"],
                message=result["message"],
                task_results=context.task_results,
                execution_time=execution_time,
                metadata={
                    "plan_name": plan.name,
                    "total_tasks": len(task_records),
                    "completed_tasks": result["completed_count"],
                    "failed_tasks": result["failed_count"],
                    "loop_executions": result.get("loop_executions", 0)
                }
            )
            
            logger.info(f"带循环的工作流执行完成: {plan.name}, 耗时: {execution_time:.2f}秒")
            return execution_result
            
        except Exception as e:
            logger.error(f"执行带循环的工作流失败: {str(e)}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExecutionResult(
                success=False,
                message=f"执行失败: {str(e)}",
                task_results=context.task_results if 'context' in locals() else {},
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
        finally:
            # 清理执行上下文
            if conversation_id in self.execution_contexts:
                del self.execution_contexts[conversation_id]
    
    async def execute_with_parallel(self, 
                                   plan: TaskPlan, 
                                   conversation_id: int, 
                                   user_id: int,
                                   parallel_groups: List[ParallelGroup]) -> ExecutionResult:
        """
        支持并行执行的工作流
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
            user_id: 用户ID
            parallel_groups: 并行组列表
        
        返回:
            ExecutionResult: 执行结果
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"开始执行带并行的工作流: {plan.name}")
            
            # 创建执行上下文
            context = WorkflowContext(
                conversation_id=conversation_id,
                user_id=user_id,
                metadata={"plan_name": plan.name, "parallel_groups": parallel_groups}
            )
            self.execution_contexts[conversation_id] = context
            
            # 创建任务记录
            task_records = await self._create_task_records(plan, conversation_id)
            
            # 构建DAG
            dag = self._build_dag(plan, task_records)
            
            # 执行带并行的工作流
            result = await self._execute_dag_with_parallel(dag, context, task_records, parallel_groups)
            
            # 计算执行时间
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 构建执行结果
            execution_result = ExecutionResult(
                success=result["success"],
                message=result["message"],
                task_results=context.task_results,
                execution_time=execution_time,
                metadata={
                    "plan_name": plan.name,
                    "total_tasks": len(task_records),
                    "completed_tasks": result["completed_count"],
                    "failed_tasks": result["failed_count"],
                    "parallel_groups": len(parallel_groups)
                }
            )
            
            logger.info(f"带并行的工作流执行完成: {plan.name}, 耗时: {execution_time:.2f}秒")
            return execution_result
            
        except Exception as e:
            logger.error(f"执行带并行的工作流失败: {str(e)}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ExecutionResult(
                success=False,
                message=f"执行失败: {str(e)}",
                task_results=context.task_results if 'context' in locals() else {},
                execution_time=execution_time,
                metadata={"error": str(e)}
            )
        finally:
            # 清理执行上下文
            if conversation_id in self.execution_contexts:
                del self.execution_contexts[conversation_id]
    
    async def _execute_dag_with_loops(self, 
                                     dag: DAG, 
                                     context: WorkflowContext, 
                                     task_records: Dict[str, int],
                                     loop_configs: Dict[str, LoopConfig]) -> Dict[str, Any]:
        """
        执行带循环的DAG
        
        参数:
            dag: 任务依赖图
            context: 执行上下文
            task_records: 任务记录映射
            loop_configs: 循环配置映射
        
        返回:
            Dict[str, Any]: 执行结果统计
        """
        completed_count = 0
        failed_count = 0
        success = True
        loop_executions = 0
        
        try:
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            for level in execution_levels:
                logger.info(f"执行层级: {[dag.node_data[task_id].name for task_id in level]}")
                
                # 检查是否有循环任务
                loop_tasks = []
                regular_tasks = []
                
                for task_id in level:
                    task_def = dag.node_data[task_id]
                    if task_def.name in loop_configs:
                        loop_tasks.append((task_id, task_def))
                    else:
                        regular_tasks.append((task_id, task_def))
                
                # 执行常规任务
                if regular_tasks:
                    level_results = await self._execute_level(
                        [task_id for task_id, _ in regular_tasks], dag, context, task_records
                    )
                    
                    for result in level_results:
                        if result["success"]:
                            completed_count += 1
                        else:
                            failed_count += 1
                            success = False
                
                # 执行循环任务
                for task_id, task_def in loop_tasks:
                    try:
                        loop_config = loop_configs[task_def.name]
                        loop_id = f"{task_def.name}_{task_id}"
                        
                        # 执行循环
                        loop_results = await self.loop_executor.execute_loop_config(
                            [task_def], loop_config, loop_id, context, self._execute_task_wrapper
                        )
                        
                        loop_executions += len(loop_results)
                        
                        # 统计结果
                        for loop_result in loop_results:
                            if loop_result.get("success", False):
                                completed_count += 1
                            else:
                                failed_count += 1
                                success = False
                        
                    except Exception as e:
                        logger.error(f"循环任务执行失败: {task_def.name}, 错误: {str(e)}")
                        failed_count += 1
                        success = False
                
                # 如果当前层级有失败的任务，决定是否继续
                if not success and not self._should_continue_on_failure([]):
                    logger.warning("检测到失败任务，停止执行")
                    break
            
            return {
                "success": success,
                "message": f"执行完成，成功: {completed_count}, 失败: {failed_count}, 循环执行: {loop_executions}",
                "completed_count": completed_count,
                "failed_count": failed_count,
                "loop_executions": loop_executions
            }
            
        except Exception as e:
            logger.error(f"执行带循环的DAG失败: {str(e)}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "completed_count": completed_count,
                "failed_count": failed_count + 1,
                "loop_executions": loop_executions
            }
    
    async def _execute_dag_with_parallel(self, 
                                        dag: DAG, 
                                        context: WorkflowContext, 
                                        task_records: Dict[str, int],
                                        parallel_groups: List[ParallelGroup]) -> Dict[str, Any]:
        """
        执行带并行的DAG
        
        参数:
            dag: 任务依赖图
            context: 执行上下文
            task_records: 任务记录映射
            parallel_groups: 并行组列表
        
        返回:
            Dict[str, Any]: 执行结果统计
        """
        completed_count = 0
        failed_count = 0
        success = True
        
        try:
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            for level in execution_levels:
                logger.info(f"执行层级: {[dag.node_data[task_id].name for task_id in level]}")
                
                # 检查是否有并行组
                parallel_tasks = []
                regular_tasks = []
                
                for task_id in level:
                    task_def = dag.node_data[task_id]
                    task_name = task_def.name
                    
                    # 检查是否属于某个并行组
                    in_parallel_group = False
                    for group in parallel_groups:
                        if task_name in group.task_names:
                            parallel_tasks.append((task_id, task_def, group))
                            in_parallel_group = True
                            break
                    
                    if not in_parallel_group:
                        regular_tasks.append((task_id, task_def))
                
                # 执行常规任务
                if regular_tasks:
                    level_results = await self._execute_level(
                        [task_id for task_id, _ in regular_tasks], dag, context, task_records
                    )
                    
                    for result in level_results:
                        if result["success"]:
                            completed_count += 1
                        else:
                            failed_count += 1
                            success = False
                
                # 执行并行任务
                if parallel_tasks:
                    # 按并行组分组
                    group_tasks = {}
                    for task_id, task_def, group in parallel_tasks:
                        group_id = id(group)
                        if group_id not in group_tasks:
                            group_tasks[group_id] = []
                        group_tasks[group_id].append((task_id, task_def))
                    
                    # 执行每个并行组
                    for group_id, tasks in group_tasks.items():
                        try:
                            execution_id = f"parallel_group_{group_id}"
                            task_defs = [task_def for _, task_def in tasks]
                            
                            # 并行执行
                            parallel_results = await self.parallel_executor.execute_parallel(
                                task_defs, execution_id, context, self._execute_task_wrapper
                            )
                            
                            # 统计结果
                            for result in parallel_results:
                                if result.get("success", False):
                                    completed_count += 1
                                else:
                                    failed_count += 1
                                    success = False
                        
                        except Exception as e:
                            logger.error(f"并行组执行失败: {str(e)}")
                            failed_count += len(tasks)
                            success = False
                
                # 如果当前层级有失败的任务，决定是否继续
                if not success and not self._should_continue_on_failure([]):
                    logger.warning("检测到失败任务，停止执行")
                    break
            
            return {
                "success": success,
                "message": f"执行完成，成功: {completed_count}, 失败: {failed_count}",
                "completed_count": completed_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"执行带并行的DAG失败: {str(e)}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "completed_count": completed_count,
                "failed_count": failed_count + 1
            }
    
    async def _execute_task_wrapper(self, 
                                   task_def: TaskDefinition, 
                                   context: WorkflowContext, 
                                   extra_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        任务执行包装器
        
        参数:
            task_def: 任务定义
            context: 工作流上下文
            extra_context: 额外上下文
        
        返回:
            Dict[str, Any]: 执行结果
        """
        return await self._execute_task(task_def, context)
