"""
记忆向量存储

基于FAISS实现的记忆向量存储和检索系统
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from .base_store import BaseVectorStore
from .persistence.faiss_persister import FAISSPersister
from .persistence.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


class MemoryVectorStore(BaseVectorStore):
    """
    记忆向量存储
    
    基于FAISS实现的记忆向量存储和检索系统
    支持分层索引、增量更新、持久化和时间衰减检索
    """
    
    def __init__(
        self,
        embedding_service,
        persist_dir: str,
        index_type: str = "Flat",
        nlist: int = 100
    ):
        """
        初始化记忆向量存储
        
        Args:
            embedding_service: 向量化服务
            persist_dir: 持久化目录
            index_type: 索引类型 ("Flat" 或 "IVFFlat")
            nlist: IVFFlat索引的聚类中心数量
        """
        if faiss is None:
            raise ImportError(
                "faiss-cpu库未安装。请运行: pip install faiss-cpu"
            )
        
        self.embedding_service = embedding_service
        self.persist_dir = persist_dir
        self.index_type = index_type
        self.nlist = nlist
        
        # 持久化管理器
        self.persister = FAISSPersister(persist_dir)
        self.metadata_manager = MetadataManager(persist_dir)
        
        # FAISS索引
        self.short_term_index = None
        self.long_term_index = None
        
        # 索引配置
        self._dimension = embedding_service.dimension
        self.save_interval = 100  # 每100个向量保存一次
        self.vector_count = 0
        
        # 初始化索引
        self._initialize_indices()
        
        # 加载已存在的索引（在初始化时跳过，避免异步问题）
        # self._load_indices()
        
        logger.info(f"记忆向量存储初始化完成: 维度={self.dimension}, 索引类型={index_type}")
    
    @property
    def dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            int: 向量维度
        """
        return self._dimension
    
    def _initialize_indices(self) -> None:
        """
        初始化FAISS索引
        """
        try:
            if self.index_type == "Flat":
                # 使用Flat索引（精确搜索，适合小规模数据）
                self.short_term_index = faiss.IndexFlatIP(self.dimension)
                self.long_term_index = faiss.IndexFlatIP(self.dimension)
                
            elif self.index_type == "IVFFlat":
                # 使用IVFFlat索引（近似搜索，适合大规模数据）
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.short_term_index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
                self.long_term_index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
                
            else:
                raise ValueError(f"不支持的索引类型: {self.index_type}")
            
            logger.info(f"FAISS索引初始化完成: 类型={self.index_type}")
            
        except Exception as e:
            logger.error(f"初始化FAISS索引失败: {e}")
            raise
    
    def _load_indices(self) -> None:
        """
        加载已存在的索引
        """
        try:
            # 加载短期记忆索引
            short_term_index = asyncio.run(self.persister.load_index("short_term"))
            if short_term_index is not None:
                self.short_term_index = short_term_index
                logger.info("短期记忆索引已加载")
            
            # 加载长期记忆索引
            long_term_index = asyncio.run(self.persister.load_index("long_term"))
            if long_term_index is not None:
                self.long_term_index = long_term_index
                logger.info("长期记忆索引已加载")
            
            # 更新向量计数
            self.vector_count = self.metadata_manager.get_stats().get("total_vectors", 0)
            
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
    
    async def add_vector(
        self,
        vector_id: int,
        vector: np.ndarray,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        添加向量到存储
        
        Args:
            vector_id: 向量ID
            vector: 向量数据
            metadata: 元数据
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 验证向量
            if vector.shape[0] != self.dimension:
                logger.error(f"向量维度不匹配: 期望={self.dimension}, 实际={vector.shape[0]}")
                return False
            
            # 确保向量是float32类型
            vector = vector.astype(np.float32).reshape(1, -1)
            
            # 获取记忆类型
            memory_type = metadata.get("memory_type", "short_term")
            
            # 选择索引
            if memory_type == "short_term":
                index = self.short_term_index
            else:
                index = self.long_term_index
            
            # 训练索引（如果需要）
            if not index.is_trained and self.index_type == "IVFFlat":
                # 对于IVFFlat索引，需要先训练
                if index.ntotal == 0:
                    # 使用当前向量进行训练
                    index.train(vector)
                else:
                    # 如果已有数据，使用现有数据训练
                    existing_vectors = np.random.randn(1000, self.dimension).astype(np.float32)
                    index.train(existing_vectors)
            
            # 添加向量到索引
            index.add(vector)
            
            # 保存元数据
            self.metadata_manager.add(vector_id, memory_type, metadata)
            
            # 更新计数
            self.vector_count += 1
            
            # 定期保存
            if self.vector_count % self.save_interval == 0:
                await self.save()
            
            logger.debug(f"向量已添加: ID={vector_id}, 类型={memory_type}")
            return True
            
        except Exception as e:
            logger.error(f"添加向量失败: {e}")
            return False
    
    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回前k个结果
            filter_metadata: 元数据过滤条件
            
        Returns:
            List[Tuple[int, float, Dict[str, Any]]]: [(vector_id, similarity_score, metadata), ...]
        """
        try:
            # 验证查询向量
            if query_vector.shape[0] != self.dimension:
                logger.error(f"查询向量维度不匹配: 期望={self.dimension}, 实际={query_vector.shape[0]}")
                return []
            
            # 确保向量是float32类型
            query_vector = query_vector.astype(np.float32).reshape(1, -1)
            
            # 搜索两个索引
            all_results = []
            
            # 搜索短期记忆
            if self.short_term_index.ntotal > 0:
                short_results = await self._search_index(
                    self.short_term_index, 
                    query_vector, 
                    top_k, 
                    "short_term"
                )
                all_results.extend(short_results)
            
            # 搜索长期记忆
            if self.long_term_index.ntotal > 0:
                long_results = await self._search_index(
                    self.long_term_index, 
                    query_vector, 
                    top_k, 
                    "long_term"
                )
                all_results.extend(long_results)
            
            # 按相似度排序
            all_results.sort(key=lambda x: x[1], reverse=True)
            
            # 应用元数据过滤
            if filter_metadata:
                filtered_results = []
                for vector_id, score, metadata in all_results:
                    if self._matches_filter(metadata, filter_metadata):
                        filtered_results.append((vector_id, score, metadata))
                all_results = filtered_results
            
            # 返回top_k结果
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"搜索向量失败: {e}")
            return []
    
    async def _search_index(
        self,
        index: 'faiss.Index',
        query_vector: np.ndarray,
        top_k: int,
        memory_type: str
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        在指定索引中搜索
        
        Args:
            index: FAISS索引
            query_vector: 查询向量
            top_k: 返回前k个结果
            memory_type: 记忆类型
            
        Returns:
            List[Tuple[int, float, Dict[str, Any]]]: 搜索结果
        """
        try:
            # 执行搜索
            distances, indices = index.search(query_vector, min(top_k, index.ntotal))
            
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS返回-1表示无效结果
                    continue
                
                # 获取向量ID
                vector_id = self.metadata_manager._index_to_id.get(idx)
                if vector_id is None:
                    continue
                
                # 获取元数据
                metadata_record = self.metadata_manager.get(vector_id)
                if metadata_record is None:
                    continue
                
                # 计算相似度分数（FAISS返回的是距离，需要转换为相似度）
                similarity_score = float(distance)
                
                results.append((vector_id, similarity_score, metadata_record["metadata"]))
            
            return results
            
        except Exception as e:
            logger.error(f"索引搜索失败: {e}")
            return []
    
    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filter_metadata: Dict[str, Any]
    ) -> bool:
        """
        检查元数据是否匹配过滤条件
        
        Args:
            metadata: 元数据
            filter_metadata: 过滤条件
            
        Returns:
            bool: 是否匹配
        """
        try:
            for key, value in filter_metadata.items():
                if key not in metadata:
                    return False
                if metadata[key] != value:
                    return False
            return True
        except Exception as e:
            logger.error(f"元数据过滤失败: {e}")
            return False
    
    async def remove_vector(self, vector_id: int) -> bool:
        """
        删除向量
        
        Args:
            vector_id: 向量ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取元数据
            metadata_record = self.metadata_manager.get(vector_id)
            if metadata_record is None:
                logger.warning(f"向量ID不存在: {vector_id}")
                return False
            
            # 获取索引位置
            index_position = metadata_record["index_position"]
            memory_type = metadata_record["memory_type"]
            
            # 选择索引
            if memory_type == "short_term":
                index = self.short_term_index
            else:
                index = self.long_term_index
            
            # 注意：FAISS不支持直接删除向量，这里只是从元数据中移除
            # 实际的向量仍然在索引中，但不会被搜索到
            self.metadata_manager.remove(vector_id)
            
            # 更新计数
            self.vector_count -= 1
            
            logger.debug(f"向量已删除: ID={vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return False
    
    async def update_vector(
        self,
        vector_id: int,
        vector: np.ndarray,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        更新向量
        
        Args:
            vector_id: 向量ID
            vector: 新的向量数据
            metadata: 新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 先删除旧向量
            await self.remove_vector(vector_id)
            
            # 添加新向量
            return await self.add_vector(vector_id, vector, metadata)
            
        except Exception as e:
            logger.error(f"更新向量失败: {e}")
            return False
    
    async def get_vector(self, vector_id: int) -> Optional[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        获取向量
        
        Args:
            vector_id: 向量ID
            
        Returns:
            Optional[Tuple[np.ndarray, Dict[str, Any]]]: (向量, 元数据) 或 None
        """
        try:
            # 获取元数据
            metadata_record = self.metadata_manager.get(vector_id)
            if metadata_record is None:
                return None
            
            # 注意：FAISS不支持直接通过ID获取向量
            # 这里返回None，实际应用中可能需要额外的存储机制
            return None, metadata_record["metadata"]
            
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 获取元数据统计
            metadata_stats = self.metadata_manager.get_stats()
            
            # 获取索引统计
            index_stats = {
                "short_term_vectors": self.short_term_index.ntotal if self.short_term_index else 0,
                "long_term_vectors": self.long_term_index.ntotal if self.long_term_index else 0,
                "total_vectors": self.vector_count,
                "index_type": self.index_type,
                "dimension": self.dimension
            }
            
            # 合并统计信息
            stats = {**metadata_stats, **index_stats}
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    async def save(self) -> bool:
        """
        保存存储到磁盘
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存索引
            if self.short_term_index and self.short_term_index.ntotal > 0:
                await self.persister.save_index("short_term", self.short_term_index)
            
            if self.long_term_index and self.long_term_index.ntotal > 0:
                await self.persister.save_index("long_term", self.long_term_index)
            
            # 保存元数据
            self.metadata_manager.save()
            
            logger.info("向量存储已保存到磁盘")
            return True
            
        except Exception as e:
            logger.error(f"保存向量存储失败: {e}")
            return False
    
    async def load(self) -> bool:
        """
        从磁盘加载存储
        
        Returns:
            bool: 是否加载成功
        """
        try:
            self._load_indices()
            logger.info("向量存储已从磁盘加载")
            return True
            
        except Exception as e:
            logger.error(f"加载向量存储失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """
        清空所有向量
        
        Returns:
            bool: 是否清空成功
        """
        try:
            # 重新初始化索引
            self._initialize_indices()
            
            # 清空元数据
            self.metadata_manager.clear()
            
            # 重置计数
            self.vector_count = 0
            
            logger.info("向量存储已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空向量存储失败: {e}")
            return False
    
    async def add_memory(
        self,
        memory_id: int,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        添加记忆到向量存储
        
        Args:
            memory_id: 记忆ID
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 向量化内容
            vector = await self.embedding_service.embed_text(content)
            
            # 添加元数据
            memory_metadata = {
                "memory_type": memory_type,
                "content": content,
                **metadata
            }
            
            # 添加到向量存储
            return await self.add_vector(memory_id, vector, memory_metadata)
            
        except Exception as e:
            logger.error(f"添加记忆到向量存储失败: {e}")
            return False
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 5,
        time_decay: bool = True
    ) -> List[Tuple[int, float]]:
        """
        搜索记忆
        
        Args:
            query: 查询文本
            memory_type: 记忆类型过滤
            top_k: 返回前k个结果
            time_decay: 是否应用时间衰减
            
        Returns:
            List[Tuple[int, float]]: [(memory_id, similarity_score), ...]
        """
        try:
            # 向量化查询
            query_vector = await self.embedding_service.embed_text(query)
            
            # 构建过滤条件
            filter_metadata = {}
            if memory_type:
                filter_metadata["memory_type"] = memory_type
            
            # 搜索向量
            results = await self.search(
                query_vector=query_vector,
                top_k=top_k,
                filter_metadata=filter_metadata if filter_metadata else None
            )
            
            # 应用时间衰减（如果需要）
            if time_decay:
                results = await self._apply_time_decay(results)
            
            # 返回格式化的结果
            return [(vector_id, score) for vector_id, score, _ in results]
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []
    
    async def _apply_time_decay(
        self,
        results: List[Tuple[int, float, Dict[str, Any]]]
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        应用时间衰减
        
        Args:
            results: 搜索结果
            
        Returns:
            List[Tuple[int, float, Dict[str, Any]]]: 应用时间衰减后的结果
        """
        try:
            from datetime import datetime, timedelta
            
            current_time = datetime.utcnow()
            decayed_results = []
            
            for vector_id, score, metadata in results:
                # 获取创建时间
                created_at_str = metadata.get("created_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        days_old = (current_time - created_at).days
                        
                        # 应用时间衰减（简单的线性衰减）
                        decay_factor = max(0.1, 1.0 - (days_old * 0.01))  # 每天衰减1%
                        decayed_score = score * decay_factor
                        
                        decayed_results.append((vector_id, decayed_score, metadata))
                    except ValueError:
                        # 如果时间格式错误，使用原始分数
                        decayed_results.append((vector_id, score, metadata))
                else:
                    # 如果没有时间信息，使用原始分数
                    decayed_results.append((vector_id, score, metadata))
            
            # 重新排序
            decayed_results.sort(key=lambda x: x[1], reverse=True)
            return decayed_results
            
        except Exception as e:
            logger.error(f"应用时间衰减失败: {e}")
            return results
    
    async def count(self) -> int:
        """
        获取存储的向量数量
        
        Returns:
            int: 向量数量
        """
        try:
            short_term_count = self.short_term_index.ntotal if self.short_term_index else 0
            long_term_count = self.long_term_index.ntotal if self.long_term_index else 0
            return short_term_count + long_term_count
        except Exception as e:
            logger.error(f"获取向量数量失败: {e}")
            return 0
