"""
GPU版本的记忆向量存储

基于FAISS GPU实现的记忆向量存储和检索系统
需要安装faiss-gpu和CUDA环境
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

try:
    import faiss
    import faiss.contrib.torch_utils  # 用于GPU支持
except ImportError:
    faiss = None

from .base_store import BaseVectorStore
from .persistence.faiss_persister import FAISSPersister
from .persistence.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)


class MemoryVectorStoreGPU(BaseVectorStore):
    """
    GPU版本的记忆向量存储
    
    基于FAISS GPU实现的记忆向量存储和检索系统
    支持GPU加速的向量检索
    """
    
    def __init__(
        self,
        embedding_service,
        persist_dir: str,
        index_type: str = "IVFFlat",
        nlist: int = 1000,
        gpu_id: int = 0,
        gpu_memory_fraction: float = 0.8
    ):
        """
        初始化GPU版本的记忆向量存储
        
        Args:
            embedding_service: 向量化服务
            persist_dir: 持久化目录
            index_type: 索引类型 ("Flat" 或 "IVFFlat")
            nlist: IVFFlat索引的聚类中心数量
            gpu_id: GPU设备ID
            gpu_memory_fraction: GPU内存使用比例
        """
        if faiss is None:
            raise ImportError(
                "faiss-gpu库未安装。请运行: pip install faiss-gpu"
            )
        
        # 检查GPU可用性
        if not faiss.get_num_gpus():
            raise RuntimeError("没有可用的GPU设备")
        
        self.embedding_service = embedding_service
        self.persist_dir = persist_dir
        self.index_type = index_type
        self.nlist = nlist
        self.gpu_id = gpu_id
        self.gpu_memory_fraction = gpu_memory_fraction
        
        # 持久化管理器
        self.persister = FAISSPersister(persist_dir)
        self.metadata_manager = MetadataManager(persist_dir)
        
        # FAISS索引
        self.short_term_index = None
        self.long_term_index = None
        
        # 索引配置
        self._dimension = embedding_service.dimension
        self.save_interval = 100
        self.vector_count = 0
        
        # 初始化GPU资源
        self._setup_gpu()
        
        # 初始化索引
        self._initialize_indices()
        
        logger.info(f"GPU记忆向量存储初始化完成: 维度={self.dimension}, GPU={gpu_id}")
    
    def _setup_gpu(self):
        """设置GPU资源"""
        try:
            # 设置GPU内存分配
            faiss.StandardGpuResources()
            
            # 创建GPU资源
            self.gpu_resource = faiss.StandardGpuResources()
            self.gpu_resource.setTempMemory(self.gpu_memory_fraction * 1024 * 1024 * 1024)  # 转换为字节
            
            logger.info(f"GPU资源设置完成: GPU {self.gpu_id}, 内存比例 {self.gpu_memory_fraction}")
            
        except Exception as e:
            logger.error(f"GPU资源设置失败: {e}")
            raise
    
    def _initialize_indices(self) -> None:
        """
        初始化FAISS GPU索引
        """
        try:
            if self.index_type == "Flat":
                # 使用Flat索引（精确搜索）
                cpu_index = faiss.IndexFlatIP(self.dimension)
                self.short_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_index
                )
                self.long_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_index
                )
                
            elif self.index_type == "IVFFlat":
                # 使用IVFFlat索引（近似搜索，适合大规模数据）
                quantizer = faiss.IndexFlatIP(self.dimension)
                cpu_index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
                
                # 转换为GPU索引
                self.short_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_index
                )
                self.long_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_index
                )
                
            else:
                raise ValueError(f"不支持的索引类型: {self.index_type}")
            
            logger.info(f"GPU FAISS索引初始化完成: 类型={self.index_type}")
            
        except Exception as e:
            logger.error(f"初始化GPU FAISS索引失败: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        return self._dimension
    
    async def add_memory(
        self,
        memory_id: int,
        content: str,
        memory_type: str,
        metadata: Dict[str, Any]
    ):
        """
        添加记忆到GPU向量存储
        
        Args:
            memory_id: 记忆ID
            content: 记忆内容
            memory_type: 记忆类型
            metadata: 元数据
        """
        try:
            # 向量化
            vector = await self.embedding_service.embed_text(content)
            vector = vector.reshape(1, -1).astype('float32')
            
            # 添加到对应索引
            if memory_type == "short_term":
                self.short_term_index.add(vector)
            else:
                self.long_term_index.add(vector)
            
            # 保存元数据
            await self.metadata_manager.add(
                memory_id=memory_id,
                memory_type=memory_type,
                metadata=metadata
            )
            
            self.vector_count += 1
            
            # 定期持久化
            if self.vector_count % self.save_interval == 0:
                await self.save()
            
            logger.debug(f"记忆 {memory_id} 已添加到GPU向量存储")
            
        except Exception as e:
            logger.error(f"添加记忆到GPU向量存储失败: {e}")
            raise
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 5,
        time_decay: bool = True
    ) -> List[Tuple[int, float]]:
        """
        在GPU上搜索记忆
        
        Args:
            query: 查询文本
            memory_type: 记忆类型过滤
            top_k: 返回结果数量
            time_decay: 是否应用时间衰减
            
        Returns:
            List[Tuple[int, float]]: 搜索结果 (memory_id, similarity_score)
        """
        try:
            # 向量化查询
            query_vector = await self.embedding_service.embed_text(query)
            query_vector = query_vector.reshape(1, -1).astype('float32')
            
            all_results = []
            
            # 搜索短期记忆
            if memory_type is None or memory_type == "short_term":
                if self.short_term_index.ntotal > 0:
                    distances, ids = self.short_term_index.search(query_vector, top_k * 2)
                    all_results.extend(list(zip(ids[0], distances[0])))
            
            # 搜索长期记忆
            if memory_type is None or memory_type == "long_term":
                if self.long_term_index.ntotal > 0:
                    distances, ids = self.long_term_index.search(query_vector, top_k * 2)
                    all_results.extend(list(zip(ids[0], distances[0])))
            
            # 过滤无效结果
            valid_results = [(mid, score) for mid, score in all_results if mid != -1]
            
            # 排序并返回Top-K
            valid_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.debug(f"GPU搜索完成: 查询='{query}', 找到{len(valid_results)}个结果")
            return valid_results[:top_k]
            
        except Exception as e:
            logger.error(f"GPU搜索记忆失败: {e}")
            return []
    
    async def count(self) -> int:
        """获取存储的向量数量"""
        try:
            short_term_count = self.short_term_index.ntotal if self.short_term_index else 0
            long_term_count = self.long_term_index.ntotal if self.long_term_index else 0
            return short_term_count + long_term_count
        except Exception as e:
            logger.error(f"获取GPU向量数量失败: {e}")
            return 0
    
    async def save(self):
        """持久化GPU索引"""
        try:
            # 将GPU索引转回CPU进行保存
            cpu_short_term = faiss.index_gpu_to_cpu(self.short_term_index)
            cpu_long_term = faiss.index_gpu_to_cpu(self.long_term_index)
            
            await self.persister.save_index("short_term", cpu_short_term)
            await self.persister.save_index("long_term", cpu_long_term)
            await self.metadata_manager.save()
            
            logger.info("GPU向量存储已保存")
            
        except Exception as e:
            logger.error(f"保存GPU向量存储失败: {e}")
            raise
    
    async def load(self):
        """从持久化存储加载GPU索引"""
        try:
            # 加载CPU索引
            cpu_short_term = await self.persister.load_index("short_term")
            cpu_long_term = await self.persister.load_index("long_term")
            
            if cpu_short_term:
                self.short_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_short_term
                )
            
            if cpu_long_term:
                self.long_term_index = faiss.index_cpu_to_gpu(
                    self.gpu_resource, self.gpu_id, cpu_long_term
                )
            
            logger.info("GPU向量存储已加载")
            
        except Exception as e:
            logger.error(f"加载GPU向量存储失败: {e}")
            raise
    
    async def clear(self):
        """清空所有向量存储"""
        try:
            self.short_term_index.reset()
            self.long_term_index.reset()
            await self.metadata_manager.clear()
            
            logger.info("GPU向量存储已清空")
            
        except Exception as e:
            logger.error(f"清空GPU向量存储失败: {e}")
            raise
    
    def __del__(self):
        """清理GPU资源"""
        try:
            if hasattr(self, 'gpu_resource'):
                del self.gpu_resource
        except:
            pass
