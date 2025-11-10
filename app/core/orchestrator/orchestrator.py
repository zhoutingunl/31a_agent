"""
Agent编排器

统一协调各个Agent和服务，提供智能路由和状态管理
作为唯一的Agent工厂，统一创建和管理所有Agent实例
"""

import logging
import time
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.core.agent.tool_agent import ToolAgent
from app.core.agent.planner_agent import PlannerAgent
from app.core.agent.executor_agent import ExecutorAgent
from app.core.roles.role_config import RoleConfig
from app.tools.manager import ToolManager
from app.dao.task_dao import TaskDAO
from app.services.memory_service import MemoryService
from app.services.knowledge_service import KnowledgeService
from .router import TaskRouter
from .state_machine import StateMachine
from .error_handler import ErrorHandler
from .schemas import (
    ExecutionMode,
    ExecutionState,
    OrchestratorRequest,
    OrchestratorResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """
    Agent编排器 - 统一的Agent工厂和管理器
    
    功能：
    - 统一创建和管理所有Agent实例（单例模式）
    - 应用角色工具权限过滤
    - 智能任务路由
    - 状态管理
    - 异常处理与恢复
    - 记忆系统深度集成
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        role_config: RoleConfig,
        memory_service: Optional[MemoryService] = None,
        knowledge_service: Optional[KnowledgeService] = None
    ):
        """
        初始化编排器
        
        Args:
            db: 数据库会话
            llm: LLM实例
            role_config: 角色配置
            memory_service: 记忆服务（可选）
            knowledge_service: 知识服务（可选）
        """
        self.db = db
        self.llm = llm
        self.role_config = role_config
        self.memory_service = memory_service
        self.knowledge_service = knowledge_service
        
        # 创建角色专属的工具管理器（应用权限过滤）
        self.tool_manager = self._create_role_tool_manager()
        
        # 初始化所有Agent实例（单例模式）
        self._initialize_agents()
        
        # 初始化路由器、状态机和错误处理器
        self.router = TaskRouter(llm)
        self.state_machine = StateMachine()
        self.error_handler = ErrorHandler()
        
        logger.info(
            f"编排器初始化完成: 角色={role_config.name}",
            memory_enabled=memory_service is not None,
            knowledge_enabled=knowledge_service is not None,
            tool_count=len(self.tool_manager.get_all_tools())
        )
    
    def _create_role_tool_manager(self) -> ToolManager:
        """
        创建角色专属的工具管理器，应用权限过滤
        
        Returns:
            ToolManager: 角色专属的工具管理器
        """
        from app.tools.manager import tool_manager
        
        # 获取所有工具
        all_tools = tool_manager.get_all_tools()
        
        # 根据角色权限过滤工具
        filtered_tools = []
        for tool in all_tools:
            tool_name = getattr(tool, 'name', str(tool))
            if self.role_config.is_tool_allowed(tool_name):
                filtered_tools.append(tool)
        
        # 创建角色专属工具管理器
        role_tool_manager = ToolManager()
        role_tool_manager.tools = {tool.name: tool for tool in filtered_tools}
        
        logger.info(
            f"角色 {self.role_config.name} 工具过滤: {len(all_tools)} -> {len(filtered_tools)}"
        )
        
        return role_tool_manager
    
    def _initialize_agents(self):
        """
        初始化所有Agent实例（单例模式）
        """
        # 创建TaskDAO
        task_dao = TaskDAO(self.db)
        
        # 初始化各个Agent
        self.tool_agent = ToolAgent(self.llm, self.tool_manager)
        self.planner_agent = PlannerAgent(task_dao, self.tool_manager, self.llm)
        self.executor_agent = ExecutorAgent(self.llm, self.tool_manager)
        
        logger.debug("所有Agent实例初始化完成")
    
    async def execute(
        self,
        request: OrchestratorRequest
    ) -> OrchestratorResponse:
        """
        执行用户请求（集成记忆系统）
        
        Args:
            request: 编排器请求
            
        Returns:
            OrchestratorResponse: 执行响应
        """
        start_time = time.time()
        
        try:
            # 重置状态机
            self.state_machine.reset()
            
            # 1. 记忆检索阶段
            memories = await self._retrieve_memories(request)
            
            # 2. 路由阶段
            self.state_machine.transition(
                ExecutionState.ROUTING,
                {"request": request.content[:100], "memories_count": len(memories)}
            )
            
            # 决定执行模式
            if request.mode:
                # 使用指定模式
                mode = request.mode
                logger.info(f"使用指定执行模式: {mode}")
            else:
                # 智能路由
                route_decision = await self.router.route(
                    request=request.content,
                    context=request.context
                )
                mode = route_decision.mode
                logger.info(
                    f"路由决策完成: {mode}",
                    confidence=route_decision.confidence,
                    reason=route_decision.reason
                )
            
            # 3. 执行阶段
            self.state_machine.transition(
                ExecutionState.EXECUTING,
                {"mode": mode}
            )
            
            # 构建增强的上下文（包含记忆）
            enhanced_context = self._build_enhanced_context(request, memories)
            
            result = await self._execute_with_mode(
                mode=mode,
                request=request,
                enhanced_context=enhanced_context
            )
            
            # 4. 记忆存储阶段
            await self._store_memory(request, result, mode)
            
            # 5. 完成阶段
            self.state_machine.transition(
                ExecutionState.COMPLETED,
                {"success": True}
            )
            
            execution_time = time.time() - start_time
            
            return OrchestratorResponse(
                success=True,
                content=result,
                mode=mode,
                execution_time=execution_time,
                state_history=self.state_machine.get_history(),
                metadata={
                    "conversation_id": request.conversation_id,
                    "user_id": request.user_id,
                    "memories_retrieved": len(memories),
                    "memory_stored": True
                }
            )
            
        except Exception as e:
            # 错误处理
            self.state_machine.transition(
                ExecutionState.ERROR,
                {"error": str(e)}
            )
            
            # 尝试恢复
            recovery = await self.error_handler.handle_error(e, request.context)
            
            if recovery.get("can_recover"):
                # 可以恢复，尝试降级执行
                logger.info(f"尝试恢复: {recovery.get('strategy')}")
                
                self.state_machine.transition(
                    ExecutionState.RECOVERING,
                    {"recovery_strategy": recovery.get("strategy")}
                )
                
                try:
                    # 使用降级模式重试
                    downgrade_mode = recovery.get("downgrade_to", ExecutionMode.SIMPLE)
                    result = await self._execute_with_mode(
                        mode=downgrade_mode,
                        request=request
                    )
                    
                    self.state_machine.transition(
                        ExecutionState.COMPLETED,
                        {"success": True, "recovered": True}
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return OrchestratorResponse(
                        success=True,
                        content=result,
                        mode=downgrade_mode,
                        execution_time=execution_time,
                        state_history=self.state_machine.get_history(),
                        metadata={
                            "recovered": True,
                            "original_error": str(e),
                            "recovery_strategy": recovery.get("strategy")
                        }
                    )
                    
                except Exception as retry_error:
                    logger.error(f"恢复失败: {retry_error}")
                    # 恢复失败，返回错误
                    pass
            
            # 无法恢复或恢复失败
            execution_time = time.time() - start_time
            
            return OrchestratorResponse(
                success=False,
                content="",
                mode=request.mode or ExecutionMode.SIMPLE,
                execution_time=execution_time,
                state_history=self.state_machine.get_history(),
                metadata={},
                error=str(e)
            )
    
    async def _execute_with_mode(
        self,
        mode: ExecutionMode,
        request: OrchestratorRequest,
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用指定模式执行任务
        
        Args:
            mode: 执行模式
            request: 请求对象
            enhanced_context: 增强的上下文（包含记忆）
            
        Returns:
            str: 执行结果
        """
        if mode == ExecutionMode.SIMPLE:
            return await self._execute_simple(request, enhanced_context)
        elif mode == ExecutionMode.PLANNING:
            return await self._execute_planning(request, enhanced_context)
        elif mode == ExecutionMode.REFLECTION:
            return await self._execute_reflection(request, enhanced_context)
        else:
            raise ValueError(f"未知的执行模式: {mode}")
    
    async def _retrieve_memories(self, request: OrchestratorRequest) -> List[Dict[str, Any]]:
        """
        检索相关记忆
        
        Args:
            request: 编排器请求
            
        Returns:
            List[Dict[str, Any]]: 相关记忆列表
        """
        if not self.memory_service:
            return []
        
        try:
            # 检索短期和长期记忆
            memories = await self.memory_service.retrieve_memories(
                query=request.content,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                limit=10
            )
            
            logger.debug(f"检索到 {len(memories)} 条相关记忆")
            return memories
            
        except Exception as e:
            logger.warning(f"记忆检索失败: {e}")
            return []
    
    def _build_enhanced_context(
        self, 
        request: OrchestratorRequest, 
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建增强的上下文（包含记忆）
        
        Args:
            request: 编排器请求
            memories: 相关记忆
            
        Returns:
            Dict[str, Any]: 增强的上下文
        """
        enhanced_context = request.context.copy() if request.context else {}
        
        # 添加记忆信息
        if memories:
            enhanced_context["memories"] = memories
            enhanced_context["memory_summary"] = self._summarize_memories(memories)
        
        # 添加角色信息
        enhanced_context["role"] = self.role_config.name
        enhanced_context["system_prompt"] = self.role_config.system_prompt
        
        return enhanced_context
    
    def _summarize_memories(self, memories: List[Dict[str, Any]]) -> str:
        """
        总结记忆信息
        
        Args:
            memories: 记忆列表
            
        Returns:
            str: 记忆总结
        """
        if not memories:
            return ""
        
        summary_parts = []
        for memory in memories[:5]:  # 只总结前5条记忆
            content = memory.get("content", "")
            memory_type = memory.get("type", "unknown")
            summary_parts.append(f"[{memory_type}] {content[:100]}...")
        
        return "\n".join(summary_parts)
    
    async def _store_memory(
        self, 
        request: OrchestratorRequest, 
        result: str, 
        mode: ExecutionMode
    ):
        """
        存储执行记忆
        
        Args:
            request: 编排器请求
            result: 执行结果
            mode: 执行模式
        """
        if not self.memory_service:
            return
        
        try:
            # 构建记忆内容
            memory_content = f"用户: {request.content}\n助手: {result}"
            
            # 根据执行模式决定记忆类型
            if mode == ExecutionMode.REFLECTION:
                memory_type = "reflection"
                importance = 0.8  # 反思模式的结果通常更重要
            elif mode == ExecutionMode.PLANNING:
                memory_type = "planning"
                importance = 0.7
            else:
                memory_type = "conversation"
                importance = 0.5
            
            # 存储记忆
            await self.memory_service.store_memory(
                content=memory_content,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                memory_type=memory_type,
                importance=importance,
                metadata={
                    "mode": mode.value,
                    "role": self.role_config.name
                }
            )
            
            logger.debug(f"记忆存储成功: {memory_type}")
            
        except Exception as e:
            logger.warning(f"记忆存储失败: {e}")
    
    async def _execute_simple(
        self,
        request: OrchestratorRequest,
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        简单对话模式执行
        
        Args:
            request: 请求对象
            enhanced_context: 增强的上下文（包含记忆）
            
        Returns:
            str: 执行结果
        """
        logger.debug("使用简单对话模式执行")
        
        # 构建消息（包含记忆上下文）
        system_prompt = self.role_config.system_prompt
        if enhanced_context and enhanced_context.get("memory_summary"):
            system_prompt += f"\n\n相关记忆:\n{enhanced_context['memory_summary']}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.content}
        ]
        
        # 调用ToolAgent
        result = self.tool_agent.run(messages=messages, stream=False)
        
        return result
    
    async def _execute_planning(
        self,
        request: OrchestratorRequest,
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        规划模式执行
        
        Args:
            request: 请求对象
            enhanced_context: 增强的上下文（包含记忆）
            
        Returns:
            str: 执行结果
        """
        logger.debug("使用规划模式执行")
        
        # 使用增强的上下文
        context = enhanced_context if enhanced_context else request.context
        
        # 调用PlannerAgent
        execution_result = await self.planner_agent.plan_and_execute(
            request=request.content,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            context=context
        )
        
        if execution_result.success:
            return execution_result.message
        else:
            raise Exception(f"规划执行失败: {execution_result.message}")
    
    async def _execute_reflection(
        self,
        request: OrchestratorRequest,
        enhanced_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        反思模式执行 - 使用ExecutorAgent的反思能力
        
        Args:
            request: 请求对象
            enhanced_context: 增强的上下文（包含记忆）
            
        Returns:
            str: 执行结果
        """
        logger.debug("使用反思模式执行")
        
        # 构建执行上下文（包含记忆信息）
        from app.core.reflection.schemas import ExecutionContext
        
        context_info = enhanced_context if enhanced_context else request.context
        
        execution_context = ExecutionContext(
            task_description=request.content,
            expected_goal="完成用户请求",
            constraints=[],
            context_info=context_info
        )
        
        # 调用ExecutorAgent的反思执行方法
        reflection_result = await self.executor_agent.execute_with_reflection(
            context=execution_context,
            enable_reflection=True,
            max_retries=3  # 默认最大重试3次
        )
        
        if reflection_result.get("success", False):
            return reflection_result.get("output", "")
        else:
            error_msg = reflection_result.get("error", "未知错误")
            raise Exception(f"反思执行失败: {error_msg}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取编排器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "state_machine": {
                "current_state": self.state_machine.get_current_state().value,
                "transition_count": len(self.state_machine.history)
            },
            "router": self.router.get_cache_stats(),
            "error_handler": self.error_handler.get_error_statistics()
        }
