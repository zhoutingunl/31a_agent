"""
记忆分类器

该模块负责将记忆内容分类为不同的类型：
- short_term: 会话内临时信息
- long_term: 重要的跨会话信息  
- episodic: 具体事件记录
- semantic: 抽象知识和概念
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class MemoryClassifier:
    """
    记忆分类器
    
    使用LLM或规则判断记忆类型，支持批量分类
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化记忆分类器
        
        Args:
            llm: 大语言模型实例，用于智能分类
        """
        self.llm = llm
        self.memory_types = {
            "short_term": "短期记忆 - 会话内临时信息，如当前对话的上下文",
            "long_term": "长期记忆 - 重要的跨会话信息，如用户偏好、重要事实",
            "episodic": "情景记忆 - 具体事件记录，如用户做了什么、发生了什么",
            "semantic": "语义记忆 - 抽象知识和概念，如定义、规则、原理"
        }
    
    async def classify_memory(
        self,
        content: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        分类单个记忆内容
        
        Args:
            content: 记忆内容
            context: 上下文信息，如会话ID、用户ID等
            
        Returns:
            str: 记忆类型
        """
        try:
            # 构建分类提示
            prompt = self._build_classification_prompt(content, context)
            
            # 调用LLM进行分类
            response = await self.llm.achat(prompt)
            
            # 解析响应
            memory_type = self._parse_classification_response(response)
            
            logger.debug(f"记忆分类结果: {memory_type} for content: {content[:50]}...")
            return memory_type
            
        except Exception as e:
            logger.error(f"记忆分类失败: {e}")
            # 降级到规则分类
            return self._rule_based_classification(content)
    
    async def batch_classify(
        self,
        contents: List[str]
    ) -> List[str]:
        """
        批量分类记忆内容
        
        Args:
            contents: 记忆内容列表
            
        Returns:
            List[str]: 对应的记忆类型列表
        """
        if not contents:
            return []
        
        try:
            # 构建批量分类提示
            prompt = self._build_batch_classification_prompt(contents)
            
            # 调用LLM进行批量分类
            response = await self.llm.achat(prompt)
            
            # 解析响应
            memory_types = self._parse_batch_classification_response(response, len(contents))
            
            logger.debug(f"批量记忆分类完成，共{len(contents)}条")
            return memory_types
            
        except Exception as e:
            logger.error(f"批量记忆分类失败: {e}")
            # 降级到逐个规则分类
            return [self._rule_based_classification(content) for content in contents]
    
    def _build_classification_prompt(
        self,
        content: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        构建分类提示
        
        Args:
            content: 记忆内容
            context: 上下文信息
            
        Returns:
            str: 分类提示
        """
        context_info = ""
        if context:
            context_info = f"\n上下文信息: {json.dumps(context, ensure_ascii=False)}"
        
        prompt = f"""
请分析以下记忆内容，并将其分类为以下四种类型之一：

记忆类型说明：
- short_term: 短期记忆 - 会话内临时信息，如当前对话的上下文、临时状态
- long_term: 长期记忆 - 重要的跨会话信息，如用户偏好、重要事实、个人资料
- episodic: 情景记忆 - 具体事件记录，如用户做了什么、发生了什么、经历的事件
- semantic: 语义记忆 - 抽象知识和概念，如定义、规则、原理、概念解释

记忆内容：
{content}
{context_info}

请只返回一个类型名称（short_term、long_term、episodic、semantic），不要包含其他内容。
"""
        return prompt
    
    def _build_batch_classification_prompt(self, contents: List[str]) -> str:
        """
        构建批量分类提示
        
        Args:
            contents: 记忆内容列表
            
        Returns:
            str: 批量分类提示
        """
        content_list = "\n".join([f"{i+1}. {content}" for i, content in enumerate(contents)])
        
        prompt = f"""
请分析以下记忆内容列表，并将每条内容分类为以下四种类型之一：

记忆类型说明：
- short_term: 短期记忆 - 会话内临时信息，如当前对话的上下文、临时状态
- long_term: 长期记忆 - 重要的跨会话信息，如用户偏好、重要事实、个人资料
- episodic: 情景记忆 - 具体事件记录，如用户做了什么、发生了什么、经历的事件
- semantic: 语义记忆 - 抽象知识和概念，如定义、规则、原理、概念解释

记忆内容列表：
{content_list}

请返回JSON格式的结果，格式如下：
[
    "short_term",
    "long_term", 
    "episodic",
    "semantic"
]

请确保返回的数组长度与输入内容数量一致。
"""
        return prompt
    
    def _parse_classification_response(self, response: str) -> str:
        """
        解析分类响应
        
        Args:
            response: LLM响应
            
        Returns:
            str: 解析出的记忆类型
        """
        response = response.strip().lower()
        
        # 直接匹配类型名称
        for memory_type in self.memory_types.keys():
            if memory_type in response:
                return memory_type
        
        # 如果无法解析，返回默认类型
        logger.warning(f"无法解析分类响应: {response}")
        return "short_term"
    
    def _parse_batch_classification_response(
        self,
        response: str,
        expected_count: int
    ) -> List[str]:
        """
        解析批量分类响应
        
        Args:
            response: LLM响应
            expected_count: 期望的结果数量
            
        Returns:
            List[str]: 解析出的记忆类型列表
        """
        try:
            # 尝试解析JSON
            result = json.loads(response)
            if isinstance(result, list) and len(result) == expected_count:
                # 验证所有类型都是有效的
                valid_types = []
                for memory_type in result:
                    if memory_type in self.memory_types:
                        valid_types.append(memory_type)
                    else:
                        logger.warning(f"无效的记忆类型: {memory_type}")
                        valid_types.append("short_term")
                return valid_types
        except json.JSONDecodeError:
            logger.warning(f"无法解析批量分类响应为JSON: {response}")
        
        # 如果解析失败，返回默认类型列表
        return ["short_term"] * expected_count
    
    def _rule_based_classification(self, content: str) -> str:
        """
        基于规则的分类（降级方案）
        
        Args:
            content: 记忆内容
            
        Returns:
            str: 记忆类型
        """
        content_lower = content.lower()
        
        # 关键词匹配规则
        if any(keyword in content_lower for keyword in ["用户", "偏好", "喜欢", "不喜欢", "设置"]):
            return "long_term"
        elif any(keyword in content_lower for keyword in ["做了", "发生", "事件", "经历", "完成"]):
            return "episodic"
        elif any(keyword in content_lower for keyword in ["定义", "概念", "原理", "规则", "解释"]):
            return "semantic"
        else:
            return "short_term"
