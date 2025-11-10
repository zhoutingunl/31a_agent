"""
状态机

管理Agent执行过程中的状态转换
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .schemas import ExecutionState, StateTransition
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StateMachine:
    """
    状态机
    
    功能：
    - 管理执行状态
    - 验证状态转换
    - 记录转换历史
    """
    
    # 定义有效的状态转换
    VALID_TRANSITIONS = {
        ExecutionState.IDLE: [ExecutionState.ROUTING],
        ExecutionState.ROUTING: [ExecutionState.EXECUTING, ExecutionState.ERROR],
        ExecutionState.EXECUTING: [ExecutionState.COMPLETED, ExecutionState.ERROR],
        ExecutionState.ERROR: [ExecutionState.RECOVERING, ExecutionState.COMPLETED],
        ExecutionState.RECOVERING: [ExecutionState.EXECUTING, ExecutionState.ERROR, ExecutionState.COMPLETED],
        ExecutionState.COMPLETED: [ExecutionState.IDLE]
    }
    
    def __init__(self):
        """
        初始化状态机
        """
        self.current_state = ExecutionState.IDLE
        self.history: List[StateTransition] = []
        logger.debug("状态机初始化完成")
    
    def transition(
        self,
        new_state: ExecutionState,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        执行状态转换
        
        Args:
            new_state: 目标状态
            context: 转换上下文
            
        Returns:
            bool: 是否转换成功
        """
        # 验证转换是否有效
        if not self.can_transition(new_state):
            logger.warning(
                f"无效的状态转换: {self.current_state} -> {new_state}"
            )
            return False
        
        # 记录转换
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.now(),
            context=context or {}
        )
        
        self.history.append(transition)
        
        # 执行转换
        old_state = self.current_state
        self.current_state = new_state
        
        logger.debug(
            f"状态转换: {old_state} -> {new_state}",
            context=context
        )
        
        return True
    
    def can_transition(self, target_state: ExecutionState) -> bool:
        """
        检查是否可以转换到目标状态
        
        Args:
            target_state: 目标状态
            
        Returns:
            bool: 是否可以转换
        """
        valid_targets = self.VALID_TRANSITIONS.get(self.current_state, [])
        return target_state in valid_targets
    
    def reset(self):
        """
        重置状态机到初始状态
        """
        self.current_state = ExecutionState.IDLE
        self.history.clear()
        logger.debug("状态机已重置")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取状态转换历史
        
        Returns:
            List[Dict[str, Any]]: 转换历史列表
        """
        return [
            {
                "from_state": t.from_state.value if hasattr(t.from_state, 'value') else str(t.from_state),
                "to_state": t.to_state.value if hasattr(t.to_state, 'value') else str(t.to_state),
                "timestamp": t.timestamp.isoformat(),
                "context": t.context
            }
            for t in self.history
        ]
    
    def get_current_state(self) -> ExecutionState:
        """
        获取当前状态
        
        Returns:
            ExecutionState: 当前状态
        """
        return self.current_state
    
    def is_completed(self) -> bool:
        """
        检查是否已完成
        
        Returns:
            bool: 是否完成
        """
        return self.current_state == ExecutionState.COMPLETED
    
    def is_error(self) -> bool:
        """
        检查是否处于错误状态
        
        Returns:
            bool: 是否错误
        """
        return self.current_state == ExecutionState.ERROR
    
    def get_execution_duration(self) -> float:
        """
        获取执行时长
        
        Returns:
            float: 执行时长（秒）
        """
        if not self.history:
            return 0.0
        
        first_transition = self.history[0]
        last_transition = self.history[-1]
        
        duration = (last_transition.timestamp - first_transition.timestamp).total_seconds()
        return duration
