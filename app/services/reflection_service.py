"""
反思服务层 - 已废弃

⚠️ 注意：此服务已废弃，反思功能已完全集成到ExecutorAgent中。
请直接使用ExecutorAgent的execute_with_reflection方法。

功能：
- 封装反思业务逻辑
- 管理反思流程
- 记录反思历史
- 提供统一的反思接口
"""

import warnings
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.core.reflection.critic import Critic
from app.core.reflection.self_corrector import SelfCorrector
from app.core.reflection.schemas import (
    ExecutionContext, ReflectionResult, ReflectionConfig, CriticFeedback,
    ReflectionHistory, CorrectionSuggestion
)
from app.core.agent.executor_agent import ExecutorAgent
from app.tools.manager import ToolManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReflectionService:
    """
    反思服务 - 已废弃
    
    ⚠️ 注意：此服务已废弃，反思功能已完全集成到ExecutorAgent中。
    请直接使用ExecutorAgent的execute_with_reflection方法。
    
    功能：
    - 封装反思业务逻辑
    - 管理反思流程
    - 记录反思历史
    - 提供统一的反思接口
    """
    
    def __init__(self, db: Session, llm: BaseLLM, tool_manager: Optional[ToolManager] = None):
        """
        初始化反思服务 - 已废弃
        
        ⚠️ 注意：此服务已废弃，请直接使用ExecutorAgent的execute_with_reflection方法。
        
        参数:
            db: 数据库会话
            llm: LLM实例
            tool_manager: 工具管理器（可选）
        """
        # 发出废弃警告
        warnings.warn(
            "ReflectionService已废弃，请直接使用ExecutorAgent的execute_with_reflection方法",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.db = db
        self.llm = llm
        self.tool_manager = tool_manager or ToolManager()
        
        # 初始化反思组件
        self.critic = Critic(llm)
        self.self_corrector = SelfCorrector(llm)
        self.executor_agent = ExecutorAgent(
            llm=llm,
            tool_manager=self.tool_manager,
            critic=self.critic,
            self_corrector=self.self_corrector
        )
        
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # 反思历史记录（内存中，实际应该存储到数据库）
        self.reflection_history: List[ReflectionHistory] = []
        
        self.logger.warning("ReflectionService 已废弃，请使用ExecutorAgent")

    async def execute_with_reflection(self,
                                    task: str,
                                    conversation_id: int,
                                    user_id: int,
                                    max_retries: Optional[int] = None,
                                    config: Optional[ReflectionConfig] = None,
                                    context_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行任务并启用反思机制
        
        参数:
            task: 任务描述
            conversation_id: 会话ID
            user_id: 用户ID
            max_retries: 最大重试次数
            config: 反思配置
            context_info: 上下文信息
            
        返回:
            Dict[str, Any]: 执行结果
        """
        try:
            self.logger.info(f"开始反思执行任务: {task[:50]}...")
            
            # 创建执行上下文
            context = ExecutionContext(
                task_description=task,
                expected_goal="完成用户请求",
                constraints=[],
                context_info=context_info or {}
            )
            
            # 设置配置
            if config:
                self.executor_agent.config = config
            
            # 执行任务
            result = await self.executor_agent.execute_with_reflection(
                context=context,
                enable_reflection=True,
                max_retries=max_retries
            )
            
            # 记录反思历史
            if result.get("reflection_enabled", False):
                self._record_reflection_history(
                    task_id=conversation_id,  # 使用conversation_id作为task_id
                    result=result,
                    context=context
                )
            
            self.logger.info(f"反思执行完成，成功: {result.get('success', False)}")
            return result
            
        except Exception as e:
            self.logger.error(f"反思执行失败: {e}")
            return {
                "output": f"反思执行失败: {str(e)}",
                "success": False,
                "error": str(e),
                "reflection_enabled": True
            }

    async def execute_with_reflection_stream(self,
                                           task: str,
                                           conversation_id: int,
                                           user_id: int,
                                           max_retries: Optional[int] = None,
                                           config: Optional[ReflectionConfig] = None,
                                           context_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行任务并启用反思机制
        
        参数:
            task: 任务描述
            conversation_id: 会话ID
            user_id: 用户ID
            max_retries: 最大重试次数
            config: 反思配置
            context_info: 上下文信息
            
        返回:
            AsyncGenerator[Dict[str, Any], None]: 流式执行结果
        """
        try:
            self.logger.info(f"开始流式反思执行任务: {task[:50]}...")
            
            # 创建执行上下文
            context = ExecutionContext(
                task_description=task,
                expected_goal="完成用户请求",
                constraints=[],
                context_info=context_info or {}
            )
            
            # 设置配置
            if config:
                self.executor_agent.config = config
            
            # 发送开始信号
            yield {
                "type": "start",
                "message": "开始执行任务...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            retry_count = 0
            max_retries = max_retries or self.executor_agent.config.max_retries
            
            while retry_count <= max_retries:
                # 发送重试信息
                if retry_count > 0:
                    yield {
                        "type": "retry",
                        "message": f"第{retry_count}次重试...",
                        "retry_count": retry_count,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                # 执行单次任务
                execution_result = await self.executor_agent._execute_single(context, retry_count)
                
                # 发送执行结果
                yield {
                    "type": "execution",
                    "message": "任务执行完成，正在评估...",
                    "output": execution_result["output"],
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 评估输出质量
                feedback = await self.critic.evaluate(execution_result["output"], context)
                
                # 发送评估结果
                yield {
                    "type": "evaluation",
                    "message": f"评估完成，评分: {feedback.overall_score:.2f}",
                    "feedback": feedback.dict(),
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 判断是否需要重试
                if not self.self_corrector.should_retry(feedback, retry_count, self.executor_agent.config):
                    # 不需要重试，发送完成信号
                    yield {
                        "type": "complete",
                        "message": "任务执行完成",
                        "output": execution_result["output"],
                        "success": True,
                        "retry_count": retry_count,
                        "final_feedback": feedback.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    break
                
                # 生成纠错建议
                suggestions = await self.self_corrector.generate_corrections(
                    feedback, context, execution_result["output"], retry_count
                )
                
                # 发送纠错建议
                yield {
                    "type": "correction",
                    "message": f"生成{len(suggestions)}条改进建议",
                    "suggestions": [s.dict() for s in suggestions],
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 更新上下文
                retry_plan = self.self_corrector.create_retry_plan(suggestions, context, retry_count)
                context = self.executor_agent._update_context_with_corrections(context, suggestions, retry_plan)
                
                retry_count += 1
            
            # 如果达到最大重试次数
            if retry_count > max_retries:
                yield {
                    "type": "max_retries",
                    "message": f"达到最大重试次数 {max_retries}",
                    "output": execution_result["output"],
                    "success": False,
                    "retry_count": retry_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"流式反思执行失败: {e}")
            yield {
                "type": "error",
                "message": f"执行失败: {str(e)}",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_reflection_history(self, 
                             task_id: Optional[int] = None,
                             limit: int = 100) -> List[ReflectionHistory]:
        """
        获取反思历史
        
        参数:
            task_id: 任务ID（可选）
            limit: 限制数量
            
        返回:
            List[ReflectionHistory]: 反思历史列表
        """
        history = self.reflection_history
        
        if task_id is not None:
            history = [h for h in history if h.task_id == task_id]
        
        return history[-limit:] if limit > 0 else history

    def analyze_improvement(self, 
                          task_id: int) -> Dict[str, Any]:
        """
        分析改进效果
        
        参数:
            task_id: 任务ID
            
        返回:
            Dict[str, Any]: 改进分析结果
        """
        # 获取该任务的历史记录
        task_history = [h for h in self.reflection_history if h.task_id == task_id]
        
        if len(task_history) < 2:
            return {
                "task_id": task_id,
                "analysis": "数据不足，无法分析改进效果",
                "iterations": len(task_history)
            }
        
        # 按迭代次数排序
        task_history.sort(key=lambda x: x.iteration)
        
        # 分析改进趋势
        initial_feedback = task_history[0].feedback
        final_feedback = task_history[-1].feedback
        
        improvement_analysis = self.self_corrector.analyze_correction_effectiveness(
            initial_feedback, final_feedback
        )
        
        return {
            "task_id": task_id,
            "total_iterations": len(task_history),
            "initial_score": initial_feedback.overall_score,
            "final_score": final_feedback.overall_score,
            "overall_improvement": improvement_analysis["overall_improvement"],
            "dimension_improvements": improvement_analysis["dimension_improvements"],
            "resolved_issues": improvement_analysis["resolved_issues"],
            "remaining_issues": improvement_analysis["remaining_issues"],
            "effectiveness_score": improvement_analysis["effectiveness_score"],
            "analysis": "改进效果分析完成"
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计
        
        返回:
            Dict[str, Any]: 性能统计信息
        """
        # 获取执行Agent的性能统计
        agent_stats = self.executor_agent.get_performance_stats()
        
        # 计算反思相关统计
        total_reflections = len(self.reflection_history)
        successful_reflections = sum(
            1 for h in self.reflection_history 
            if h.feedback.overall_score >= 0.8
        )
        
        avg_improvement = 0
        if total_reflections > 0:
            improvements = []
            for h in self.reflection_history:
                if h.improvement_score is not None:
                    improvements.append(h.improvement_score)
            
            if improvements:
                avg_improvement = sum(improvements) / len(improvements)
        
        return {
            "agent_stats": agent_stats,
            "reflection_stats": {
                "total_reflections": total_reflections,
                "successful_reflections": successful_reflections,
                "success_rate": successful_reflections / total_reflections if total_reflections > 0 else 0,
                "average_improvement": avg_improvement
            }
        }

    def _record_reflection_history(self,
                                 task_id: int,
                                 result: Dict[str, Any],
                                 context: ExecutionContext):
        """
        记录反思历史
        
        参数:
            task_id: 任务ID
            result: 执行结果
            context: 执行上下文
        """
        try:
            # 获取执行历史
            execution_history = self.executor_agent.get_execution_history()
            
            for i, execution in enumerate(execution_history):
                history = ReflectionHistory(
                    task_id=task_id,
                    iteration=i + 1,
                    output=execution.get("output", ""),
                    feedback=execution.get("feedback"),
                    suggestions=[],  # 这里可以添加建议信息
                    improvement_score=None,  # 可以计算改进分数
                    created_at=execution.get("timestamp", datetime.utcnow())
                )
                
                self.reflection_history.append(history)
            
            self.logger.info(f"记录反思历史完成，任务ID: {task_id}, 迭代次数: {len(execution_history)}")
            
        except Exception as e:
            self.logger.error(f"记录反思历史失败: {e}")

    async def quick_evaluate(self, 
                           output: str, 
                           task_description: str) -> bool:
        """
        快速评估是否需要纠错
        
        参数:
            output: 输出内容
            task_description: 任务描述
            
        返回:
            bool: 是否需要纠错
        """
        try:
            context = ExecutionContext(
                task_description=task_description,
                expected_goal="完成用户请求",
                constraints=[],
                context_info={}
            )
            
            return await self.critic.quick_evaluate(output, context)
            
        except Exception as e:
            self.logger.error(f"快速评估失败: {e}")
            return True  # 默认需要纠错

    def clear_history(self):
        """清空反思历史"""
        self.reflection_history.clear()
        self.executor_agent.clear_execution_history()
        self.logger.info("反思历史已清空")

    def get_config(self) -> Dict[str, Any]:
        """
        获取反思配置信息
        
        返回:
            Dict[str, Any]: 反思配置信息
        """
        return {
            "max_retries": self.executor_agent.config.max_retries,
            "quality_threshold": self.executor_agent.config.quality_threshold,
            "enable_reflection": True,
            "critic_config": {
                "evaluation_criteria": self.critic.evaluation_criteria,
                "quality_threshold": self.critic.quality_threshold
            },
            "self_corrector_config": {
                "max_suggestions": self.self_corrector.max_suggestions,
                "improvement_threshold": self.self_corrector.improvement_threshold
            },
            "executor_config": {
                "enable_tools": self.tool_manager is not None,
                "available_tools": [tool.name for tool in self.tool_manager.get_all_tools()] if self.tool_manager else []
            }
        }

    def export_reflection_data(self, 
                             task_id: Optional[int] = None) -> Dict[str, Any]:
        """
        导出反思数据
        
        参数:
            task_id: 任务ID（可选）
            
        返回:
            Dict[str, Any]: 导出的反思数据
        """
        history = self.get_reflection_history(task_id)
        
        return {
            "export_time": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "total_records": len(history),
            "reflection_history": [h.dict() for h in history],
            "performance_stats": self.get_performance_stats()
        }
