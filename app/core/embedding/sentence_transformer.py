"""
SentenceTransformer向量化实现

基于sentence-transformers库的向量化服务实现
"""

import logging
import asyncio
from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .embedding_service import EmbeddingService
from .embedding_cache import EmbeddingCache

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding(EmbeddingService):
    """
    基于SentenceTransformer的向量化实现
    
    模型: paraphrase-multilingual-MiniLM-L12-v2
    维度: 384
    支持: 多语言
    """
    
    def __init__(
        self, 
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        cache_dir: str = "./data/cache/embeddings",
        device: str = "cpu"
    ):
        """
        初始化SentenceTransformer向量化服务
        
        Args:
            model_name: 模型名称
            cache_dir: 缓存目录
            device: 计算设备 (cpu/cuda)
        """
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers库未安装。请运行: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.device = device
        
        # 初始化模型
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self._dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.error(f"加载SentenceTransformer模型失败: {e}")
            raise
        
        # 初始化缓存
        self.cache = EmbeddingCache(cache_dir)
        
        logger.info(f"SentenceTransformer向量化服务初始化完成: 模型={model_name}, 维度={self._dimension}")
    
    @property
    def dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            int: 向量维度
        """
        return self._dimension
    
    async def embed_text(self, text: str) -> np.ndarray:
        """
        向量化单个文本
        
        Args:
            text: 要向量化的文本
            
        Returns:
            np.ndarray: 向量表示
        """
        try:
            # 检查缓存
            cached_vector = await self.cache.get(text)
            if cached_vector is not None:
                return cached_vector
            
            # 在线程池中执行向量化（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            vector = await loop.run_in_executor(
                None, 
                self._encode_text, 
                text
            )
            
            # 缓存结果
            await self.cache.set(text, vector)
            
            return vector
            
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            # 返回零向量作为降级方案
            return np.zeros(self._dimension, dtype=np.float32)
    
    async def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量向量化文本
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            np.ndarray: 向量矩阵，形状为 (len(texts), dimension)
        """
        try:
            if not texts:
                return np.empty((0, self._dimension), dtype=np.float32)
            
            # 检查缓存
            cached_vectors = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cached_vector = await self.cache.get(text)
                if cached_vector is not None:
                    cached_vectors.append((i, cached_vector))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # 向量化未缓存的文本
            if uncached_texts:
                loop = asyncio.get_event_loop()
                uncached_vectors = await loop.run_in_executor(
                    None,
                    self._encode_batch,
                    uncached_texts
                )
                
                # 缓存新向量
                for text, vector in zip(uncached_texts, uncached_vectors):
                    await self.cache.set(text, vector)
            else:
                uncached_vectors = []
            
            # 合并结果
            result = np.zeros((len(texts), self._dimension), dtype=np.float32)
            
            # 填充缓存的向量
            for i, vector in cached_vectors:
                result[i] = vector
            
            # 填充新向量化的向量
            for i, vector in zip(uncached_indices, uncached_vectors):
                result[i] = vector
            
            return result
            
        except Exception as e:
            logger.error(f"批量文本向量化失败: {e}")
            # 返回零向量矩阵作为降级方案
            return np.zeros((len(texts), self._dimension), dtype=np.float32)
    
    async def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            
        Returns:
            float: 相似度分数 (0-1)
        """
        try:
            # 向量化两个文本
            vector1 = await self.embed_text(text1)
            vector2 = await self.embed_text(text2)
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(vector1, vector2)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"计算文本相似度失败: {e}")
            return 0.0
    
    async def most_similar(
        self, 
        query_text: str, 
        candidate_texts: List[str], 
        top_k: int = 5
    ) -> List[tuple]:
        """
        找到与查询文本最相似的候选文本
        
        Args:
            query_text: 查询文本
            candidate_texts: 候选文本列表
            top_k: 返回前k个最相似的结果
            
        Returns:
            List[tuple]: [(text, similarity_score), ...] 按相似度降序排列
        """
        try:
            if not candidate_texts:
                return []
            
            # 向量化查询文本
            query_vector = await self.embed_text(query_text)
            
            # 批量向量化候选文本
            candidate_vectors = await self.embed_batch(candidate_texts)
            
            # 计算相似度
            similarities = []
            for i, candidate_vector in enumerate(candidate_vectors):
                similarity = self._cosine_similarity(query_vector, candidate_vector)
                similarities.append((candidate_texts[i], float(similarity)))
            
            # 按相似度排序并返回top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"查找最相似文本失败: {e}")
            return []
    
    def _encode_text(self, text: str) -> np.ndarray:
        """
        编码单个文本（同步方法）
        
        Args:
            text: 输入文本
            
        Returns:
            np.ndarray: 向量表示
        """
        try:
            # 预处理文本
            processed_text = self._preprocess_text(text)
            
            # 向量化
            vector = self.model.encode(processed_text, convert_to_numpy=True)
            
            # 确保是float32类型
            return vector.astype(np.float32)
            
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            return np.zeros(self._dimension, dtype=np.float32)
    
    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量编码文本（同步方法）
        
        Args:
            texts: 输入文本列表
            
        Returns:
            np.ndarray: 向量矩阵
        """
        try:
            # 预处理文本
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # 批量向量化
            vectors = self.model.encode(processed_texts, convert_to_numpy=True)
            
            # 确保是float32类型
            return vectors.astype(np.float32)
            
        except Exception as e:
            logger.error(f"批量文本编码失败: {e}")
            return np.zeros((len(texts), self._dimension), dtype=np.float32)
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 预处理后的文本
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 基本清理
        text = text.strip()
        
        # 限制长度（避免过长文本影响性能）
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def _cosine_similarity(self, vector1: np.ndarray, vector2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vector1: 第一个向量
            vector2: 第二个向量
            
        Returns:
            float: 余弦相似度
        """
        try:
            # 计算点积
            dot_product = np.dot(vector1, vector2)
            
            # 计算模长
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            # 避免除零
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # 计算余弦相似度
            similarity = dot_product / (norm1 * norm2)
            
            # 确保结果在[-1, 1]范围内
            return max(-1.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"计算余弦相似度失败: {e}")
            return 0.0
    
    async def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            dict: 缓存统计信息
        """
        return await self.cache.get_cache_stats()
    
    async def clear_cache(self) -> bool:
        """
        清空缓存
        
        Returns:
            bool: 是否清空成功
        """
        return await self.cache.clear()
    
    async def warm_up_cache(self, texts: List[str]) -> int:
        """
        预热缓存
        
        Args:
            texts: 要预加载的文本列表
            
        Returns:
            int: 成功预加载的数量
        """
        return await self.cache.warm_up(texts)
