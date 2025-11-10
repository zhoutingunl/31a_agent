"""
Planning service for business logic encapsulation.

This module provides high-level business logic for task planning,
integrating with the planning components and providing a clean API.
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime

from app.core.planning.task_decomposer import TaskDecomposer
from app.core.planning.workflow_engine import WorkflowEngine
from app.core.planning.schemas import TaskPlan, ExecutionResult
from app.core.agent.planner_agent import PlannerAgent
from app.dao.task_dao import TaskDAO
from app.tools.manager import ToolManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlanningService:
    """
    规划服务
    
    功能：
    - 提供任务规划的业务逻辑封装
    - 管理规划Agent的生命周期
    - 提供高级API接口
    - 处理业务规则和验证
    """
    
    def __init__(self, task_dao: TaskDAO, tool_manager: ToolManager):
        """
        初始化规划服务
        
        参数:
            task_dao: 任务数据访问对象
            tool_manager: 工具管理器
        """
        self.task_dao = task_dao
        self.tool_manager = tool_manager
        self._planner_agent = None
    
    @property
    def planner_agent(self) -> PlannerAgent:
        """获取规划Agent实例"""
        if self._planner_agent is None:
            self._planner_agent = PlannerAgent(self.task_dao, self.tool_manager)
        return self._planner_agent
    
    async def plan_task(self, 
                       request: str, 
                       conversation_id: int, 
                       user_id: int,
                       context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """
        规划任务（仅分解，不执行）
        
        参数:
            request: 用户请求
            conversation_id: 会话ID
            user_id: 用户ID
            context: 上下文信息
        
        返回:
            TaskPlan: 任务计划
        """
        try:
            logger.info(f"开始规划任务: {request[:100]}...")
            
            # 验证请求
            if not self._validate_request(request):
                raise ValueError("请求格式无效")
            
            # 创建任务分解器
            decomposer = TaskDecomposer()
            
            # 分解任务
            plan = decomposer.decompose(request, context or {})
            
            logger.info(f"任务规划完成: {plan.name}, 共 {len(plan.tasks)} 个任务")
            return plan
            
        except Exception as e:
            logger.error(f"任务规划失败: {str(e)}")
            raise
    
    async def execute_plan(self, 
                          plan: TaskPlan, 
                          conversation_id: int, 
                          user_id: int) -> ExecutionResult:
        """
        执行任务计划
        
        参数:
            plan: 任务计划
            conversation_id: 会话ID
            user_id: 用户ID
        
        返回:
            ExecutionResult: 执行结果
        """
        try:
            logger.info(f"开始执行计划: {plan.name}")
            
            # 验证计划
            if not self._validate_plan(plan):
                raise ValueError("任务计划无效")
            
            # 执行计划
            result = await self.planner_agent.plan_and_execute(
                "",  # 空请求，因为计划已经存在
                conversation_id,
                user_id,
                {"existing_plan": plan.dict()}
            )
            
            logger.info(f"计划执行完成: {plan.name}, 成功: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"计划执行失败: {str(e)}")
            raise
    
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
            logger.info(f"开始规划并执行: {request[:100]}...")
            
            # 验证请求
            if not self._validate_request(request):
                raise ValueError("请求格式无效")
            
            # 规划并执行
            result = await self.planner_agent.plan_and_execute(
                request, conversation_id, user_id, context
            )
            
            logger.info(f"规划执行完成, 成功: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"规划执行失败: {str(e)}")
            raise
    
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
            logger.info(f"开始流式规划执行: {request[:100]}...")
            
            # 验证请求
            if not self._validate_request(request):
                yield {
                    "type": "error",
                    "message": "请求格式无效",
                    "timestamp": datetime.utcnow().isoformat()
                }
                return
            
            # 流式执行
            async for progress in self.planner_agent.plan_and_execute_stream(
                request, conversation_id, user_id, context
            ):
                yield progress
                
        except Exception as e:
            logger.error(f"流式规划执行失败: {str(e)}")
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
        return await self.planner_agent.get_execution_status(conversation_id)
    
    async def cancel_execution(self, conversation_id: int) -> bool:
        """
        取消执行
        
        参数:
            conversation_id: 会话ID
        
        返回:
            bool: 是否成功取消
        """
        return await self.planner_agent.cancel_execution(conversation_id)
    
    async def get_task_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Dict[str, Any]: 任务统计信息
        """
        return await self.planner_agent.get_task_statistics(conversation_id)
    
    async def get_optimization_suggestions(self, conversation_id: int) -> Dict[str, Any]:
        """
        获取优化建议
        
        参数:
            conversation_id: 会话ID
        
        返回:
            Dict[str, Any]: 优化建议
        """
        return await self.planner_agent.suggest_optimization(conversation_id)
    
    async def get_conversation_plans(self, conversation_id: int) -> List[Dict[str, Any]]:
        """
        获取会话的所有任务计划
        
        参数:
            conversation_id: 会话ID
        
        返回:
            List[Dict[str, Any]]: 任务计划列表
        """
        try:
            # 获取会话的所有任务
            tasks = self.task_dao.get_tasks_by_conversation_simple(conversation_id)
            
            # 按计划分组
            plans = {}
            for task in tasks:
                plan_name = task.metadata.get("plan_name", "未命名计划")
                if plan_name not in plans:
                    plans[plan_name] = {
                        "name": plan_name,
                        "tasks": [],
                        "created_at": task.created_at,
                        "status": "unknown"
                    }
                
                plans[plan_name]["tasks"].append({
                    "id": task.id,
                    "name": task.metadata.get("name", task.description),
                    "description": task.description,
                    "type": task.task_type,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at
                })
            
            # 计算计划状态
            for plan in plans.values():
                task_statuses = [task["status"] for task in plan["tasks"]]
                if all(status == "completed" for status in task_statuses):
                    plan["status"] = "completed"
                elif any(status == "failed" for status in task_statuses):
                    plan["status"] = "failed"
                elif any(status == "running" for status in task_statuses):
                    plan["status"] = "running"
                else:
                    plan["status"] = "pending"
            
            return list(plans.values())
            
        except Exception as e:
            logger.error(f"获取会话计划失败: {str(e)}")
            return []
    
    def _validate_request(self, request: str) -> bool:
        """
        验证请求格式
        
        参数:
            request: 用户请求
        
        返回:
            bool: 是否有效
        """
        if not request or not request.strip():
            return False
        
        # 检查请求长度
        if len(request) > 10000:
            return False
        
        # 检查是否包含恶意内容（简单检查）
        malicious_patterns = ["<script", "javascript:", "eval("]
        request_lower = request.lower()
        for pattern in malicious_patterns:
            if pattern in request_lower:
                return False
        
        return True
    
    def _validate_plan(self, plan: TaskPlan) -> bool:
        """
        验证任务计划
        
        参数:
            plan: 任务计划
        
        返回:
            bool: 是否有效
        """
        if not plan.name or not plan.description:
            return False
        
        if not plan.tasks:
            return False
        
        # 检查任务数量限制
        if len(plan.tasks) > 100:
            return False
        
        # 检查任务名称唯一性
        task_names = [task.name for task in plan.tasks]
        if len(task_names) != len(set(task_names)):
            return False
        
        return True
    
    async def estimate_execution_time(self, plan: TaskPlan) -> Dict[str, Any]:
        """
        估算执行时间
        
        参数:
            plan: 任务计划
        
        返回:
            Dict[str, Any]: 时间估算信息
        """
        try:
            total_estimated_time = 0
            task_estimates = []
            
            for task in plan.tasks:
                # 从元数据获取预估时间
                estimated_time = task.metadata.get("estimated_time", 0)
                if isinstance(estimated_time, str):
                    # 解析时间字符串（如 "5分钟", "1小时"）
                    estimated_time = self._parse_time_string(estimated_time)
                
                total_estimated_time += estimated_time
                task_estimates.append({
                    "name": task.name,
                    "estimated_time": estimated_time,
                    "type": task.task_type.value
                })
            
            return {
                "total_estimated_time": total_estimated_time,
                "total_estimated_time_formatted": self._format_time(total_estimated_time),
                "task_estimates": task_estimates,
                "parallel_opportunities": self._estimate_parallel_savings(plan)
            }
            
        except Exception as e:
            logger.error(f"估算执行时间失败: {str(e)}")
            return {
                "total_estimated_time": 0,
                "error": str(e)
            }
    
    def _parse_time_string(self, time_str: str) -> int:
        """
        解析时间字符串
        
        参数:
            time_str: 时间字符串
        
        返回:
            int: 时间（秒）
        """
        time_str = time_str.lower().strip()
        
        if "分钟" in time_str or "min" in time_str:
            number = int(''.join(filter(str.isdigit, time_str)))
            return number * 60
        elif "小时" in time_str or "hour" in time_str:
            number = int(''.join(filter(str.isdigit, time_str)))
            return number * 3600
        elif "秒" in time_str or "sec" in time_str:
            number = int(''.join(filter(str.isdigit, time_str)))
            return number
        else:
            # 默认按分钟处理
            number = int(''.join(filter(str.isdigit, time_str))) if any(c.isdigit() for c in time_str) else 5
            return number * 60
    
    def _format_time(self, seconds: int) -> str:
        """
        格式化时间
        
        参数:
            seconds: 时间（秒）
        
        返回:
            str: 格式化时间字符串
        """
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{hours}小时"
    
    def _estimate_parallel_savings(self, plan: TaskPlan) -> Dict[str, Any]:
        """
        估算并行执行节省的时间
        
        参数:
            plan: 任务计划
        
        返回:
            Dict[str, Any]: 并行节省信息
        """
        # 简单的启发式分析
        # 这里可以实现更复杂的并行分析算法
        
        independent_tasks = []
        for task in plan.tasks:
            if task.name not in plan.dependencies or not plan.dependencies[task.name]:
                independent_tasks.append(task)
        
        if len(independent_tasks) > 1:
            # 假设可以并行执行所有独立任务
            max_parallel_time = max(
                task.metadata.get("estimated_time", 300) 
                for task in independent_tasks
            )
            sequential_time = sum(
                task.metadata.get("estimated_time", 300) 
                for task in independent_tasks
            )
            
            return {
                "can_parallelize": True,
                "parallel_tasks": len(independent_tasks),
                "sequential_time": sequential_time,
                "parallel_time": max_parallel_time,
                "time_saved": sequential_time - max_parallel_time
            }
        
        return {
            "can_parallelize": False,
            "parallel_tasks": 0,
            "time_saved": 0
        }
