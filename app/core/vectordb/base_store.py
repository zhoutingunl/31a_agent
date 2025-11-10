"""
向量存储基类

定义了向量存储的标准接口
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """
    向量存储基类
    
    定义了向量存储和检索的标准接口
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def remove_vector(self, vector_id: int) -> bool:
        """
        删除向量
        
        Args:
            vector_id: 向量ID
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_vector(self, vector_id: int) -> Optional[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        获取向量
        
        Args:
            vector_id: 向量ID
            
        Returns:
            Optional[Tuple[np.ndarray, Dict[str, Any]]]: (向量, 元数据) 或 None
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        pass
    
    @abstractmethod
    async def save(self) -> bool:
        """
        保存存储到磁盘
        
        Returns:
            bool: 是否保存成功
        """
        pass
    
    @abstractmethod
    async def load(self) -> bool:
        """
        从磁盘加载存储
        
        Returns:
            bool: 是否加载成功
        """
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """
        清空所有向量
        
        Returns:
            bool: 是否清空成功
        """
        pass
