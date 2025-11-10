"""
向量化服务抽象基类

定义了向量化服务的标准接口
"""

import logging
from abc import ABC, abstractmethod
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """
    向量化服务抽象基类
    
    定义了文本向量化的标准接口
    """
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        获取向量维度
        
        Returns:
            int: 向量维度
        """
        pass
    
    @abstractmethod
    async def embed_text(self, text: str) -> np.ndarray:
        """
        向量化单个文本
        
        Args:
            text: 要向量化的文本
            
        Returns:
            np.ndarray: 向量表示
        """
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        批量向量化文本
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            np.ndarray: 向量矩阵，形状为 (len(texts), dimension)
        """
        pass
    
    @abstractmethod
    async def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 第一个文本
            text2: 第二个文本
            
        Returns:
            float: 相似度分数 (0-1)
        """
        pass
    
    @abstractmethod
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
        pass
