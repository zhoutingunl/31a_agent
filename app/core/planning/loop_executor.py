"""
Loop executor for handling iterative task execution.

This module provides functionality for:
- For loops (iterating over items)
- While loops (conditional iteration)
- Retry mechanisms with backoff
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Union
from datetime import datetime, timedelta

from app.core.planning.schemas import (
    TaskDefinition, LoopConfig, LoopType, Condition, WorkflowContext
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LoopExecutor:
    """
    循环执行器
    
    功能：
    - 支持for循环（遍历列表）
    - 支持while循环（条件循环）
    - 支持智能重试（带退避策略）
    - 管理循环状态和上下文
    """
    
    def __init__(self):
        """初始化循环执行器"""
        self.active_loops: Dict[str, Dict[str, Any]] = {}
    
    async def execute_for_loop(self, 
                              tasks: List[TaskDefinition], 
                              items: List[Any],
                              loop_id: str,
                              context: WorkflowContext,
                              task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any]) -> List[Dict[str, Any]]:
        """
        执行for循环
        
        参数:
            tasks: 要循环执行的任务列表
            items: 要遍历的项目列表
            loop_id: 循环ID
            context: 工作流上下文
            task_executor: 任务执行函数
        
        返回:
            List[Dict[str, Any]]: 所有迭代的执行结果
        """
        try:
            logger.info(f"开始执行for循环: {loop_id}, 项目数: {len(items)}")
            
            results = []
            loop_context = {
                "loop_id": loop_id,
                "loop_type": "for",
                "total_items": len(items),
                "current_index": 0,
                "started_at": datetime.utcnow()
            }
            
            self.active_loops[loop_id] = loop_context
            
            for index, item in enumerate(items):
                try:
                    # 更新循环上下文
                    loop_context["current_index"] = index
                    loop_context["current_item"] = item
                    
                    # 设置上下文变量
                    context.set_variable(f"{loop_id}_current_item", item)
                    context.set_variable(f"{loop_id}_current_index", index)
                    context.set_variable(f"{loop_id}_total_items", len(items))
                    
                    logger.debug(f"For循环 {loop_id} 迭代 {index + 1}/{len(items)}: {item}")
                    
                    # 执行任务列表
                    iteration_results = []
                    for task in tasks:
                        result = await task_executor(task, context, {"loop_item": item, "loop_index": index})
                        iteration_results.append(result)
                    
                    results.append({
                        "index": index,
                        "item": item,
                        "success": all(r.get("success", False) for r in iteration_results),
                        "results": iteration_results,
                        "timestamp": datetime.utcnow()
                    })
                    
                except Exception as e:
                    logger.error(f"For循环 {loop_id} 迭代 {index} 失败: {str(e)}")
                    results.append({
                        "index": index,
                        "item": item,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow()
                    })
            
            # 清理循环上下文
            if loop_id in self.active_loops:
                del self.active_loops[loop_id]
            
            logger.info(f"For循环 {loop_id} 执行完成，成功: {sum(1 for r in results if r['success'])}/{len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"For循环 {loop_id} 执行失败: {str(e)}")
            if loop_id in self.active_loops:
                del self.active_loops[loop_id]
            raise
    
    async def execute_while_loop(self, 
                                tasks: List[TaskDefinition], 
                                condition: Condition,
                                max_iterations: int,
                                loop_id: str,
                                context: WorkflowContext,
                                task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any]) -> List[Dict[str, Any]]:
        """
        执行while循环
        
        参数:
            tasks: 要循环执行的任务列表
            condition: 循环条件
            max_iterations: 最大迭代次数
            loop_id: 循环ID
            context: 工作流上下文
            task_executor: 任务执行函数
        
        返回:
            List[Dict[str, Any]]: 所有迭代的执行结果
        """
        try:
            logger.info(f"开始执行while循环: {loop_id}, 最大迭代: {max_iterations}")
            
            results = []
            iteration = 0
            loop_context = {
                "loop_id": loop_id,
                "loop_type": "while",
                "max_iterations": max_iterations,
                "current_iteration": 0,
                "started_at": datetime.utcnow()
            }
            
            self.active_loops[loop_id] = loop_context
            
            while iteration < max_iterations:
                try:
                    # 检查循环条件
                    if not condition.evaluate(context.variables):
                        logger.info(f"While循环 {loop_id} 条件不满足，退出循环")
                        break
                    
                    # 更新循环上下文
                    loop_context["current_iteration"] = iteration
                    
                    # 设置上下文变量
                    context.set_variable(f"{loop_id}_current_iteration", iteration)
                    context.set_variable(f"{loop_id}_max_iterations", max_iterations)
                    
                    logger.debug(f"While循环 {loop_id} 迭代 {iteration + 1}/{max_iterations}")
                    
                    # 执行任务列表
                    iteration_results = []
                    for task in tasks:
                        result = await task_executor(task, context, {"loop_iteration": iteration})
                        iteration_results.append(result)
                    
                    results.append({
                        "iteration": iteration,
                        "success": all(r.get("success", False) for r in iteration_results),
                        "results": iteration_results,
                        "condition_met": condition.evaluate(context.variables),
                        "timestamp": datetime.utcnow()
                    })
                    
                    iteration += 1
                    
                except Exception as e:
                    logger.error(f"While循环 {loop_id} 迭代 {iteration} 失败: {str(e)}")
                    results.append({
                        "iteration": iteration,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow()
                    })
                    iteration += 1
            
            # 检查是否达到最大迭代次数
            if iteration >= max_iterations:
                logger.warning(f"While循环 {loop_id} 达到最大迭代次数: {max_iterations}")
            
            # 清理循环上下文
            if loop_id in self.active_loops:
                del self.active_loops[loop_id]
            
            logger.info(f"While循环 {loop_id} 执行完成，迭代次数: {iteration}")
            return results
            
        except Exception as e:
            logger.error(f"While循环 {loop_id} 执行失败: {str(e)}")
            if loop_id in self.active_loops:
                del self.active_loops[loop_id]
            raise
    
    async def execute_with_retry(self, 
                                task: TaskDefinition,
                                max_retries: int,
                                retry_delay: float,
                                backoff_factor: float,
                                retry_id: str,
                                context: WorkflowContext,
                                task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any]) -> Dict[str, Any]:
        """
        执行带重试的任务
        
        参数:
            task: 要执行的任务
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            backoff_factor: 退避因子
            retry_id: 重试ID
            context: 工作流上下文
            task_executor: 任务执行函数
        
        返回:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始执行带重试的任务: {retry_id}, 最大重试: {max_retries}")
            
            retry_context = {
                "retry_id": retry_id,
                "max_retries": max_retries,
                "current_attempt": 0,
                "started_at": datetime.utcnow()
            }
            
            last_error = None
            
            for attempt in range(max_retries + 1):  # +1 因为包含首次尝试
                try:
                    retry_context["current_attempt"] = attempt
                    
                    # 设置上下文变量
                    context.set_variable(f"{retry_id}_current_attempt", attempt)
                    context.set_variable(f"{retry_id}_max_retries", max_retries)
                    
                    if attempt > 0:
                        logger.info(f"重试任务 {retry_id} 第 {attempt} 次尝试")
                    
                    # 执行任务
                    result = await task_executor(task, context, {"attempt": attempt})
                    
                    if result.get("success", False):
                        logger.info(f"任务 {retry_id} 执行成功，尝试次数: {attempt + 1}")
                        return {
                            "success": True,
                            "result": result,
                            "attempts": attempt + 1,
                            "total_time": (datetime.utcnow() - retry_context["started_at"]).total_seconds()
                        }
                    else:
                        last_error = result.get("message", "任务执行失败")
                        
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"任务 {retry_id} 第 {attempt + 1} 次尝试失败: {str(e)}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries:
                    delay = retry_delay * (backoff_factor ** attempt)
                    logger.debug(f"等待 {delay:.2f} 秒后重试...")
                    await asyncio.sleep(delay)
            
            # 所有重试都失败了
            logger.error(f"任务 {retry_id} 重试 {max_retries} 次后仍然失败")
            return {
                "success": False,
                "error": last_error,
                "attempts": max_retries + 1,
                "total_time": (datetime.utcnow() - retry_context["started_at"]).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"重试任务 {retry_id} 执行异常: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "attempts": 0,
                "total_time": 0
            }
    
    async def execute_loop_config(self, 
                                 tasks: List[TaskDefinition],
                                 config: LoopConfig,
                                 loop_id: str,
                                 context: WorkflowContext,
                                 task_executor: Callable[[TaskDefinition, WorkflowContext, Dict[str, Any]], Any]) -> List[Dict[str, Any]]:
        """
        根据配置执行循环
        
        参数:
            tasks: 任务列表
            config: 循环配置
            loop_id: 循环ID
            context: 工作流上下文
            task_executor: 任务执行函数
        
        返回:
            List[Dict[str, Any]]: 执行结果
        """
        try:
            if config.type == LoopType.FOR:
                if not config.items:
                    raise ValueError("For循环必须指定items")
                return await self.execute_for_loop(
                    tasks, config.items, loop_id, context, task_executor
                )
            
            elif config.type == LoopType.WHILE:
                if not config.condition:
                    raise ValueError("While循环必须指定condition")
                return await self.execute_while_loop(
                    tasks, config.condition, config.max_iterations, loop_id, context, task_executor
                )
            
            elif config.type == LoopType.RETRY:
                if len(tasks) != 1:
                    raise ValueError("重试循环只能包含一个任务")
                result = await self.execute_with_retry(
                    tasks[0], config.max_iterations, config.retry_delay, 
                    config.backoff_factor, loop_id, context, task_executor
                )
                return [result]
            
            else:
                raise ValueError(f"不支持的循环类型: {config.type}")
                
        except Exception as e:
            logger.error(f"执行循环配置失败: {str(e)}")
            raise
    
    def get_active_loops(self) -> Dict[str, Dict[str, Any]]:
        """
        获取活跃的循环
        
        返回:
            Dict[str, Dict[str, Any]]: 活跃循环信息
        """
        return self.active_loops.copy()
    
    def cancel_loop(self, loop_id: str) -> bool:
        """
        取消循环执行
        
        参数:
            loop_id: 循环ID
        
        返回:
            bool: 是否成功取消
        """
        if loop_id in self.active_loops:
            del self.active_loops[loop_id]
            logger.info(f"取消循环: {loop_id}")
            return True
        return False
    
    def get_loop_status(self, loop_id: str) -> Optional[Dict[str, Any]]:
        """
        获取循环状态
        
        参数:
            loop_id: 循环ID
        
        返回:
            Optional[Dict[str, Any]]: 循环状态信息
        """
        if loop_id not in self.active_loops:
            return None
        
        loop_info = self.active_loops[loop_id].copy()
        loop_info["duration"] = (datetime.utcnow() - loop_info["started_at"]).total_seconds()
        
        return loop_info
