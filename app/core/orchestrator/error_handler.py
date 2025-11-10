"""
异常处理器

处理执行过程中的各种异常，提供恢复策略
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .schemas import ExecutionMode
from app.utils.logger import get_logger
from app.utils.exceptions import AgentException

logger = get_logger(__name__)


class ErrorHandler:
    """
    异常处理器
    
    功能：
    - 分类异常类型
    - 提供恢复策略
    - 记录异常历史
    """
    
    def __init__(self):
        """
        初始化异常处理器
        """
        self.error_history = []
        self.max_retry_count = 3
        self.retry_counts = {}
        
        logger.info("异常处理器初始化完成")
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            context: 执行上下文
            
        Returns:
            Dict[str, Any]: 恢复策略
        """
        try:
            # 记录异常
            error_record = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now(),
                "context": context
            }
            self.error_history.append(error_record)
            
            logger.error(
                f"捕获异常: {type(error).__name__}",
                error=str(error),
                context=context
            )
            
            # 根据异常类型选择恢复策略
            if self._is_tool_error(error):
                return await self._recover_from_tool_error(error, context)
            elif self._is_llm_error(error):
                return await self._recover_from_llm_error(error, context)
            elif self._is_timeout_error(error):
                return await self._recover_from_timeout(error, context)
            elif self._is_validation_error(error):
                return await self._recover_from_validation_error(error, context)
            else:
                return await self._recover_from_unknown_error(error, context)
                
        except Exception as e:
            logger.error(f"异常处理器自身出错: {e}")
            return {
                "can_recover": False,
                "strategy": "abort",
                "reason": f"异常处理器失败: {str(e)}"
            }
    
    def _is_tool_error(self, error: Exception) -> bool:
        """检查是否是工具调用错误"""
        error_type = type(error).__name__
        return "Tool" in error_type or "tool" in str(error).lower()
    
    def _is_llm_error(self, error: Exception) -> bool:
        """检查是否是LLM错误"""
        error_type = type(error).__name__
        return "LLM" in error_type or "llm" in str(error).lower() or "model" in str(error).lower()
    
    def _is_timeout_error(self, error: Exception) -> bool:
        """检查是否是超时错误"""
        error_type = type(error).__name__
        return "Timeout" in error_type or "timeout" in str(error).lower()
    
    def _is_validation_error(self, error: Exception) -> bool:
        """检查是否是验证错误"""
        error_type = type(error).__name__
        return "Validation" in error_type or "validation" in str(error).lower()
    
    async def _recover_from_tool_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从工具调用错误中恢复
        
        策略：
        1. 重试工具调用（最多3次）
        2. 降级到不使用该工具
        3. 切换到备用工具
        """
        task_id = context.get("task_id", "unknown")
        retry_key = f"tool_{task_id}"
        
        retry_count = self.retry_counts.get(retry_key, 0)
        
        if retry_count < self.max_retry_count:
            # 重试
            self.retry_counts[retry_key] = retry_count + 1
            return {
                "can_recover": True,
                "strategy": "retry",
                "reason": f"工具调用失败，重试第 {retry_count + 1} 次",
                "retry_count": retry_count + 1
            }
        else:
            # 超过重试次数，降级
            return {
                "can_recover": True,
                "strategy": "downgrade",
                "reason": "工具调用失败次数过多，降级到简单模式",
                "downgrade_to": ExecutionMode.SIMPLE
            }
    
    async def _recover_from_llm_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从LLM错误中恢复
        
        策略：
        1. 重试LLM调用
        2. 简化提示词
        3. 切换到备用模型
        """
        task_id = context.get("task_id", "unknown")
        retry_key = f"llm_{task_id}"
        
        retry_count = self.retry_counts.get(retry_key, 0)
        
        if retry_count < 2:  # LLM错误只重试2次
            self.retry_counts[retry_key] = retry_count + 1
            return {
                "can_recover": True,
                "strategy": "retry",
                "reason": f"LLM调用失败，重试第 {retry_count + 1} 次",
                "retry_count": retry_count + 1
            }
        else:
            return {
                "can_recover": True,
                "strategy": "simplify",
                "reason": "LLM调用失败，简化请求",
                "downgrade_to": ExecutionMode.SIMPLE
            }
    
    async def _recover_from_timeout(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从超时错误中恢复
        
        策略：
        1. 延长超时时间重试
        2. 分解任务
        3. 降级到更快的模式
        """
        return {
            "can_recover": True,
            "strategy": "downgrade",
            "reason": "执行超时，降级到简单模式",
            "downgrade_to": ExecutionMode.SIMPLE
        }
    
    async def _recover_from_validation_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从验证错误中恢复
        
        策略：
        1. 修正输入格式
        2. 使用默认值
        """
        return {
            "can_recover": False,
            "strategy": "abort",
            "reason": f"数据验证失败: {str(error)}"
        }
    
    async def _recover_from_unknown_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从未知错误中恢复
        
        策略：
        1. 降级到简单模式
        2. 如果仍失败则中止
        """
        retry_key = f"unknown_{context.get('task_id', 'unknown')}"
        retry_count = self.retry_counts.get(retry_key, 0)
        
        if retry_count < 1:
            self.retry_counts[retry_key] = retry_count + 1
            return {
                "can_recover": True,
                "strategy": "downgrade",
                "reason": f"未知错误，降级到简单模式: {str(error)}",
                "downgrade_to": ExecutionMode.SIMPLE
            }
        else:
            return {
                "can_recover": False,
                "strategy": "abort",
                "reason": f"无法恢复: {str(error)}"
            }
    
    def reset_retry_counts(self):
        """
        重置重试计数
        """
        self.retry_counts.clear()
        logger.debug("重试计数已重置")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计
        
        Returns:
            Dict[str, Any]: 错误统计信息
        """
        if not self.error_history:
            return {
                "total_errors": 0,
                "error_types": {},
                "recent_errors": []
            }
        
        # 统计错误类型
        error_types = {}
        for record in self.error_history:
            error_type = record["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 最近的错误
        recent_errors = self.error_history[-10:]
        
        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "recent_errors": [
                {
                    "type": e["error_type"],
                    "message": e["error_message"],
                    "timestamp": e["timestamp"].isoformat()
                }
                for e in recent_errors
            ]
        }
