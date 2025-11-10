"""
Parallel executor for concurrent task execution.

This module provides functionality for:
- Identifying parallelizable tasks
- Managing concurrent execution
- Aggregating parallel results
- Handling timeouts and errors
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from app.core.planning.schemas import (
    TaskDefinition, DAG, ParallelGroup, WorkflowContext
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParallelExecutor:
    """
    并行执行器
    
    功能：
    - 识别可并行执行的任务
    - 管理并发执行
    - 聚合并行任务结果
    - 处理超时和错误
    """
    
    def __init__(self, max_workers: int = 10):
        """
        初始化并行执行器
        
        参数:
            max_workers: 最大并发工作线程数
        """
        self.max_workers = max_workers
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute_parallel(self, 
                              tasks: List[TaskDefinition], 
                              execution_id: str,
                              context: WorkflowContext,
                              task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any],
                              timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        并行执行任务列表
        
        参数:
            tasks: 要并行执行的任务列表
            execution_id: 执行ID
            context: 工作流上下文
            task_executor: 任务执行函数
            timeout: 超时时间（秒）
        
        返回:
            List[Dict[str, Any]]: 执行结果列表
        """
        try:
            logger.info(f"开始并行执行: {execution_id}, 任务数: {len(tasks)}")
            
            execution_context = {
                "execution_id": execution_id,
                "total_tasks": len(tasks),
                "completed_tasks": 0,
                "failed_tasks": 0,
                "started_at": datetime.utcnow()
            }
            
            self.active_executions[execution_id] = execution_context
            
            # 创建执行任务
            execution_tasks = []
            for i, task in enumerate(tasks):
                exec_task = self._create_parallel_task(
                    task, i, context, task_executor, execution_id
                )
                execution_tasks.append(exec_task)
            
            # 并行执行
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*execution_tasks, return_exceptions=True),
                    timeout=timeout
                )
            else:
                results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # 处理结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "task_index": i,
                        "task_name": tasks[i].name,
                        "success": False,
                        "error": str(result),
                        "timestamp": datetime.utcnow()
                    })
                    execution_context["failed_tasks"] += 1
                else:
                    processed_results.append(result)
                    if result.get("success", False):
                        execution_context["completed_tasks"] += 1
                    else:
                        execution_context["failed_tasks"] += 1
            
            # 清理执行上下文
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            logger.info(f"并行执行完成: {execution_id}, 成功: {execution_context['completed_tasks']}, 失败: {execution_context['failed_tasks']}")
            return processed_results
            
        except asyncio.TimeoutError:
            logger.error(f"并行执行超时: {execution_id}")
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            raise
        except Exception as e:
            logger.error(f"并行执行失败: {execution_id}, 错误: {str(e)}")
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            raise
    
    def _create_parallel_task(self, 
                             task: TaskDefinition, 
                             task_index: int,
                             context: WorkflowContext,
                             task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any],
                             execution_id: str):
        """
        创建并行执行任务
        
        参数:
            task: 任务定义
            task_index: 任务索引
            context: 工作流上下文
            task_executor: 任务执行函数
            execution_id: 执行ID
        
        返回:
            Coroutine: 执行任务协程
        """
        async def execute_single_parallel_task():
            try:
                logger.debug(f"开始并行执行任务: {task.name}")
                
                # 设置任务上下文
                task_context = {
                    "execution_id": execution_id,
                    "task_index": task_index,
                    "parallel_execution": True
                }
                
                # 执行任务
                result = await task_executor(task, context, task_context)
                
                return {
                    "task_index": task_index,
                    "task_name": task.name,
                    "success": result.get("success", False),
                    "result": result,
                    "timestamp": datetime.utcnow()
                }
                
            except Exception as e:
                logger.error(f"并行任务执行失败: {task.name}, 错误: {str(e)}")
                return {
                    "task_index": task_index,
                    "task_name": task.name,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                }
        
        return execute_single_parallel_task()
    
    def identify_parallel_tasks(self, dag: DAG) -> List[List[int]]:
        """
        识别DAG中可并行执行的任务层级
        
        参数:
            dag: 任务依赖图
        
        返回:
            List[List[int]]: 可并行执行的任务层级列表
        """
        try:
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            # 过滤出可以并行的层级（包含多个任务）
            parallel_levels = []
            for level in execution_levels:
                if len(level) > 1:
                    parallel_levels.append(level)
            
            logger.debug(f"识别到 {len(parallel_levels)} 个可并行层级")
            return parallel_levels
            
        except Exception as e:
            logger.error(f"识别并行任务失败: {str(e)}")
            return []
    
    async def execute_parallel_groups(self, 
                                    parallel_groups: List[ParallelGroup],
                                    context: WorkflowContext,
                                    task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        执行并行组
        
        参数:
            parallel_groups: 并行组列表
            context: 工作流上下文
            task_executor: 任务执行函数
        
        返回:
            Dict[str, List[Dict[str, Any]]]: 各组执行结果
        """
        try:
            logger.info(f"开始执行 {len(parallel_groups)} 个并行组")
            
            group_results = {}
            
            for group in parallel_groups:
                group_id = f"group_{id(group)}"
                logger.debug(f"执行并行组: {group_id}, 任务: {group.task_names}")
                
                # 这里需要根据任务名称获取任务定义
                # 假设context中有任务定义映射
                tasks = []
                for task_name in group.task_names:
                    task_def = context.metadata.get("task_definitions", {}).get(task_name)
                    if task_def:
                        tasks.append(task_def)
                    else:
                        logger.warning(f"未找到任务定义: {task_name}")
                
                if tasks:
                    try:
                        results = await self.execute_parallel(
                            tasks, group_id, context, task_executor, group.timeout
                        )
                        group_results[group_id] = results
                    except Exception as e:
                        logger.error(f"并行组 {group_id} 执行失败: {str(e)}")
                        group_results[group_id] = [{
                            "success": False,
                            "error": str(e),
                            "timestamp": datetime.utcnow()
                        }]
                else:
                    logger.warning(f"并行组 {group_id} 没有有效任务")
                    group_results[group_id] = []
            
            logger.info(f"并行组执行完成，成功组数: {sum(1 for results in group_results.values() if any(r.get('success', False) for r in results))}")
            return group_results
            
        except Exception as e:
            logger.error(f"执行并行组失败: {str(e)}")
            raise
    
    def analyze_parallel_potential(self, tasks: List[TaskDefinition], dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        分析并行执行潜力
        
        参数:
            tasks: 任务列表
            dependencies: 依赖关系
        
        返回:
            Dict[str, Any]: 并行潜力分析结果
        """
        try:
            # 构建DAG
            dag = DAG()
            task_name_to_id = {task.name: i for i, task in enumerate(tasks)}
            
            # 添加节点
            for task in tasks:
                dag.add_node(task_name_to_id[task.name], task.name)
            
            # 添加边
            for task_name, deps in dependencies.items():
                if task_name in task_name_to_id:
                    task_id = task_name_to_id[task_name]
                    for dep in deps:
                        if dep in task_name_to_id:
                            dep_id = task_name_to_id[dep]
                            dag.add_edge(dep_id, task_id)
            
            # 获取执行层级
            execution_levels = dag.get_execution_levels()
            
            # 分析并行潜力
            total_tasks = len(tasks)
            parallel_levels = [level for level in execution_levels if len(level) > 1]
            max_parallel_tasks = max(len(level) for level in execution_levels) if execution_levels else 1
            
            # 计算理论加速比
            sequential_time = total_tasks  # 假设每个任务耗时1单位
            parallel_time = len(execution_levels)  # 并行执行时间等于层级数
            theoretical_speedup = sequential_time / parallel_time if parallel_time > 0 else 1
            
            # 识别独立任务
            independent_tasks = []
            for task in tasks:
                if task.name not in dependencies or not dependencies[task.name]:
                    independent_tasks.append(task.name)
            
            return {
                "total_tasks": total_tasks,
                "execution_levels": len(execution_levels),
                "parallel_levels": len(parallel_levels),
                "max_parallel_tasks": max_parallel_tasks,
                "independent_tasks": len(independent_tasks),
                "theoretical_speedup": theoretical_speedup,
                "parallel_efficiency": len(parallel_levels) / len(execution_levels) if execution_levels else 0,
                "recommendations": self._generate_parallel_recommendations(
                    total_tasks, len(parallel_levels), len(independent_tasks), theoretical_speedup
                )
            }
            
        except Exception as e:
            logger.error(f"分析并行潜力失败: {str(e)}")
            return {
                "error": str(e),
                "total_tasks": len(tasks),
                "parallel_levels": 0,
                "theoretical_speedup": 1
            }
    
    def _generate_parallel_recommendations(self, 
                                         total_tasks: int, 
                                         parallel_levels: int, 
                                         independent_tasks: int, 
                                         theoretical_speedup: float) -> List[str]:
        """
        生成并行执行建议
        
        参数:
            total_tasks: 总任务数
            parallel_levels: 并行层级数
            independent_tasks: 独立任务数
            theoretical_speedup: 理论加速比
        
        返回:
            List[str]: 建议列表
        """
        recommendations = []
        
        if independent_tasks > 1:
            recommendations.append(f"发现 {independent_tasks} 个独立任务，可以完全并行执行")
        
        if parallel_levels > 0:
            recommendations.append(f"有 {parallel_levels} 个层级可以并行执行")
        
        if theoretical_speedup > 2:
            recommendations.append(f"理论加速比达到 {theoretical_speedup:.1f}x，建议使用并行执行")
        elif theoretical_speedup < 1.5:
            recommendations.append("并行执行收益有限，建议保持串行执行")
        
        if total_tasks > 20 and parallel_levels == 0:
            recommendations.append("任务数量较多但缺乏并行机会，建议重新设计任务依赖关系")
        
        return recommendations
    
    def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        """
        获取活跃的执行
        
        返回:
            Dict[str, Dict[str, Any]]: 活跃执行信息
        """
        return self.active_executions.copy()
    
    def cancel_execution(self, execution_id: str) -> bool:
        """
        取消执行
        
        参数:
            execution_id: 执行ID
        
        返回:
            bool: 是否成功取消
        """
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
            logger.info(f"取消并行执行: {execution_id}")
            return True
        return False
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        参数:
            execution_id: 执行ID
        
        返回:
            Optional[Dict[str, Any]]: 执行状态信息
        """
        if execution_id not in self.active_executions:
            return None
        
        exec_info = self.active_executions[execution_id].copy()
        exec_info["duration"] = (datetime.utcnow() - exec_info["started_at"]).total_seconds()
        exec_info["progress"] = exec_info["completed_tasks"] / exec_info["total_tasks"] if exec_info["total_tasks"] > 0 else 0
        
        return exec_info
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)
