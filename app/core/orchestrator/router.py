"""
任务路由器

智能分析用户请求，决定使用哪种执行模式
"""

import logging
import re
from typing import Dict, Any, Optional

from app.core.llm.base import BaseLLM
from .schemas import ExecutionMode, RouteDecision
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRouter:
    """
    任务路由器
    
    功能：
    - 分析请求特征
    - 智能路由决策
    - 缓存路由结果
    """
    
    # 简单查询关键词
    SIMPLE_KEYWORDS = [
        "什么", "怎么", "如何", "查询", "查看", "获取", "显示", "告诉我",
        "hello", "hi", "你好", "谢谢", "再见", "解释", "说明", "介绍"
    ]
    
    # 规划任务关键词
    PLANNING_KEYWORDS = [
        "规划", "计划", "分析", "设计", "重构", "优化", "改进",
        "帮我", "步骤", "流程", "方案", "策略", "架构", "系统",
        "多步骤", "复杂", "分解", "任务", "项目"
    ]
    
    # 反思任务关键词
    REFLECTION_KEYWORDS = [
        "生成", "创建", "编写", "实现", "开发", "构建", "制作",
        "代码", "SQL", "测试", "文档", "脚本", "程序", "算法",
        "高质量", "完美", "最佳", "优化", "改进", "修复", "调试"
    ]
    
    # 任务复杂度指标
    COMPLEXITY_INDICATORS = {
        "high": ["系统", "架构", "框架", "平台", "完整", "全面", "详细"],
        "medium": ["分析", "设计", "规划", "方案", "策略", "流程"],
        "low": ["简单", "快速", "基础", "基本", "入门"]
    }
    
    def __init__(self, llm: Optional[BaseLLM] = None):
        """
        初始化任务路由器
        
        Args:
            llm: LLM实例（用于复杂度判断）
        """
        self.llm = llm
        self.route_cache: Dict[str, RouteDecision] = {}
        self.cache_size = 100
        
        logger.info("任务路由器初始化完成")
    
    async def route(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RouteDecision:
        """
        智能路由决策
        
        Args:
            request: 用户请求
            context: 上下文信息
            
        Returns:
            RouteDecision: 路由决策结果
        """
        try:
            # 1. 检查缓存
            cache_key = self._get_cache_key(request)
            if cache_key in self.route_cache:
                logger.debug(f"使用缓存的路由决策: {cache_key}")
                return self.route_cache[cache_key]
            
            # 2. 基于规则的快速判断
            rule_based_mode = self._rule_based_route(request)
            if rule_based_mode:
                decision = RouteDecision(
                    mode=rule_based_mode,
                    confidence=0.8,
                    reason="基于规则匹配",
                    analysis={"method": "rule_based"}
                )
                self._cache_decision(cache_key, decision)
                return decision
            
            # 3. 基于LLM的复杂度分析
            if self.llm:
                llm_mode = await self._llm_based_route(request, context)
                if llm_mode:
                    decision = RouteDecision(
                        mode=llm_mode,
                        confidence=0.9,
                        reason="基于LLM分析",
                        analysis={"method": "llm_based"}
                    )
                    self._cache_decision(cache_key, decision)
                    return decision
            
            # 4. 默认使用简单模式
            decision = RouteDecision(
                mode=ExecutionMode.SIMPLE,
                confidence=0.6,
                reason="默认简单模式",
                analysis={"method": "default"}
            )
            self._cache_decision(cache_key, decision)
            return decision
            
        except Exception as e:
            logger.error(f"路由决策失败: {e}")
            # 降级到简单模式
            return RouteDecision(
                mode=ExecutionMode.SIMPLE,
                confidence=0.5,
                reason=f"路由失败，降级到简单模式: {str(e)}",
                analysis={"method": "fallback", "error": str(e)}
            )
    
    def _rule_based_route(self, request: str) -> Optional[ExecutionMode]:
        """
        基于规则的路由判断（增强版）
        
        Args:
            request: 用户请求
            
        Returns:
            Optional[ExecutionMode]: 执行模式，如果无法判断则返回None
        """
        request_lower = request.lower()
        request_length = len(request.strip())
        
        # 1. 检查任务复杂度指标
        complexity_score = self._calculate_complexity_score(request_lower)
        
        # 2. 检查关键词匹配
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in request_lower)
        planning_count = sum(1 for kw in self.PLANNING_KEYWORDS if kw in request_lower)
        reflection_count = sum(1 for kw in self.REFLECTION_KEYWORDS if kw in request_lower)
        
        # 3. 检查特殊模式指示词
        if any(word in request_lower for word in ["代码", "sql", "脚本", "程序", "算法"]):
            return ExecutionMode.REFLECTION
        
        if any(word in request_lower for word in ["步骤", "流程", "方案", "策略", "架构"]):
            return ExecutionMode.PLANNING
        
        # 4. 基于请求长度的快速判断
        if request_length < 15:
            return ExecutionMode.SIMPLE
        elif request_length > 200:
            # 长请求通常是复杂任务
            if complexity_score >= 0.6:
                return ExecutionMode.REFLECTION
            else:
                return ExecutionMode.PLANNING
        
        # 5. 基于关键词计数的综合判断
        total_keywords = simple_count + planning_count + reflection_count
        if total_keywords == 0:
            # 没有匹配关键词，基于复杂度判断
            if complexity_score >= 0.7:
                return ExecutionMode.REFLECTION
            elif complexity_score >= 0.4:
                return ExecutionMode.PLANNING
            else:
                return ExecutionMode.SIMPLE
        
        # 6. 加权评分
        simple_score = simple_count * 1.0
        planning_score = planning_count * 1.2
        reflection_score = reflection_count * 1.5
        
        # 结合复杂度调整
        if complexity_score >= 0.6:
            reflection_score *= 1.5
            planning_score *= 1.2
        elif complexity_score >= 0.3:
            planning_score *= 1.3
        
        # 选择最高分的模式
        scores = {
            ExecutionMode.SIMPLE: simple_score,
            ExecutionMode.PLANNING: planning_score,
            ExecutionMode.REFLECTION: reflection_score
        }
        
        best_mode = max(scores, key=scores.get)
        best_score = scores[best_mode]
        
        # 如果最高分太低，返回None让LLM判断
        if best_score < 1.0:
            return None
        
        return best_mode
    
    def _calculate_complexity_score(self, request_lower: str) -> float:
        """
        计算任务复杂度评分
        
        Args:
            request_lower: 小写的用户请求
            
        Returns:
            float: 复杂度评分 (0.0-1.0)
        """
        score = 0.0
        
        # 检查复杂度指标
        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            count = sum(1 for indicator in indicators if indicator in request_lower)
            if level == "high":
                score += count * 0.3
            elif level == "medium":
                score += count * 0.2
            else:  # low
                score += count * 0.1
        
        # 检查特殊复杂度指标
        if any(word in request_lower for word in ["完整", "全面", "详细", "系统", "架构"]):
            score += 0.3
        
        if any(word in request_lower for word in ["多", "几个", "多个", "各种", "不同"]):
            score += 0.2
        
        # 检查技术术语
        tech_terms = ["api", "数据库", "算法", "框架", "库", "接口", "协议"]
        tech_count = sum(1 for term in tech_terms if term in request_lower)
        score += tech_count * 0.1
        
        return min(score, 1.0)  # 限制在0-1之间
    
    async def _llm_based_route(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ExecutionMode]:
        """
        基于LLM的路由判断（增强版）
        
        Args:
            request: 用户请求
            context: 上下文信息
            
        Returns:
            Optional[ExecutionMode]: 执行模式
        """
        try:
            # 构建增强的提示词
            context_info = ""
            if context:
                if context.get("memories"):
                    context_info += f"\n相关记忆数量: {len(context['memories'])}"
                if context.get("role"):
                    context_info += f"\n角色类型: {context['role']}"
            
            prompt = f"""
请分析以下用户请求的复杂度，并选择最合适的执行模式：

用户请求: {request}
{context_info}

执行模式详细说明:
1. simple - 简单对话模式：
   - 适用于：简单问答、信息查询、单步骤任务、基础对话
   - 特点：快速响应，直接调用工具或LLM
   - 示例：查询天气、解释概念、简单计算

2. planning - 规划模式：
   - 适用于：多步骤任务、需要分解的复杂任务、项目管理
   - 特点：任务分解、工作流执行、进度跟踪
   - 示例：制定学习计划、分析问题、设计流程

3. reflection - 反思模式：
   - 适用于：代码生成、复杂分析、高质量输出、需要验证的任务
   - 特点：自我批评、质量检查、迭代改进
   - 示例：编写代码、生成文档、复杂算法实现

请根据请求的复杂度、任务类型和输出质量要求，选择最合适的模式。
只返回模式名称（simple、planning 或 reflection），不要包含其他内容。
"""
            
            response = await self.llm.generate([{"role": "user", "content": prompt}])
            response = response.strip().lower()
            
            # 解析响应
            if "simple" in response:
                return ExecutionMode.SIMPLE
            elif "planning" in response:
                return ExecutionMode.PLANNING
            elif "reflection" in response:
                return ExecutionMode.REFLECTION
            else:
                logger.warning(f"LLM返回了无法识别的模式: {response}")
                return None
                
        except Exception as e:
            logger.error(f"LLM路由判断失败: {e}")
            return None
    
    def _get_cache_key(self, request: str) -> str:
        """
        生成缓存键
        
        Args:
            request: 用户请求
            
        Returns:
            str: 缓存键
        """
        # 简化请求作为缓存键（去除空格、标点，转小写）
        cleaned = re.sub(r'[^\w\s]', '', request.lower())
        cleaned = re.sub(r'\s+', '_', cleaned)
        return cleaned[:100]  # 限制长度
    
    def _cache_decision(self, cache_key: str, decision: RouteDecision):
        """
        缓存路由决策
        
        Args:
            cache_key: 缓存键
            decision: 路由决策
        """
        # 限制缓存大小
        if len(self.route_cache) >= self.cache_size:
            # 移除最早的缓存项
            first_key = next(iter(self.route_cache))
            del self.route_cache[first_key]
        
        self.route_cache[cache_key] = decision
    
    def clear_cache(self):
        """
        清空路由缓存
        """
        self.route_cache.clear()
        logger.debug("路由缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        mode_distribution = {}
        for decision in self.route_cache.values():
            mode = decision.mode
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        return {
            "cache_size": len(self.route_cache),
            "max_size": self.cache_size,
            "mode_distribution": mode_distribution
        }
