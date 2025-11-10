"""
向量存储持久化模块

该模块实现了向量存储的持久化功能，包括：
- FAISS索引持久化
- 元数据管理
"""

from .faiss_persister import FAISSPersister
from .metadata_manager import MetadataManager

__all__ = [
    "FAISSPersister",
    "MetadataManager"
]
