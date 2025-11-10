"""
记忆压缩器

该模块负责记忆的压缩和摘要生成，包括：
- 相似记忆合并
- LLM驱动的摘要生成
- 关键信息提取
- 冗余信息去除
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime

from app.core.llm.base import BaseLLM
from app.models.memory import MemoryStore

logger = logging.getLogger(__name__)


class MemoryCompressor:
    """
    记忆压缩器
    
    负责记忆的压缩和摘要生成，减少存储空间并保留关键信息
    """
    
    def __init__(self, llm: BaseLLM):
        """
        初始化记忆压缩器
        
        Args:
            llm: 大语言模型实例，用于摘要生成
        """
        self.llm = llm
        self.max_compression_ratio = 0.3  # 最大压缩比例
        self.min_compression_ratio = 0.7  # 最小压缩比例
    
    async def compress_memories(
        self,
        memories: List[MemoryStore],
        compression_ratio: float = 0.5
    ) -> MemoryStore:
        """
        压缩多个记忆为单个摘要记忆
        
        Args:
            memories: 要压缩的记忆列表
            compression_ratio: 压缩比例（0-1），越小压缩越厉害
            
        Returns:
            MemoryStore: 压缩后的记忆对象
        """
        if not memories:
            raise ValueError("记忆列表不能为空")
        
        if len(memories) == 1:
            return memories[0]
        
        try:
            # 确保压缩比例在合理范围内
            compression_ratio = max(
                self.max_compression_ratio,
                min(self.min_compression_ratio, compression_ratio)
            )
            
            # 按重要性排序记忆
            sorted_memories = sorted(
                memories,
                key=lambda m: m.importance_score or 0,
                reverse=True
            )
            
            # 构建压缩提示
            prompt = self._build_compression_prompt(sorted_memories, compression_ratio)
            
            # 调用LLM生成摘要
            response = await self.llm.achat(prompt)
            
            # 解析响应
            compressed_content = self._parse_compression_response(response)
            
            # 创建压缩后的记忆对象
            compressed_memory = self._create_compressed_memory(
                memories, compressed_content
            )
            
            logger.info(f"成功压缩{len(memories)}条记忆，压缩比例: {compression_ratio}")
            return compressed_memory
            
        except Exception as e:
            logger.error(f"记忆压缩失败: {e}")
            # 降级到简单合并
            return self._simple_merge_memories(memories)
    
    async def extract_key_information(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        从记忆内容中提取关键信息
        
        Args:
            content: 记忆内容
            
        Returns:
            Dict[str, Any]: 提取的关键信息
        """
        try:
            # 构建关键信息提取提示
            prompt = self._build_key_extraction_prompt(content)
            
            # 调用LLM提取关键信息
            response = await self.llm.achat(prompt)
            
            # 解析响应
            key_info = self._parse_key_extraction_response(response)
            
            logger.debug(f"成功提取关键信息: {len(key_info)}个字段")
            return key_info
            
        except Exception as e:
            logger.error(f"关键信息提取失败: {e}")
            return {"summary": content[:200] + "..." if len(content) > 200 else content}
    
    async def merge_similar_memories(
        self,
        memories: List[MemoryStore],
        similarity_threshold: float = 0.8
    ) -> List[MemoryStore]:
        """
        合并相似的记忆
        
        Args:
            memories: 记忆列表
            similarity_threshold: 相似度阈值
            
        Returns:
            List[MemoryStore]: 合并后的记忆列表
        """
        if len(memories) <= 1:
            return memories
        
        try:
            # 构建相似性分析提示
            prompt = self._build_similarity_analysis_prompt(memories, similarity_threshold)
            
            # 调用LLM分析相似性
            response = await self.llm.achat(prompt)
            
            # 解析响应，获取合并方案
            merge_groups = self._parse_similarity_response(response, len(memories))
            
            # 执行合并
            merged_memories = []
            for group in merge_groups:
                if len(group) > 1:
                    # 合并组内记忆
                    merged_memory = await self.compress_memories(
                        [memories[i] for i in group],
                        compression_ratio=0.6
                    )
                    merged_memories.append(merged_memory)
                else:
                    # 单独记忆
                    merged_memories.append(memories[group[0]])
            
            logger.info(f"相似记忆合并完成: {len(memories)} -> {len(merged_memories)}")
            return merged_memories
            
        except Exception as e:
            logger.error(f"相似记忆合并失败: {e}")
            return memories
    
    def _build_compression_prompt(
        self,
        memories: List[MemoryStore],
        compression_ratio: float
    ) -> str:
        """
        构建压缩提示
        
        Args:
            memories: 记忆列表
            compression_ratio: 压缩比例
            
        Returns:
            str: 压缩提示
        """
        # 构建记忆内容列表
        memory_contents = []
        for i, memory in enumerate(memories):
            content = f"""
记忆 {i+1}:
- 类型: {memory.memory_type}
- 重要性: {memory.importance_score or 0:.2f}
- 内容: {memory.content}
- 创建时间: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
            memory_contents.append(content)
        
        memory_list = "\n".join(memory_contents)
        
        prompt = f"""
请将以下多条记忆压缩为一条摘要记忆，保留最重要的信息：

{memory_list}

压缩要求：
1. 保留所有关键信息和重要细节
2. 去除冗余和重复信息
3. 保持信息的准确性和完整性
4. 压缩比例约为 {compression_ratio:.1%}
5. 使用清晰、简洁的语言

请返回压缩后的记忆内容，不要包含其他说明。
"""
        return prompt
    
    def _build_key_extraction_prompt(self, content: str) -> str:
        """
        构建关键信息提取提示
        
        Args:
            content: 记忆内容
            
        Returns:
            str: 关键信息提取提示
        """
        prompt = f"""
