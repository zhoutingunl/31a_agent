"""
重要性评分器

该模块负责计算记忆内容的重要性分数，基于多个维度：
- 信息新颖性（是否是新知识）
- 情感强度（用户情绪反应）
- 任务相关性（与当前任务的关联）
- 引用频率（被访问的次数）
- 时间因素（最近的信息权重高）
"""

import logging
import math
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.core.llm.base import BaseLLM
from app.models.memory import MemoryStore

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """
    重要性评分器
    
    基于多维度计算记忆的重要性分数（0-1范围）
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化重要性评分器
        
        Args:
            llm: 大语言模型实例，用于智能评分
        """
        self.llm = llm
        self.weights = {
            "novelty": 0.25,      # 新颖性权重
            "emotional": 0.20,    # 情感强度权重
            "relevance": 0.25,    # 任务相关性权重
            "frequency": 0.15,    # 引用频率权重
            "recency": 0.15       # 时间因素权重
        }
    
    async def score_memory(
        self,
        memory: MemoryStore,
        context: Optional[Dict] = None
    ) -> float:
        """
        计算记忆的重要性分数
        
        Args:
            memory: 记忆对象
            context: 上下文信息，如当前任务、用户状态等
            
        Returns:
            float: 重要性分数（0-1）
        """
        try:
            # 计算各个维度的分数
            novelty_score = await self._calculate_novelty_score(memory, context)
            emotional_score = await self._calculate_emotional_score(memory, context)
            relevance_score = await self._calculate_relevance_score(memory, context)
            frequency_score = self._calculate_frequency_score(memory)
            recency_score = self._calculate_recency_score(memory)
            
            # 加权计算总分
            total_score = (
                novelty_score * self.weights["novelty"] +
                emotional_score * self.weights["emotional"] +
                relevance_score * self.weights["relevance"] +
                frequency_score * self.weights["frequency"] +
                recency_score * self.weights["recency"]
            )
            
            # 确保分数在0-1范围内
            total_score = max(0.0, min(1.0, total_score))
            
            logger.debug(f"记忆重要性评分: {total_score:.3f} (新颖性:{novelty_score:.3f}, "
                        f"情感:{emotional_score:.3f}, 相关性:{relevance_score:.3f}, "
                        f"频率:{frequency_score:.3f}, 时间:{recency_score:.3f})")
            
            return total_score
            
        except Exception as e:
            logger.error(f"重要性评分失败: {e}")
            # 返回默认分数
            return 0.5
    
    def calculate_decay_score(
        self,
        original_score: float,
        created_at: datetime,
        access_count: int
    ) -> float:
        """
        计算时间衰减后的分数
        
        Args:
            original_score: 原始重要性分数
            created_at: 创建时间
            access_count: 访问次数
            
        Returns:
            float: 衰减后的分数
        """
        try:
            # 计算时间衰减因子
            time_decay = self._calculate_time_decay(created_at)
            
            # 计算访问强化因子
            access_boost = self._calculate_access_boost(access_count)
            
            # 应用衰减和强化
            decayed_score = original_score * time_decay * access_boost
            
            # 确保分数在0-1范围内
            return max(0.0, min(1.0, decayed_score))
            
        except Exception as e:
            logger.error(f"衰减分数计算失败: {e}")
            return original_score
    
    async def _calculate_novelty_score(
        self,
        memory: MemoryStore,
        context: Optional[Dict] = None
    ) -> float:
        """
        计算新颖性分数
        
        Args:
            memory: 记忆对象
            context: 上下文信息
            
        Returns:
            float: 新颖性分数（0-1）
        """
        try:
            # 构建新颖性评估提示
            prompt = f"""
请评估以下记忆内容的新颖性（是否包含新知识或新信息）：

记忆内容：{memory.content}

评估标准：
- 1.0: 包含全新的知识、概念或信息
- 0.8: 包含部分新信息或新角度
- 0.6: 包含一些新细节或补充信息
- 0.4: 主要是已知信息的重新组织
- 0.2: 完全是已知信息
- 0.0: 重复或冗余信息

请只返回一个0-1之间的数字，保留2位小数。
"""
            
            response = await self.llm.achat(prompt)
            score = self._parse_score_response(response)
            
            return score
            
        except Exception as e:
            logger.error(f"新颖性评分失败: {e}")
            return 0.5
    
    async def _calculate_emotional_score(
        self,
        memory: MemoryStore,
        context: Optional[Dict] = None
    ) -> float:
        """
        计算情感强度分数
        
        Args:
            memory: 记忆对象
            context: 上下文信息
            
        Returns:
            float: 情感强度分数（0-1）
        """
        try:
            # 构建情感强度评估提示
            prompt = f"""
请评估以下记忆内容的情感强度（用户情绪反应的强烈程度）：

记忆内容：{memory.content}

评估标准：
- 1.0: 包含强烈的情感表达（愤怒、兴奋、悲伤、恐惧等）
- 0.8: 包含明显的情感倾向（喜欢、不喜欢、担心等）
- 0.6: 包含轻微的情感色彩（满意、不满意等）
- 0.4: 包含中性但带有个人色彩的信息
- 0.2: 主要是客观信息，情感色彩很淡
- 0.0: 完全客观、无情感色彩的信息

请只返回一个0-1之间的数字，保留2位小数。
"""
            
            response = await self.llm.achat(prompt)
            score = self._parse_score_response(response)
            
            return score
            
        except Exception as e:
            logger.error(f"情感强度评分失败: {e}")
            return 0.3
    
    async def _calculate_relevance_score(
        self,
        memory: MemoryStore,
        context: Optional[Dict] = None
    ) -> float:
        """
        计算任务相关性分数
        
        Args:
            memory: 记忆对象
            context: 上下文信息
            
        Returns:
            float: 任务相关性分数（0-1）
        """
        try:
            if not context or "current_task" not in context:
                return 0.5
            
            current_task = context["current_task"]
            
            # 构建相关性评估提示
            prompt = f"""
请评估以下记忆内容与当前任务的相关性：

当前任务：{current_task}
记忆内容：{memory.content}

评估标准：
- 1.0: 直接相关，对完成任务至关重要
- 0.8: 高度相关，对完成任务很有帮助
- 0.6: 中等相关，对完成任务有一定帮助
- 0.4: 低度相关，可能对完成任务有帮助
- 0.2: 几乎不相关，对完成任务帮助很小
- 0.0: 完全不相关，对完成任务没有帮助

请只返回一个0-1之间的数字，保留2位小数。
"""
            
            response = await self.llm.achat(prompt)
            score = self._parse_score_response(response)
            
            return score
            
        except Exception as e:
            logger.error(f"任务相关性评分失败: {e}")
            return 0.5
    
    def _calculate_frequency_score(self, memory: MemoryStore) -> float:
        """
        计算引用频率分数
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 引用频率分数（0-1）
        """
        try:
            # 从元数据中获取访问次数
            metadata = memory.memory_metadata or {}
            access_count = metadata.get("access_count", 0)
            
            # 使用对数函数计算频率分数，避免过高
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
            logger.error(f"引用频率评分失败: {e}")
            return 0.3
    
    def _calculate_recency_score(self, memory: MemoryStore) -> float:
        """
        计算时间因素分数
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 时间因素分数（0-1）
        """
        try:
            now = datetime.utcnow()
            created_at = memory.created_at
            
            # 计算时间差（小时）
            time_diff = (now - created_at).total_seconds() / 3600
            
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
            logger.error(f"时间因素评分失败: {e}")
            return 0.5
    
    def _calculate_time_decay(self, created_at: datetime) -> float:
        """
        计算时间衰减因子
        
        Args:
            created_at: 创建时间
            
        Returns:
            float: 时间衰减因子（0-1）
        """
        try:
            now = datetime.utcnow()
            days_ago = (now - created_at).days
            
            # 使用指数衰减：衰减率 = e^(-λt)
            # λ = 0.01 表示每天衰减1%
            decay_rate = 0.01
            decay_factor = math.exp(-decay_rate * days_ago)
            
            return max(0.1, decay_factor)  # 最低保留10%
            
        except Exception as e:
            logger.error(f"时间衰减计算失败: {e}")
            return 0.5
    
    def _calculate_access_boost(self, access_count: int) -> float:
        """
        计算访问强化因子
        
        Args:
            access_count: 访问次数
            
        Returns:
            float: 访问强化因子（1.0-2.0）
        """
        try:
            if access_count == 0:
                return 1.0
            elif access_count == 1:
                return 1.1
            elif access_count <= 5:
                return 1.2
            elif access_count <= 10:
                return 1.3
            else:
                # 使用对数函数，避免过高
                return min(2.0, 1.3 + math.log(access_count - 10) * 0.1)
                
        except Exception as e:
            logger.error(f"访问强化计算失败: {e}")
            return 1.0
    
    def _parse_score_response(self, response: str) -> float:
        """
        解析评分响应
        
        Args:
            response: LLM响应
            
        Returns:
            float: 解析出的分数
        """
        try:
            # 提取数字
            import re
            numbers = re.findall(r'0\.\d{1,2}|1\.0{1,2}', response)
            if numbers:
                score = float(numbers[0])
                return max(0.0, min(1.0, score))
            
            # 如果没有找到标准格式，尝试其他格式
            numbers = re.findall(r'\d+\.?\d*', response)
            if numbers:
                score = float(numbers[0])
                if score > 1:
                    score = score / 10  # 假设是10分制
                return max(0.0, min(1.0, score))
            
            logger.warning(f"无法解析评分响应: {response}")
            return 0.5
            
        except Exception as e:
            logger.error(f"评分响应解析失败: {e}")
            return 0.5
