"""
遗忘机制

该模块实现了基于Ebbinghaus遗忘曲线的记忆遗忘机制：
- 时间衰减：随时间降低重要性
- 访问强化：被访问的记忆重要性提升
- 主动遗忘：低价值记忆自动删除或归档
"""

import logging
import math
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta

from app.models.memory import MemoryStore

logger = logging.getLogger(__name__)


class ForgettingMechanism:
    """
    遗忘机制
    
    基于Ebbinghaus遗忘曲线实现记忆的时间衰减和主动遗忘
    """
    
    def __init__(self):
        """
        初始化遗忘机制
        """
        # 遗忘曲线参数
        self.decay_rate = 0.01  # 每日衰减率
        self.retention_threshold = 0.3  # 保留阈值
        self.forget_threshold = 0.1  # 遗忘阈值
        
        # 访问强化参数
        self.access_boost_factor = 0.1  # 每次访问的强化因子
        self.max_access_boost = 0.5  # 最大访问强化
        
        # 时间权重参数
        self.recency_weight = 0.3  # 近期记忆权重
        self.frequency_weight = 0.4  # 访问频率权重
        self.importance_weight = 0.3  # 原始重要性权重
    
    def calculate_retention_score(
        self,
        memory: MemoryStore,
        current_time: datetime
    ) -> float:
        """
        计算记忆的保留分数
        
        Args:
            memory: 记忆对象
            current_time: 当前时间
            
        Returns:
            float: 保留分数（0-1）
        """
        try:
            # 计算时间衰减
            time_decay = self._calculate_time_decay(memory.created_at, current_time)
            
            # 计算访问强化
            access_boost = self._calculate_access_boost(memory)
            
            # 计算综合保留分数
            retention_score = time_decay * access_boost
            
            # 确保分数在合理范围内
            retention_score = max(0.0, min(1.0, retention_score))
            
            logger.debug(f"记忆保留分数: {retention_score:.3f} "
                        f"(时间衰减:{time_decay:.3f}, 访问强化:{access_boost:.3f})")
            
            return retention_score
            
        except Exception as e:
            logger.error(f"保留分数计算失败: {e}")
            return 0.5
    
    async def apply_forgetting(
        self,
        memories: List[MemoryStore],
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        应用遗忘机制
        
        Args:
            memories: 记忆列表
            threshold: 遗忘阈值
            
        Returns:
            Dict[str, Any]: 遗忘结果统计
        """
        if not memories:
            return {
                "total_memories": 0,
                "forgotten_count": 0,
                "retained_count": 0,
                "forgotten_memories": [],
                "retained_memories": []
            }
        
        try:
            current_time = datetime.utcnow()
            forgotten_memories = []
            retained_memories = []
            
            for memory in memories:
                # 计算保留分数
                retention_score = self.calculate_retention_score(memory, current_time)
                
                # 判断是否应该遗忘
                if self.should_forget(memory, retention_score, threshold):
                    forgotten_memories.append(memory)
                else:
                    retained_memories.append(memory)
            
            result = {
                "total_memories": len(memories),
                "forgotten_count": len(forgotten_memories),
                "retained_count": len(retained_memories),
                "forgotten_memories": forgotten_memories,
                "retained_memories": retained_memories,
                "forgetting_rate": len(forgotten_memories) / len(memories) if memories else 0
            }
            
            logger.info(f"遗忘机制应用完成: {len(forgotten_memories)}/{len(memories)} 条记忆被遗忘")
            return result
            
        except Exception as e:
            logger.error(f"遗忘机制应用失败: {e}")
            return {
                "total_memories": len(memories),
                "forgotten_count": 0,
                "retained_count": len(memories),
                "forgotten_memories": [],
                "retained_memories": memories,
                "error": str(e)
            }
    
    def should_forget(
        self,
        memory: MemoryStore,
        retention_score: float,
        threshold: float = 0.3
    ) -> bool:
        """
        判断记忆是否应该被遗忘
        
        Args:
            memory: 记忆对象
            retention_score: 保留分数
            threshold: 遗忘阈值
            
        Returns:
            bool: 是否应该遗忘
        """
        try:
            # 基础判断：保留分数低于阈值
            if retention_score < threshold:
                return True
            
            # 特殊记忆类型保护
            if memory.memory_type == "long_term" and memory.importance_score and memory.importance_score > 0.8:
                return False
            
            # 最近访问的记忆保护
            metadata = memory.memory_metadata or {}
            last_access = metadata.get("last_access_time")
            if last_access:
                try:
                    last_access_time = datetime.fromisoformat(last_access)
                    if (datetime.utcnow() - last_access_time).days < 7:
                        return False
                except ValueError:
                    pass
            
            # 高访问频率的记忆保护
            access_count = metadata.get("access_count", 0)
            if access_count > 10:
                return False
            
            return retention_score < threshold
            
        except Exception as e:
            logger.error(f"遗忘判断失败: {e}")
            return False
    
    def update_access_info(
        self,
        memory: MemoryStore,
        access_time: datetime = None
    ) -> MemoryStore:
        """
        更新记忆的访问信息
        
        Args:
            memory: 记忆对象
            access_time: 访问时间
            
        Returns:
            MemoryStore: 更新后的记忆对象
        """
        try:
            if access_time is None:
                access_time = datetime.utcnow()
            
            # 获取或创建元数据
            metadata = memory.memory_metadata or {}
            
            # 更新访问信息
            metadata["last_access_time"] = access_time.isoformat()
            metadata["access_count"] = metadata.get("access_count", 0) + 1
            
            # 计算访问强化后的重要性分数
            original_importance = memory.importance_score or 0
            access_boost = self._calculate_access_boost(memory)
            boosted_importance = min(1.0, original_importance + (access_boost - 1.0) * self.access_boost_factor)
            
            # 更新记忆对象
            memory.memory_metadata = metadata
            memory.importance_score = boosted_importance
            
            logger.debug(f"记忆访问信息已更新: 访问次数={metadata['access_count']}, "
                        f"重要性分数={boosted_importance:.3f}")
            
            return memory
            
        except Exception as e:
            logger.error(f"访问信息更新失败: {e}")
            return memory
    
    def _calculate_time_decay(
        self,
        created_at: datetime,
        current_time: datetime
    ) -> float:
        """
        计算时间衰减因子
        
        Args:
            created_at: 创建时间
            current_time: 当前时间
            
        Returns:
            float: 时间衰减因子（0-1）
        """
        try:
            # 计算时间差（天）
            time_diff = (current_time - created_at).total_seconds() / (24 * 3600)
            
            # 使用指数衰减函数：R = e^(-λt)
            # 其中 λ 是衰减率，t 是时间
            decay_factor = math.exp(-self.decay_rate * time_diff)
            
            # 确保衰减因子在合理范围内
            return max(0.1, decay_factor)  # 最低保留10%
            
        except Exception as e:
            logger.error(f"时间衰减计算失败: {e}")
            return 0.5
    
    def _calculate_access_boost(self, memory: MemoryStore) -> float:
        """
        计算访问强化因子
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 访问强化因子（1.0-2.0）
        """
        try:
            metadata = memory.memory_metadata or {}
            access_count = metadata.get("access_count", 0)
            
            if access_count == 0:
                return 1.0
            
            # 使用对数函数计算强化因子，避免过高
            boost_factor = 1.0 + min(
                self.max_access_boost,
                math.log(access_count + 1) * self.access_boost_factor
            )
            
            return boost_factor
            
        except Exception as e:
            logger.error(f"访问强化计算失败: {e}")
            return 1.0
    
    def get_memory_priority(
        self,
        memory: MemoryStore,
        current_time: datetime = None
    ) -> float:
        """
        计算记忆的优先级分数
        
        Args:
            memory: 记忆对象
            current_time: 当前时间
            
        Returns:
            float: 优先级分数（0-1）
        """
        try:
            if current_time is None:
                current_time = datetime.utcnow()
            
            # 计算各个维度的分数
            recency_score = self._calculate_recency_score(memory.created_at, current_time)
            frequency_score = self._calculate_frequency_score(memory)
            importance_score = memory.importance_score or 0
            
            # 加权计算优先级
            priority = (
                recency_score * self.recency_weight +
                frequency_score * self.frequency_weight +
                importance_score * self.importance_weight
            )
            
            return max(0.0, min(1.0, priority))
            
        except Exception as e:
            logger.error(f"优先级计算失败: {e}")
            return 0.5
    
    def _calculate_recency_score(
        self,
        created_at: datetime,
        current_time: datetime
    ) -> float:
        """
        计算近期性分数
        
        Args:
            created_at: 创建时间
            current_time: 当前时间
            
        Returns:
            float: 近期性分数（0-1）
        """
        try:
            # 计算时间差（小时）
            time_diff = (current_time - created_at).total_seconds() / 3600
            
            # 使用指数衰减函数
            if time_diff <= 1:  # 1小时内
                return 1.0
            elif time_diff <= 24:  # 1天内
                return 0.9
            elif time_diff <= 168:  # 1周内
                return 0.7
            elif time_diff <= 720:  # 1月内
                return 0.5
            elif time_diff <= 2160:  # 3月内
                return 0.3
            else:  # 3月以上
                return 0.1
                
        except Exception as e:
            logger.error(f"近期性分数计算失败: {e}")
            return 0.5
    
    def _calculate_frequency_score(self, memory: MemoryStore) -> float:
        """
        计算访问频率分数
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 访问频率分数（0-1）
        """
        try:
            metadata = memory.memory_metadata or {}
            access_count = metadata.get("access_count", 0)
            
            # 使用对数函数计算频率分数
            if access_count == 0:
                return 0.1
            elif access_count == 1:
                return 0.3
            elif access_count <= 3:
                return 0.5
            elif access_count <= 10:
                return 0.7
            else:
                return min(1.0, 0.8 + math.log(access_count - 10) * 0.1)
                
        except Exception as e:
            logger.error(f"访问频率分数计算失败: {e}")
            return 0.3
    
    def get_forgetting_schedule(
        self,
        memories: List[MemoryStore],
        days_ahead: int = 30
    ) -> List[Tuple[MemoryStore, datetime, float]]:
        """
        获取记忆的遗忘时间表
        
        Args:
            memories: 记忆列表
            days_ahead: 预测天数
            
        Returns:
            List[Tuple[MemoryStore, datetime, float]]: 遗忘时间表
        """
        try:
            schedule = []
            current_time = datetime.utcnow()
            
            for memory in memories:
                # 计算当前保留分数
                current_retention = self.calculate_retention_score(memory, current_time)
                
                # 预测遗忘时间
                forget_time = self._predict_forget_time(
                    memory, current_time, days_ahead
                )
                
                if forget_time:
                    schedule.append((memory, forget_time, current_retention))
            
            # 按遗忘时间排序
            schedule.sort(key=lambda x: x[1])
            
            return schedule
            
        except Exception as e:
            logger.error(f"遗忘时间表生成失败: {e}")
            return []
    
    def _predict_forget_time(
        self,
        memory: MemoryStore,
        current_time: datetime,
        days_ahead: int
    ) -> datetime:
        """
        预测记忆的遗忘时间
        
        Args:
            memory: 记忆对象
            current_time: 当前时间
            days_ahead: 预测天数
            
        Returns:
            datetime: 预测的遗忘时间
        """
        try:
            # 计算当前保留分数
            current_retention = self.calculate_retention_score(memory, current_time)
            
            # 如果已经低于遗忘阈值，立即遗忘
            if current_retention < self.forget_threshold:
                return current_time
            
            # 计算达到遗忘阈值所需的时间
            # 使用指数衰减公式反推：t = -ln(R) / λ
            target_retention = self.forget_threshold
            time_to_forget = -math.log(target_retention) / self.decay_rate
            
            # 转换为小时
            hours_to_forget = time_to_forget * 24
            
            # 计算遗忘时间
            forget_time = current_time + timedelta(hours=hours_to_forget)
            
            # 限制在预测范围内
            max_time = current_time + timedelta(days=days_ahead)
            if forget_time > max_time:
                return None
            
            return forget_time
            
        except Exception as e:
            logger.error(f"遗忘时间预测失败: {e}")
            return None
