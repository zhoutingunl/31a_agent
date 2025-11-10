"""
Dynamic planner for runtime plan modification.

This module provides functionality for:
- Runtime task addition
- Plan adjustment based on execution context
- Intelligent path selection
- Adaptive workflow management
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime

from app.core.planning.schemas import (
    TaskPlan, TaskDefinition, TaskType, DAG, WorkflowContext, Condition
)
from app.core.planning.task_decomposer import TaskDecomposer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DynamicPlanner:
    """
    动态计划修改器
    
    功能：
    - 运行时动态添加任务
    - 调整执行计划
    - 智能路径选择
    - 自适应工作流管理
    """
    
    def __init__(self):
        """初始化动态计划修改器"""
        self.decomposer = None  # 延迟初始化，避免LLM依赖
        self.active_modifications: Dict[str, Dict[str, Any]] = {}
    
    async def add_task_runtime(self, 
                              parent_task_id: int, 
                              new_task: TaskDefinition,
                              plan: TaskPlan,
                              context: WorkflowContext) -> TaskPlan:
        """
        运行时动态添加任务
        
        参数:
            parent_task_id: 父任务ID
            new_task: 新任务定义
            plan: 当前任务计划
            context: 工作流上下文
        
        返回:
            TaskPlan: 修改后的任务计划
        """
        try:
            logger.info(f"动态添加任务: {new_task.name}, 父任务: {parent_task_id}")
            
            # 创建修改记录
            modification_id = f"add_{new_task.name}_{datetime.utcnow().timestamp()}"
            self.active_modifications[modification_id] = {
                "type": "add_task",
                "parent_task_id": parent_task_id,
                "new_task": new_task,
                "timestamp": datetime.utcnow()
            }
            
            # 添加新任务到计划
            modified_plan = plan.copy(deep=True)
            modified_plan.tasks.append(new_task)
            
            # 更新依赖关系
            if new_task.name not in modified_plan.dependencies:
                modified_plan.dependencies[new_task.name] = []
            
            # 找到父任务名称
            parent_task_name = None
            for task in plan.tasks:
                if hasattr(task, 'id') and task.id == parent_task_id:
                    parent_task_name = task.name
                    break
            
            if parent_task_name:
                modified_plan.dependencies[new_task.name].append(parent_task_name)
            
            # 更新元数据
            modified_plan.metadata["modifications"] = modified_plan.metadata.get("modifications", [])
            modified_plan.metadata["modifications"].append({
                "type": "add_task",
                "task_name": new_task.name,
                "parent_task_id": parent_task_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"任务添加成功: {new_task.name}")
            return modified_plan
            
        except Exception as e:
            logger.error(f"动态添加任务失败: {str(e)}")
            raise
    
    async def adjust_plan(self, 
                         plan: TaskPlan, 
                         execution_context: Dict[str, Any],
                         context: WorkflowContext) -> TaskPlan:
        """
        根据执行情况调整计划
        
        参数:
            plan: 当前任务计划
            execution_context: 执行上下文
            context: 工作流上下文
        
        返回:
            TaskPlan: 调整后的任务计划
        """
        try:
            logger.info("开始调整任务计划")
            
            modified_plan = plan.copy(deep=True)
            adjustments_made = []
            
            # 1. 根据失败任务调整计划
            failed_tasks = execution_context.get("failed_tasks", [])
            if failed_tasks:
                adjustments = await self._handle_failed_tasks(modified_plan, failed_tasks, context)
                adjustments_made.extend(adjustments)
            
            # 2. 根据执行时间调整优先级
            execution_times = execution_context.get("execution_times", {})
            if execution_times:
                adjustments = await self._adjust_priorities_by_time(modified_plan, execution_times)
                adjustments_made.extend(adjustments)
            
            # 3. 根据资源使用情况调整计划
            resource_usage = execution_context.get("resource_usage", {})
            if resource_usage:
                adjustments = await self._adjust_for_resources(modified_plan, resource_usage)
                adjustments_made.extend(adjustments)
            
            # 4. 根据用户反馈调整计划
            user_feedback = execution_context.get("user_feedback", {})
            if user_feedback:
                adjustments = await self._adjust_based_on_feedback(modified_plan, user_feedback)
                adjustments_made.extend(adjustments)
            
            # 更新元数据
            if adjustments_made:
                modified_plan.metadata["adjustments"] = modified_plan.metadata.get("adjustments", [])
                modified_plan.metadata["adjustments"].extend(adjustments_made)
                modified_plan.metadata["last_adjusted"] = datetime.utcnow().isoformat()
            
            logger.info(f"计划调整完成，共进行 {len(adjustments_made)} 项调整")
            return modified_plan
            
        except Exception as e:
            logger.error(f"调整计划失败: {str(e)}")
            raise
    
    async def _handle_failed_tasks(self, 
                                  plan: TaskPlan, 
                                  failed_tasks: List[Dict[str, Any]], 
                                  context: WorkflowContext) -> List[Dict[str, Any]]:
        """
        处理失败任务
        
        参数:
            plan: 任务计划
            failed_tasks: 失败任务列表
            context: 工作流上下文
        
        返回:
            List[Dict[str, Any]]: 调整记录
        """
        adjustments = []
        
        for failed_task in failed_tasks:
            task_name = failed_task.get("name")
            error_message = failed_task.get("error", "")
            
            # 找到对应的任务定义
            task_def = None
            for task in plan.tasks:
                if task.name == task_name:
                    task_def = task
                    break
            
            if not task_def:
                continue
            
            # 根据错误类型决定调整策略
            if "timeout" in error_message.lower():
                # 超时错误：增加重试或分解任务
                adjustments.append({
                    "type": "add_retry",
                    "task_name": task_name,
                    "reason": "timeout_error",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # 添加重试任务
                retry_task = TaskDefinition(
                    name=f"{task_name}_retry",
                    description=f"重试任务: {task_def.description}",
                    task_type=TaskType.RETRY,
                    priority=task_def.priority + 1,
                    tool_name=task_def.tool_name,
                    tool_params=task_def.tool_params,
                    metadata={"original_task": task_name, "retry_count": 1}
                )
                plan.tasks.append(retry_task)
                plan.dependencies[retry_task.name] = [task_name]
            
            elif "resource" in error_message.lower():
                # 资源错误：降低优先级或延迟执行
                task_def.priority = max(1, task_def.priority - 2)
                adjustments.append({
                    "type": "reduce_priority",
                    "task_name": task_name,
                    "new_priority": task_def.priority,
                    "reason": "resource_error",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            elif "dependency" in error_message.lower():
                # 依赖错误：调整依赖关系
                adjustments.append({
                    "type": "adjust_dependencies",
                    "task_name": task_name,
                    "reason": "dependency_error",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return adjustments
    
    async def _adjust_priorities_by_time(self, 
                                        plan: TaskPlan, 
                                        execution_times: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        根据执行时间调整优先级
        
        参数:
            plan: 任务计划
            execution_times: 执行时间映射
        
        返回:
            List[Dict[str, Any]]: 调整记录
        """
        adjustments = []
        
        # 计算平均执行时间
        if not execution_times:
            return adjustments
        
        avg_time = sum(execution_times.values()) / len(execution_times)
        
        for task in plan.tasks:
            task_time = execution_times.get(task.name, avg_time)
            
            # 如果任务执行时间过长，降低优先级
            if task_time > avg_time * 2:
                old_priority = task.priority
                task.priority = max(1, task.priority - 1)
                adjustments.append({
                    "type": "reduce_priority",
                    "task_name": task.name,
                    "old_priority": old_priority,
                    "new_priority": task.priority,
                    "reason": "long_execution_time",
                    "execution_time": task_time,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # 如果任务执行时间很短，提高优先级
            elif task_time < avg_time * 0.5:
                old_priority = task.priority
                task.priority = min(10, task.priority + 1)
                adjustments.append({
                    "type": "increase_priority",
                    "task_name": task.name,
                    "old_priority": old_priority,
                    "new_priority": task.priority,
                    "reason": "short_execution_time",
                    "execution_time": task_time,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return adjustments
    
    async def _adjust_for_resources(self, 
                                   plan: TaskPlan, 
                                   resource_usage: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据资源使用情况调整计划
        
        参数:
            plan: 任务计划
            resource_usage: 资源使用情况
        
        返回:
            List[Dict[str, Any]]: 调整记录
        """
        adjustments = []
        
        # 检查内存使用
        memory_usage = resource_usage.get("memory", 0)
        if memory_usage > 0.8:  # 内存使用超过80%
            # 降低并行度，提高任务优先级
            for task in plan.tasks:
                if task.task_type == TaskType.PARALLEL:
                    task.priority = min(10, task.priority + 1)
                    adjustments.append({
                        "type": "increase_priority",
                        "task_name": task.name,
                        "reason": "high_memory_usage",
                        "memory_usage": memory_usage,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # 检查CPU使用
        cpu_usage = resource_usage.get("cpu", 0)
        if cpu_usage > 0.9:  # CPU使用超过90%
            # 降低计算密集型任务的优先级
            for task in plan.tasks:
                if "计算" in task.description or "分析" in task.description:
                    old_priority = task.priority
                    task.priority = max(1, task.priority - 1)
                    adjustments.append({
                        "type": "reduce_priority",
                        "task_name": task.name,
                        "old_priority": old_priority,
                        "new_priority": task.priority,
                        "reason": "high_cpu_usage",
                        "cpu_usage": cpu_usage,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        return adjustments
    
    async def _adjust_based_on_feedback(self, 
                                       plan: TaskPlan, 
                                       user_feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据用户反馈调整计划
        
        参数:
            plan: 任务计划
            user_feedback: 用户反馈
        
        返回:
            List[Dict[str, Any]]: 调整记录
        """
        adjustments = []
        
        # 处理用户满意度反馈
        satisfaction = user_feedback.get("satisfaction", 0)
        if satisfaction < 0.5:  # 满意度低于50%
            # 增加反思和验证任务
            for task in plan.tasks:
                if task.task_type == TaskType.REFLECT:
                    task.priority = min(10, task.priority + 2)
                    adjustments.append({
                        "type": "increase_priority",
                        "task_name": task.name,
                        "reason": "low_satisfaction",
                        "satisfaction": satisfaction,
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # 处理用户建议
        suggestions = user_feedback.get("suggestions", [])
        for suggestion in suggestions:
            if suggestion.get("type") == "add_task":
                # 根据用户建议添加新任务
                new_task = TaskDefinition(
                    name=suggestion.get("name", f"user_suggested_{datetime.utcnow().timestamp()}"),
                    description=suggestion.get("description", "用户建议的任务"),
                    task_type=TaskType.EXECUTE,
                    priority=suggestion.get("priority", 5),
                    metadata={"source": "user_suggestion", "suggestion": suggestion}
                )
                plan.tasks.append(new_task)
                adjustments.append({
                    "type": "add_user_suggested_task",
                    "task_name": new_task.name,
                    "suggestion": suggestion,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return adjustments
    
    def select_optimal_path(self, 
                           plan: TaskPlan, 
                           context: WorkflowContext,
                           constraints: Dict[str, Any]) -> TaskPlan:
        """
        选择最优执行路径
        
        参数:
            plan: 任务计划
            context: 工作流上下文
            constraints: 约束条件
        
        返回:
            TaskPlan: 优化后的任务计划
        """
        try:
            logger.info("开始选择最优执行路径")
            
            # 复制计划
            optimized_plan = plan.copy(deep=True)
            
            # 1. 根据时间约束优化
            time_constraint = constraints.get("max_time")
            if time_constraint:
                optimized_plan = self._optimize_for_time(optimized_plan, time_constraint)
            
            # 2. 根据资源约束优化
            resource_constraint = constraints.get("max_resources")
            if resource_constraint:
                optimized_plan = self._optimize_for_resources(optimized_plan, resource_constraint)
            
            # 3. 根据质量约束优化
            quality_constraint = constraints.get("min_quality")
            if quality_constraint:
                optimized_plan = self._optimize_for_quality(optimized_plan, quality_constraint)
            
            logger.info("最优路径选择完成")
            return optimized_plan
            
        except Exception as e:
            logger.error(f"选择最优路径失败: {str(e)}")
            return plan
    
    def _optimize_for_time(self, plan: TaskPlan, max_time: float) -> TaskPlan:
        """根据时间约束优化计划"""
        # 简单的启发式优化：提高快速任务的优先级
        for task in plan.tasks:
            estimated_time = task.metadata.get("estimated_time", 300)  # 默认5分钟
            if estimated_time < 60:  # 少于1分钟的任务
                task.priority = min(10, task.priority + 1)
        
        return plan
    
    def _optimize_for_resources(self, plan: TaskPlan, max_resources: Dict[str, float]) -> TaskPlan:
        """根据资源约束优化计划"""
        # 根据资源限制调整任务优先级
        for task in plan.tasks:
            resource_requirement = task.metadata.get("resource_requirement", {})
            
            # 检查内存需求
            memory_req = resource_requirement.get("memory", 0)
            if memory_req > max_resources.get("memory", 1.0) * 0.5:
                task.priority = max(1, task.priority - 1)
            
            # 检查CPU需求
            cpu_req = resource_requirement.get("cpu", 0)
            if cpu_req > max_resources.get("cpu", 1.0) * 0.5:
                task.priority = max(1, task.priority - 1)
        
        return plan
    
    def _optimize_for_quality(self, plan: TaskPlan, min_quality: float) -> TaskPlan:
        """根据质量约束优化计划"""
        # 提高质量相关任务的优先级
        for task in plan.tasks:
            if task.task_type == TaskType.REFLECT or "验证" in task.description or "检查" in task.description:
                task.priority = min(10, task.priority + 1)
        
        return plan
    
    def get_modification_history(self, plan: TaskPlan) -> List[Dict[str, Any]]:
        """
        获取计划修改历史
        
        参数:
            plan: 任务计划
        
        返回:
            List[Dict[str, Any]]: 修改历史
        """
        modifications = plan.metadata.get("modifications", [])
        adjustments = plan.metadata.get("adjustments", [])
        
        history = modifications + adjustments
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return history
    
    def get_active_modifications(self) -> Dict[str, Dict[str, Any]]:
        """
        获取活跃的修改
        
        返回:
            Dict[str, Dict[str, Any]]: 活跃修改信息
        """
        return self.active_modifications.copy()
    
    def cancel_modification(self, modification_id: str) -> bool:
        """
        取消修改
        
        参数:
            modification_id: 修改ID
        
        返回:
            bool: 是否成功取消
        """
        if modification_id in self.active_modifications:
            del self.active_modifications[modification_id]
            logger.info(f"取消修改: {modification_id}")
            return True
        return False
