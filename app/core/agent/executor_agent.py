"""
执行Agent - 集成反思能力的任务执行器

功能：
- 执行具体任务
- 集成反思循环
- 管理重试机制
- 调用工具执行
- 支持流式输出
"""

import asyncio
from typing import List, Dict, Any, Optional, Union, Iterator, AsyncGenerator
from datetime import datetime

from app.core.agent.base import BaseAgent
from app.core.llm.base import BaseLLM
from app.tools.manager import ToolManager
from app.core.reflection.critic import Critic
from app.core.reflection.self_corrector import SelfCorrector
from app.core.reflection.schemas import (
    ExecutionContext, ReflectionResult, ReflectionConfig, CriticFeedback
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutorAgent(BaseAgent):
    """
    执行Agent
    
    功能：
    - 执行具体任务
    - 集成反思循环
    - 管理重试机制
    - 调用工具执行
    - 支持流式输出
    """
    
    def __init__(self, 
                 llm: BaseLLM, 
                 tool_manager: ToolManager,
                 critic: Optional[Critic] = None,
                 self_corrector: Optional[SelfCorrector] = None,
                 config: Optional[ReflectionConfig] = None):
        """
        初始化执行Agent
        
        参数:
            llm: LLM实例
            tool_manager: 工具管理器
            critic: 批评者（可选）
            self_corrector: 自我纠错器（可选）
            config: 反思配置（可选）
        """
        super().__init__(llm)
        self.tool_manager = tool_manager
        self.critic = critic or Critic(llm)
        self.self_corrector = self_corrector or SelfCorrector(llm)
        self.config = config or ReflectionConfig()
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # 执行历史记录
        self.execution_history: List[Dict[str, Any]] = []
        
        self.logger.info("ExecutorAgent 初始化成功")

    def run(self,
            messages: List[Dict[str, str]],
            stream: bool = False,
            **kwargs) -> Union[str, Iterator[str]]:
        """
        运行 Agent（实现抽象方法）
        
        参数:
            messages: 消息列表
            stream: 是否流式输出
            **kwargs: 其他参数
            
        返回:
            Union[str, Iterator[str]]: 回复内容或流式迭代器
        """
        if not messages:
            return "没有收到消息"
        
        last_message = messages[-1]
        request = last_message.get("content", "")
        
        # 创建执行上下文
        context = ExecutionContext(
            task_description=request,
            expected_goal=kwargs.get("expected_goal", "完成用户请求"),
            constraints=kwargs.get("constraints", []),
            context_info=kwargs.get("context_info", {})
        )
        
        # 同步调用异步方法
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if stream:
            # 流式执行
            return self._stream_execute(context, **kwargs)
        else:
            # 非流式执行
            result = loop.run_until_complete(
                self.execute_with_reflection(context, **kwargs)
            )
            return result.get("output", "执行失败")

    async def execute_with_reflection(self,
                                    context: ExecutionContext,
                                    enable_reflection: bool = True,
                                    max_retries: Optional[int] = None,
                                    **kwargs) -> Dict[str, Any]:
        """
        带反思的任务执行
        
        参数:
            context: 执行上下文
            enable_reflection: 是否启用反思
            max_retries: 最大重试次数
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 执行结果
        """
        start_time = datetime.utcnow()
        retry_count = 0
        max_retries = max_retries or self.config.max_retries
        
        self.logger.info(f"开始执行任务: {context.task_description[:50]}...")
        
        try:
            while retry_count <= max_retries:
                # 执行任务
                execution_result = await self._execute_single(context, retry_count, **kwargs)
                
                if not enable_reflection:
                    # 不启用反思，直接返回结果
                    return {
                        "output": execution_result["output"],
                        "success": True,
                        "retry_count": retry_count,
                        "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                        "reflection_enabled": False
                    }
                
                # 评估输出质量
                feedback = await self.critic.evaluate(execution_result["output"], context)
                
                # 记录执行历史
                self.execution_history.append({
                    "retry_count": retry_count,
                    "output": execution_result["output"],
                    "feedback": feedback,
                    "timestamp": datetime.utcnow()
                })
                
                # 判断是否需要重试
                if not self.self_corrector.should_retry(feedback, retry_count, self.config):
                    self.logger.info(f"任务执行完成，重试次数: {retry_count}, 最终评分: {feedback.overall_score:.2f}")
                    return {
                        "output": execution_result["output"],
                        "success": True,
                        "retry_count": retry_count,
                        "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                        "final_feedback": feedback,
                        "reflection_enabled": True
                    }
                
                # 生成纠错建议
                suggestions = await self.self_corrector.generate_corrections(
                    feedback, context, execution_result["output"], retry_count
                )
                
                # 创建重试计划
                retry_plan = self.self_corrector.create_retry_plan(
                    suggestions, context, retry_count
                )
                
                self.logger.info(f"第{retry_count + 1}次重试，评分: {feedback.overall_score:.2f}, 建议数: {len(suggestions)}")
                
                # 更新上下文以包含纠错信息
                context = self._update_context_with_corrections(context, suggestions, retry_plan)
                retry_count += 1
            
            # 达到最大重试次数
            self.logger.warning(f"达到最大重试次数 {max_retries}，停止重试")
            return {
                "output": execution_result["output"],
                "success": False,
                "retry_count": retry_count,
                "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                "final_feedback": feedback,
                "max_retries_reached": True,
                "reflection_enabled": True
            }
            
        except Exception as e:
            self.logger.error(f"执行任务失败: {e}")
            return {
                "output": f"执行失败: {str(e)}",
                "success": False,
                "retry_count": retry_count,
                "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                "error": str(e),
                "reflection_enabled": enable_reflection
            }

    async def _execute_single(self,
                            context: ExecutionContext,
                            retry_count: int,
                            **kwargs) -> Dict[str, Any]:
        """
        单次任务执行
        
        参数:
            context: 执行上下文
            retry_count: 重试次数
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 执行结果
        """
        try:
            # 构建执行提示词
            prompt = self._build_execution_prompt(context, retry_count, **kwargs)
            
            # 调用LLM执行任务
            output = await self.llm.achat(prompt)
            
            # 记录执行信息
            execution_info = {
                "prompt": prompt,
                "output": output,
                "retry_count": retry_count,
                "timestamp": datetime.utcnow()
            }
            
            return {
                "output": output,
                "execution_info": execution_info,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"单次执行失败: {e}")
            return {
                "output": f"执行失败: {str(e)}",
                "execution_info": {
                    "error": str(e),
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow()
                },
                "success": False
            }

    def _build_execution_prompt(self,
                              context: ExecutionContext,
                              retry_count: int,
                              **kwargs) -> str:
        """
        构建执行提示词
        
        参数:
            context: 执行上下文
            retry_count: 重试次数
            **kwargs: 其他参数
            
        返回:
            str: 执行提示词
        """
        base_prompt = f"""请完成以下任务：

任务描述: {context.task_description}
期望目标: {context.expected_goal}"""

        # 添加约束条件
        if context.constraints:
            base_prompt += f"\n约束条件: {', '.join(context.constraints)}"

        # 添加上下文信息
        if context.context_info:
            base_prompt += f"\n上下文信息: {context.context_info}"

        # 如果是重试，添加重试提示
        if retry_count > 0:
            base_prompt += f"\n\n这是第{retry_count + 1}次尝试，请特别注意之前可能存在的问题。"
            
            # 添加之前的反馈信息
            if self.execution_history:
                last_feedback = self.execution_history[-1].get("feedback")
                if last_feedback:
                    base_prompt += f"\n之前的反馈: {last_feedback.feedback_text}"

        # 添加执行指导
        base_prompt += "\n\n请提供清晰、准确、完整的回答。"

        return base_prompt

    def _update_context_with_corrections(self,
                                       context: ExecutionContext,
                                       suggestions: List,
                                       retry_plan: Dict[str, Any]) -> ExecutionContext:
        """
        使用纠错信息更新上下文
        
        参数:
            context: 原始上下文
            suggestions: 纠错建议
            retry_plan: 重试计划
            
        返回:
            ExecutionContext: 更新后的上下文
        """
        # 创建新的上下文信息
        new_context_info = context.context_info.copy()
        new_context_info.update({
            "correction_suggestions": [s.dict() for s in suggestions],
            "retry_plan": retry_plan,
            "retry_count": retry_plan.get("retry_count", 0)
        })
        
        # 更新约束条件
        new_constraints = context.constraints.copy()
        if "focus_areas" in retry_plan:
            new_constraints.extend([f"重点关注: {area}" for area in retry_plan["focus_areas"]])
        
        return ExecutionContext(
            task_description=context.task_description,
            expected_goal=context.expected_goal,
            constraints=new_constraints,
            context_info=new_context_info
        )

    def _stream_execute(self, context: ExecutionContext, **kwargs) -> Iterator[str]:
        """
        流式执行（简化实现）
        
        参数:
            context: 执行上下文
            **kwargs: 其他参数
            
        返回:
            Iterator[str]: 流式输出迭代器
        """
        # 简化实现，实际应该支持真正的流式输出
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            self.execute_with_reflection(context, **kwargs)
        )
        
        output = result.get("output", "")
        
        # 模拟流式输出
        words = output.split()
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield " " + word

    async def execute_with_tools(self,
                               context: ExecutionContext,
                               tool_names: Optional[List[str]] = None,
                               **kwargs) -> Dict[str, Any]:
        """
        使用工具执行任务
        
        参数:
            context: 执行上下文
            tool_names: 要使用的工具名称列表
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 执行结果
        """
        try:
            # 获取可用工具
            available_tools = self.tool_manager.get_all_tools()
            
            if tool_names:
                # 过滤指定工具
                available_tools = [tool for tool in available_tools if tool.name in tool_names]
            
            # 构建包含工具信息的提示词
            tool_info = "\n".join([f"- {tool.name}: {tool.description}" for tool in available_tools])
            
            enhanced_context = ExecutionContext(
                task_description=context.task_description,
                expected_goal=context.expected_goal,
                constraints=context.constraints + [f"可用工具: {tool_info}"],
                context_info=context.context_info
            )
            
            # 执行任务
            return await self.execute_with_reflection(enhanced_context, **kwargs)
            
        except Exception as e:
            self.logger.error(f"工具执行失败: {e}")
            return {
                "output": f"工具执行失败: {str(e)}",
                "success": False,
                "error": str(e)
            }

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        获取执行历史
        
        返回:
            List[Dict[str, Any]]: 执行历史列表
        """
        return self.execution_history.copy()

    def clear_execution_history(self):
        """清空执行历史"""
        self.execution_history.clear()

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        
        返回:
            Dict[str, Any]: 性能统计信息
        """
        if not self.execution_history:
            return {"total_executions": 0}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for h in self.execution_history if h.get("feedback", {}).get("overall_score", 0) >= 0.8)
        
        avg_score = sum(h.get("feedback", {}).get("overall_score", 0) for h in self.execution_history) / total_executions
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_score": avg_score,
            "last_execution": self.execution_history[-1] if self.execution_history else None
        }
