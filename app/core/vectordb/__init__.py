"""
向量数据库模块

该模块实现了基于FAISS的向量存储和检索功能，包括：
- 向量存储基类
- 记忆向量存储
- FAISS持久化
- 元数据管理
"""

from .base_store import BaseVectorStore
from .memory_vector_store import MemoryVectorStore
from .persistence.faiss_persister import FAISSPersister
from .persistence.metadata_manager import MetadataManager

__all__ = [
    "BaseVectorStore",
    "MemoryVectorStore",
    "FAISSPersister",
    "MetadataManager"
]
