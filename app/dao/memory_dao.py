"""
文件名: memory_dao.py
功能: 记忆管理相关的数据访问对象
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, desc, asc, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.dao.base import BaseDAO
from app.models.memory import MemoryStore
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryDAO(BaseDAO[MemoryStore]):
    """
    记忆数据访问对象
    
    功能：
    - 记忆的 CRUD 操作
    - 记忆类型管理
    - 记忆检索和过滤
    - 记忆过期处理
    - 重要性评分管理
    """
    
    def __init__(self, db: Session):
        super().__init__(MemoryStore, db)
    
    def create_memory(self,
                     conversation_id: int,
                     memory_type: str,
                     content: str,
                     importance_score: float = 0.0,
                     embedding: Optional[bytes] = None,
                     expires_at: Optional[datetime] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> MemoryStore:
        """
        创建新记忆
        
        参数:
            conversation_id: 会话ID
            memory_type: 记忆类型
            content: 记忆内容
            importance_score: 重要性评分
            embedding: 向量嵌入
            expires_at: 过期时间
            metadata: 元数据
        
        返回:
            MemoryStore: 创建的记忆对象
        
        异常:
            SQLAlchemyError: 数据库操作失败时抛出
        """
        try:
            memory = MemoryStore(
                conversation_id=conversation_id,
                memory_type=memory_type,
                content=content,
                importance_score=importance_score,
                embedding=embedding,
                expires_at=expires_at,
                metadata=metadata
            )
            
            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)
            
            logger.info(f"记忆创建成功: {memory.id} - {memory.memory_type}")
            return memory
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"创建记忆失败: {str(e)}")
            raise
    
    def get_memories_by_conversation(self, 
                                   conversation_id: int,
                                   memory_type: Optional[str] = None,
                                   include_expired: bool = False) -> List[MemoryStore]:
        """
        获取会话的所有记忆
        
        参数:
            conversation_id: 会话ID
            memory_type: 记忆类型过滤（可选）
            include_expired: 是否包含过期记忆
        
        返回:
            List[MemoryStore]: 记忆列表
        """
        try:
            query = select(MemoryStore).where(MemoryStore.conversation_id == conversation_id)
            
            if memory_type:
                query = query.where(MemoryStore.memory_type == memory_type)
            
            if not include_expired:
                query = query.where(
                    or_(
                        MemoryStore.expires_at.is_(None),
                        MemoryStore.expires_at > datetime.utcnow()
                    )
                )
            
            query = query.order_by(desc(MemoryStore.importance_score), desc(MemoryStore.created_at))
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取会话记忆失败: {str(e)}")
            raise
    
    def get_memory_by_id(self, memory_id: int) -> Optional[MemoryStore]:
        """
        根据ID获取记忆
        
        参数:
            memory_id: 记忆ID
        
        返回:
            Optional[MemoryStore]: 记忆对象，如果不存在则返回None
        """
        try:
            query = select(MemoryStore).where(MemoryStore.id == memory_id)
            result = self.db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"获取记忆失败: {str(e)}")
            raise
    
    def get_memories_by_type(self, 
                           memory_type: str,
                           conversation_id: Optional[int] = None,
                           limit: Optional[int] = None) -> List[MemoryStore]:
        """
        根据类型获取记忆
        
        参数:
            memory_type: 记忆类型
            conversation_id: 会话ID（可选，用于过滤特定会话）
            limit: 限制返回数量
        
        返回:
            List[MemoryStore]: 记忆列表
        """
        try:
            query = select(MemoryStore).where(MemoryStore.memory_type == memory_type)
            
            if conversation_id:
                query = query.where(MemoryStore.conversation_id == conversation_id)
            
            # 过滤过期记忆
            query = query.where(
                or_(
                    MemoryStore.expires_at.is_(None),
                    MemoryStore.expires_at > datetime.utcnow()
                )
            )
            
            query = query.order_by(desc(MemoryStore.importance_score), desc(MemoryStore.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取类型记忆失败: {str(e)}")
            raise
    
    def get_important_memories(self, 
                             conversation_id: Optional[int] = None,
                             min_importance: float = 0.5,
                             limit: Optional[int] = None) -> List[MemoryStore]:
        """
        获取重要记忆
        
        参数:
            conversation_id: 会话ID（可选，用于过滤特定会话）
            min_importance: 最小重要性评分
            limit: 限制返回数量
        
        返回:
            List[MemoryStore]: 重要记忆列表
        """
        try:
            query = select(MemoryStore).where(MemoryStore.importance_score >= min_importance)
            
            if conversation_id:
                query = query.where(MemoryStore.conversation_id == conversation_id)
            
            # 过滤过期记忆
            query = query.where(
                or_(
                    MemoryStore.expires_at.is_(None),
                    MemoryStore.expires_at > datetime.utcnow()
                )
            )
            
            query = query.order_by(desc(MemoryStore.importance_score), desc(MemoryStore.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"获取重要记忆失败: {str(e)}")
            raise
    
    def mark_memory_accessed(self, memory_id: int) -> bool:
        """
        标记记忆被访问
        
        参数:
            memory_id: 记忆ID
        
        返回:
            bool: 更新是否成功
        """
        try:
            query = update(MemoryStore).where(MemoryStore.id == memory_id).values(
                access_count=MemoryStore.access_count + 1,
                last_accessed_at=datetime.utcnow()
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"记忆访问标记成功: {memory_id}")
                return True
            else:
                logger.warning(f"记忆不存在: {memory_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"标记记忆访问失败: {str(e)}")
            raise
    
    def update_importance_score(self, memory_id: int, importance_score: float) -> bool:
        """
        更新记忆重要性评分
        
        参数:
            memory_id: 记忆ID
            importance_score: 新的重要性评分
        
        返回:
            bool: 更新是否成功
        """
        try:
            if not 0.0 <= importance_score <= 1.0:
                raise ValueError("重要性评分必须在 0.0 到 1.0 之间")
            
            query = update(MemoryStore).where(MemoryStore.id == memory_id).values(
                importance_score=importance_score
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"记忆重要性评分更新成功: {memory_id} -> {importance_score}")
                return True
            else:
                logger.warning(f"记忆不存在: {memory_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"更新记忆重要性评分失败: {str(e)}")
            raise
    
    def extend_memory_expiration(self, memory_id: int, hours: int = 24) -> bool:
        """
        延长记忆过期时间
        
        参数:
            memory_id: 记忆ID
            hours: 延长小时数
        
        返回:
            bool: 更新是否成功
        """
        try:
            memory = self.get_memory_by_id(memory_id)
            if not memory:
                logger.warning(f"记忆不存在: {memory_id}")
                return False
            
            new_expires_at = memory.expires_at + timedelta(hours=hours) if memory.expires_at else datetime.utcnow() + timedelta(hours=hours)
            
            query = update(MemoryStore).where(MemoryStore.id == memory_id).values(
                expires_at=new_expires_at
            )
            
            result = self.db.execute(query)
            self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"记忆过期时间延长成功: {memory_id} -> {new_expires_at}")
                return True
            else:
                logger.warning(f"记忆不存在: {memory_id}")
                return False
                
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"延长记忆过期时间失败: {str(e)}")
            raise
    
    def cleanup_expired_memories(self, memory_type: Optional[str] = None) -> int:
        """
        清理过期记忆
        
        参数:
            memory_type: 记忆类型（可选，用于过滤特定类型）
        
        返回:
            int: 清理的记忆数量
        """
        try:
            query = delete(MemoryStore).where(
                and_(
                    MemoryStore.expires_at.isnot(None),
                    MemoryStore.expires_at <= datetime.utcnow()
                )
            )
            
            if memory_type:
                query = query.where(MemoryStore.memory_type == memory_type)
            
            result = self.db.execute(query)
            self.db.commit()
            
            deleted_count = result.rowcount
            logger.info(f"清理过期记忆完成: {deleted_count} 条")
            return deleted_count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"清理过期记忆失败: {str(e)}")
            raise
    
    def get_memory_statistics(self, conversation_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        参数:
            conversation_id: 会话ID（可选，用于过滤特定会话）
        
        返回:
            Dict[str, Any]: 记忆统计信息
        """
        try:
            query = select(MemoryStore)
            
            if conversation_id:
                query = query.where(MemoryStore.conversation_id == conversation_id)
            
            result = self.db.execute(query)
            memories = result.scalars().all()
            
            stats = {
                "total": len(memories),
                "by_type": {},
                "by_importance": {
                    "high": 0,    # >= 0.7
                    "medium": 0,  # 0.3 - 0.7
                    "low": 0      # < 0.3
                },
                "expired": 0,
                "total_access_count": 0,
                "avg_importance": 0.0
            }
            
            total_importance = 0.0
            
            for memory in memories:
                # 按类型统计
                if memory.memory_type not in stats["by_type"]:
                    stats["by_type"][memory.memory_type] = 0
                stats["by_type"][memory.memory_type] += 1
                
                # 按重要性统计
                if memory.importance_score >= 0.7:
                    stats["by_importance"]["high"] += 1
                elif memory.importance_score >= 0.3:
                    stats["by_importance"]["medium"] += 1
                else:
                    stats["by_importance"]["low"] += 1
                
                # 过期记忆统计
                if memory.is_expired:
                    stats["expired"] += 1
                
                # 访问次数统计
                stats["total_access_count"] += memory.access_count
                
                # 重要性评分统计
                total_importance += memory.importance_score
            
            # 计算平均重要性
            if len(memories) > 0:
                stats["avg_importance"] = total_importance / len(memories)
            
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"获取记忆统计失败: {str(e)}")
            raise
    
    def search_memories(self, 
                       query_text: str,
                       conversation_id: Optional[int] = None,
                       memory_type: Optional[str] = None,
                       limit: Optional[int] = None) -> List[MemoryStore]:
        """
        搜索记忆（基于内容文本匹配）
        
        参数:
            query_text: 搜索文本
            conversation_id: 会话ID（可选，用于过滤特定会话）
            memory_type: 记忆类型（可选）
            limit: 限制返回数量
        
        返回:
            List[MemoryStore]: 匹配的记忆列表
        """
        try:
            query = select(MemoryStore).where(
                MemoryStore.content.contains(query_text)
            )
            
            if conversation_id:
                query = query.where(MemoryStore.conversation_id == conversation_id)
            
            if memory_type:
                query = query.where(MemoryStore.memory_type == memory_type)
            
            # 过滤过期记忆
            query = query.where(
                or_(
                    MemoryStore.expires_at.is_(None),
                    MemoryStore.expires_at > datetime.utcnow()
                )
            )
            
            query = query.order_by(desc(MemoryStore.importance_score), desc(MemoryStore.created_at))
            
            if limit:
                query = query.limit(limit)
            
            result = self.db.execute(query)
            return result.scalars().all()
            
        except SQLAlchemyError as e:
            logger.error(f"搜索记忆失败: {str(e)}")
            raise
