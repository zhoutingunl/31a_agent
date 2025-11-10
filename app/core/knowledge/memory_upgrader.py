"""
记忆升级器

将高质量记忆升级为知识，实现记忆到知识的转换
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.dao.memory_dao import MemoryDAO
from app.dao.knowledge_dao import KnowledgeDAO
from app.models.memory import MemoryStore
from .knowledge_graph_manager import KnowledgeGraphManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryUpgrader:
    """
    记忆升级器
    
    将高质量记忆升级为知识:
    - 重要性阈值判断
    - 信息提炼和结构化
    - 知识图谱整合
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        memory_dao: MemoryDAO,
        knowledge_dao: KnowledgeDAO,
        knowledge_graph_manager: KnowledgeGraphManager
    ):
        """
        初始化记忆升级器
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            memory_dao: 记忆数据访问对象
            knowledge_dao: 知识数据访问对象
            knowledge_graph_manager: 知识图谱管理器
        """
        self.db = db
        self.llm = llm
        self.memory_dao = memory_dao
        self.knowledge_dao = knowledge_dao
        self.kg_manager = knowledge_graph_manager
        
        # 升级配置
        self.importance_threshold = 0.7
        self.quality_threshold = 0.6
        self.min_content_length = 20
        
        logger.info("记忆升级器初始化完成")
    
    async def upgrade_memories_to_knowledge(
        self,
        memories: List[MemoryStore],
        user_id: int,
        importance_threshold: Optional[float] = None,
        force_upgrade: bool = False
    ) -> Dict[str, Any]:
        """
        将记忆升级为知识
        
        Args:
            memories: 记忆列表
            user_id: 用户ID
            importance_threshold: 重要性阈值
            force_upgrade: 是否强制升级（忽略阈值）
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            threshold = importance_threshold or self.importance_threshold
            
            # 筛选高质量记忆
            if force_upgrade:
                high_quality_memories = memories
            else:
                high_quality_memories = self._filter_high_quality_memories(
                    memories, threshold
                )
            
            if not high_quality_memories:
                return {
                    "upgraded": 0,
                    "skipped": len(memories),
                    "message": f"没有记忆满足重要性阈值 {threshold}"
                }
            
            logger.info(f"开始升级 {len(high_quality_memories)} 个高质量记忆")
            
            # 构建知识图谱
            kg_result = await self.kg_manager.build_from_memories(
                memories=high_quality_memories,
                user_id=user_id
            )
            
            # 标记记忆已升级
            upgraded_count = 0
            for memory in high_quality_memories:
                try:
                    # 更新记忆元数据
                    memory.memory_metadata = memory.memory_metadata or {}
                    memory.memory_metadata["upgraded_to_knowledge"] = True
                    memory.memory_metadata["upgraded_at"] = datetime.now().isoformat()
                    memory.memory_metadata["knowledge_entities"] = kg_result.get("entities_created", 0)
                    memory.memory_metadata["knowledge_relations"] = kg_result.get("relations_created", 0)
                    
                    self.memory_dao.update(memory)
                    upgraded_count += 1
                    
                except Exception as e:
                    logger.error(f"标记记忆 {memory.id} 升级状态失败: {e}")
                    continue
            
            result = {
                "upgraded": upgraded_count,
                "skipped": len(memories) - len(high_quality_memories),
                "entities_created": kg_result.get("entities_created", 0),
                "relations_created": kg_result.get("relations_created", 0),
                "processed_memories": kg_result.get("processed_memories", 0),
                "message": f"成功升级 {upgraded_count} 个记忆为知识"
            }
            
            logger.info(f"记忆升级完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"记忆升级失败: {e}")
            return {
                "upgraded": 0,
                "skipped": len(memories),
                "error": str(e)
            }
    
    def _filter_high_quality_memories(
        self,
        memories: List[MemoryStore],
        importance_threshold: float
    ) -> List[MemoryStore]:
        """
        筛选高质量记忆
        
        Args:
            memories: 记忆列表
            importance_threshold: 重要性阈值
            
        Returns:
            List[MemoryStore]: 高质量记忆列表
        """
        high_quality = []
        
        for memory in memories:
            # 检查是否已经升级
            if memory.memory_metadata and memory.memory_metadata.get("upgraded_to_knowledge"):
                continue
            
            # 检查重要性分数
            if memory.importance_score is None or memory.importance_score < importance_threshold:
                continue
            
            # 检查内容长度
            if len(memory.content.strip()) < self.min_content_length:
                continue
            
            # 检查记忆类型（某些类型不适合升级）
            if memory.memory_type in ["temporary", "session"]:
                continue
            
            # 检查质量分数（如果有）
            quality_score = memory.memory_metadata.get("quality_score", 1.0) if memory.memory_metadata else 1.0
            if quality_score < self.quality_threshold:
                continue
            
            high_quality.append(memory)
        
        logger.debug(f"从 {len(memories)} 个记忆中筛选出 {len(high_quality)} 个高质量记忆")
        return high_quality
    
    async def upgrade_conversation_memories(
        self,
        conversation_id: int,
        user_id: int,
        importance_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        升级会话中的记忆
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            importance_threshold: 重要性阈值
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            # 获取会话记忆
            memories = self.memory_dao.get_by_conversation(conversation_id)
            
            if not memories:
                return {
                    "upgraded": 0,
                    "skipped": 0,
                    "message": "会话中没有记忆"
                }
            
            # 升级记忆
            result = await self.upgrade_memories_to_knowledge(
                memories=memories,
                user_id=user_id,
                importance_threshold=importance_threshold
            )
            
            result["conversation_id"] = conversation_id
            return result
            
        except Exception as e:
            logger.error(f"升级会话记忆失败: {e}")
            return {
                "upgraded": 0,
                "skipped": 0,
                "conversation_id": conversation_id,
                "error": str(e)
            }
    
    async def upgrade_user_memories(
        self,
        user_id: int,
        importance_threshold: Optional[float] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        升级用户的所有记忆
        
        Args:
            user_id: 用户ID
            importance_threshold: 重要性阈值
            limit: 限制处理数量
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            # 获取用户记忆
            memories = self.memory_dao.get_by_user(user_id, limit=limit)
            
            if not memories:
                return {
                    "upgraded": 0,
                    "skipped": 0,
                    "message": "用户没有记忆"
                }
            
            # 升级记忆
            result = await self.upgrade_memories_to_knowledge(
                memories=memories,
                user_id=user_id,
                importance_threshold=importance_threshold
            )
            
            result["user_id"] = user_id
            return result
            
        except Exception as e:
            logger.error(f"升级用户记忆失败: {e}")
            return {
                "upgraded": 0,
                "skipped": 0,
                "user_id": user_id,
                "error": str(e)
            }
    
    async def get_upgrade_candidates(
        self,
        user_id: int,
        importance_threshold: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取可升级的记忆候选
        
        Args:
            user_id: 用户ID
            importance_threshold: 重要性阈值
            limit: 限制数量
            
        Returns:
            List[Dict[str, Any]]: 候选记忆列表
        """
        try:
            threshold = importance_threshold or self.importance_threshold
            
            # 获取用户记忆
            memories = self.memory_dao.get_by_user(user_id, limit=limit)
            
            candidates = []
            for memory in memories:
                # 检查是否已经升级
                if memory.memory_metadata and memory.memory_metadata.get("upgraded_to_knowledge"):
                    continue
                
                # 检查重要性分数
                if memory.importance_score is None or memory.importance_score < threshold:
                    continue
                
                # 检查内容长度
                if len(memory.content.strip()) < self.min_content_length:
                    continue
                
                # 检查记忆类型
                if memory.memory_type in ["temporary", "session"]:
                    continue
                
                # 计算升级潜力分数
                upgrade_potential = self._calculate_upgrade_potential(memory)
                
                candidates.append({
                    "memory_id": memory.id,
                    "content": memory.content[:100] + "..." if len(memory.content) > 100 else memory.content,
                    "memory_type": memory.memory_type,
                    "importance_score": memory.importance_score,
                    "upgrade_potential": upgrade_potential,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "conversation_id": memory.conversation_id
                })
            
            # 按升级潜力排序
            candidates.sort(key=lambda x: x["upgrade_potential"], reverse=True)
            
            logger.info(f"找到 {len(candidates)} 个升级候选记忆")
            return candidates
            
        except Exception as e:
            logger.error(f"获取升级候选失败: {e}")
            return []
    
    def _calculate_upgrade_potential(self, memory: MemoryStore) -> float:
        """
        计算记忆的升级潜力分数
        
        Args:
            memory: 记忆对象
            
        Returns:
            float: 升级潜力分数 (0-1)
        """
        try:
            score = 0.0
            
            # 重要性分数权重 (40%)
            if memory.importance_score is not None:
                score += memory.importance_score * 0.4
            
            # 内容长度权重 (20%)
            content_length = len(memory.content.strip())
            if content_length >= 100:
                score += 0.2
            elif content_length >= 50:
                score += 0.15
            elif content_length >= 20:
                score += 0.1
            
            # 记忆类型权重 (20%)
            type_weights = {
                "fact": 0.2,
                "preference": 0.15,
                "skill": 0.15,
                "goal": 0.1,
                "episodic": 0.1,
                "semantic": 0.2
            }
            score += type_weights.get(memory.memory_type, 0.05)
            
            # 质量分数权重 (20%)
            if memory.memory_metadata:
                quality_score = memory.memory_metadata.get("quality_score", 0.5)
                score += quality_score * 0.2
            else:
                score += 0.1  # 默认质量分数
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"计算升级潜力失败: {e}")
            return 0.0
    
    async def batch_upgrade_memories(
        self,
        memory_ids: List[int],
        user_id: int,
        force_upgrade: bool = False
    ) -> Dict[str, Any]:
        """
        批量升级指定记忆
        
        Args:
            memory_ids: 记忆ID列表
            user_id: 用户ID
            force_upgrade: 是否强制升级
            
        Returns:
            Dict[str, Any]: 升级结果
        """
        try:
            memories = []
            for memory_id in memory_ids:
                memory = self.memory_dao.get_by_id(memory_id)
                if memory and memory.conversation_id:  # 确保记忆存在且有会话ID
                    memories.append(memory)
            
            if not memories:
                return {
                    "upgraded": 0,
                    "skipped": len(memory_ids),
                    "message": "没有找到有效的记忆"
                }
            
            # 升级记忆
            result = await self.upgrade_memories_to_knowledge(
                memories=memories,
                user_id=user_id,
                force_upgrade=force_upgrade
            )
            
            result["requested_count"] = len(memory_ids)
            return result
            
        except Exception as e:
            logger.error(f"批量升级记忆失败: {e}")
            return {
                "upgraded": 0,
                "skipped": len(memory_ids),
                "error": str(e)
            }
    
    async def get_upgrade_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        获取升级统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 获取用户所有记忆
            all_memories = self.memory_dao.get_by_user(user_id)
            
            # 统计已升级的记忆
            upgraded_memories = [
                m for m in all_memories
                if m.memory_metadata and m.memory_metadata.get("upgraded_to_knowledge")
            ]
            
            # 统计可升级的记忆
            upgradeable_memories = self._filter_high_quality_memories(
                all_memories, self.importance_threshold
            )
            
            # 按记忆类型统计
            type_stats = {}
            for memory in all_memories:
                memory_type = memory.memory_type
                if memory_type not in type_stats:
                    type_stats[memory_type] = {
                        "total": 0,
                        "upgraded": 0,
                        "upgradeable": 0
                    }
                
                type_stats[memory_type]["total"] += 1
                
                if memory.memory_metadata and memory.memory_metadata.get("upgraded_to_knowledge"):
                    type_stats[memory_type]["upgraded"] += 1
                
                if memory in upgradeable_memories:
                    type_stats[memory_type]["upgradeable"] += 1
            
            # 获取知识图谱统计
            kg_stats = await self.kg_manager.get_entity_statistics(user_id)
            
            return {
                "total_memories": len(all_memories),
                "upgraded_memories": len(upgraded_memories),
                "upgradeable_memories": len(upgradeable_memories),
                "upgrade_rate": len(upgraded_memories) / len(all_memories) if all_memories else 0,
                "type_statistics": type_stats,
                "knowledge_graph": kg_stats
            }
            
        except Exception as e:
            logger.error(f"获取升级统计信息失败: {e}")
            return {
                "total_memories": 0,
                "upgraded_memories": 0,
                "upgradeable_memories": 0,
                "upgrade_rate": 0,
                "type_statistics": {},
                "knowledge_graph": {},
                "error": str(e)
            }
    
    def set_upgrade_thresholds(
        self,
        importance_threshold: Optional[float] = None,
        quality_threshold: Optional[float] = None,
        min_content_length: Optional[int] = None
    ):
        """
        设置升级阈值
        
        Args:
            importance_threshold: 重要性阈值
            quality_threshold: 质量阈值
            min_content_length: 最小内容长度
        """
        if importance_threshold is not None:
            self.importance_threshold = importance_threshold
        
        if quality_threshold is not None:
            self.quality_threshold = quality_threshold
        
        if min_content_length is not None:
            self.min_content_length = min_content_length
        
        logger.info(f"升级阈值已更新: 重要性={self.importance_threshold}, 质量={self.quality_threshold}, 最小长度={self.min_content_length}")