请从以下记忆内容中提取关键信息，返回JSON格式：

记忆内容：{content}

请提取以下类型的信息：
- summary: 内容摘要（50字以内）
- key_points: 关键要点列表
- entities: 重要实体（人名、地名、概念等）
- emotions: 情感色彩
- importance: 重要性评估（1-10分）
- category: 内容分类

返回格式：
{{
    "summary": "内容摘要",
    "key_points": ["要点1", "要点2"],
    "entities": ["实体1", "实体2"],
    "emotions": "情感描述",
    "importance": 8,
    "category": "分类"
}}
"""
        return prompt
    
    def _build_similarity_analysis_prompt(
        self,
        memories: List[MemoryStore],
        similarity_threshold: float
    ) -> str:
        """
        构建相似性分析提示
        
        Args:
            memories: 记忆列表
            similarity_threshold: 相似度阈值
            
        Returns:
            str: 相似性分析提示
        """
        # 构建记忆内容列表
        memory_contents = []
        for i, memory in enumerate(memories):
            content = f"""
记忆 {i+1}:
- 类型: {memory.memory_type}
- 内容: {memory.content}
"""
            memory_contents.append(content)
        
        memory_list = "\n".join(memory_contents)
        
        prompt = f"""
请分析以下记忆的相似性，将相似的记忆分组：

{memory_list}

相似性标准：
- 内容主题相似
- 涉及相同的人、事、物
- 时间、地点相关
- 相似度阈值: {similarity_threshold:.1%}

请返回JSON格式的分组结果：
{{
    "groups": [
        [1, 3, 5],  // 相似记忆的索引（从1开始）
        [2, 4],     // 另一组相似记忆
        [6]         // 单独的记忆
    ]
}}

注意：
- 每个记忆只能属于一个组
- 组内记忆应该相似
- 组间记忆应该不相似
- 索引从1开始计数
"""
        return prompt
    
    def _parse_compression_response(self, response: str) -> str:
        """
        解析压缩响应
        
        Args:
            response: LLM响应
            
        Returns:
            str: 压缩后的内容
        """
        # 清理响应，去除多余的说明
        response = response.strip()
        
        # 如果响应包含"压缩后的记忆内容："等前缀，去除
        prefixes = [
            "压缩后的记忆内容：",
            "摘要记忆：",
            "压缩结果：",
            "合并后的记忆："
        ]
        
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break
        
        return response
    
    def _parse_key_extraction_response(self, response: str) -> Dict[str, Any]:
        """
        解析关键信息提取响应
        
        Args:
            response: LLM响应
            
        Returns:
            Dict[str, Any]: 提取的关键信息
        """
        try:
            # 尝试解析JSON
            key_info = json.loads(response)
            return key_info
        except json.JSONDecodeError:
            logger.warning(f"无法解析关键信息提取响应为JSON: {response}")
            return {"summary": response[:200] + "..." if len(response) > 200 else response}
    
    def _parse_similarity_response(
        self,
        response: str,
        memory_count: int
    ) -> List[List[int]]:
        """
        解析相似性分析响应
        
        Args:
            response: LLM响应
            memory_count: 记忆总数
            
        Returns:
            List[List[int]]: 合并组列表
        """
        try:
            # 尝试解析JSON
            result = json.loads(response)
            groups = result.get("groups", [])
            
            # 验证分组结果
            all_indices = set()
            for group in groups:
                for idx in group:
                    if 1 <= idx <= memory_count:
                        all_indices.add(idx - 1)  # 转换为0基索引
            
            # 确保所有记忆都被分组
            for i in range(memory_count):
                if i not in all_indices:
                    groups.append([i + 1])  # 添加未分组的记忆
            
            return groups
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"无法解析相似性分析响应: {e}")
            # 返回每个记忆单独成组
            return [[i + 1] for i in range(memory_count)]
    
    def _create_compressed_memory(
        self,
        original_memories: List[MemoryStore],
        compressed_content: str
    ) -> MemoryStore:
        """
        创建压缩后的记忆对象
        
        Args:
            original_memories: 原始记忆列表
            compressed_content: 压缩后的内容
            
        Returns:
            MemoryStore: 压缩后的记忆对象
        """
        # 使用第一个记忆作为基础
        base_memory = original_memories[0]
        
        # 计算平均重要性分数
        avg_importance = sum(
            m.importance_score or 0 for m in original_memories
        ) / len(original_memories)
        
        # 构建压缩元数据
        compression_metadata = {
            "compressed": True,
            "original_count": len(original_memories),
            "original_ids": [m.id for m in original_memories],
            "compression_time": datetime.utcnow().isoformat(),
            "original_types": [m.memory_type for m in original_memories]
        }
        
        # 创建新的记忆对象
        compressed_memory = MemoryStore(
            conversation_id=base_memory.conversation_id,
            user_id=base_memory.user_id,
            content=compressed_content,
            memory_type="long_term",  # 压缩后的记忆通常是长期记忆
            importance_score=avg_importance,
            memory_metadata=compression_metadata
        )
        
        return compressed_memory
    
    def _simple_merge_memories(self, memories: List[MemoryStore]) -> MemoryStore:
        """
        简单合并记忆（降级方案）
        
        Args:
            memories: 记忆列表
            
        Returns:
            MemoryStore: 合并后的记忆对象
        """
        # 按重要性排序
        sorted_memories = sorted(
            memories,
            key=lambda m: m.importance_score or 0,
            reverse=True
        )
        
        # 简单拼接内容
        merged_content = "\n\n".join([
            f"[{m.memory_type}] {m.content}"
            for m in sorted_memories
        ])
        
        # 创建合并后的记忆
        return self._create_compressed_memory(memories, merged_content)
