"""
向量缓存

实现向量化结果的缓存机制，提高性能
"""

import json
import logging
import hashlib
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """
    向量缓存类
    
    提供向量化结果的缓存功能，支持持久化存储
    """
    
    def __init__(self, cache_dir: str, max_size: int = 10000):
        """
        初始化向量缓存
        
        Args:
            cache_dir: 缓存目录路径
            max_size: 最大缓存条目数
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        
        # 内存缓存
        self._memory_cache: Dict[str, np.ndarray] = {}
        
        # 缓存元数据
        self._metadata_file = self.cache_dir / "cache_metadata.json"
        self._metadata = self._load_metadata()
        
        logger.info(f"向量缓存初始化完成: 目录={cache_dir}, 最大大小={max_size}")
    
    def _get_text_hash(self, text: str) -> str:
        """
        生成文本的哈希值作为缓存键
        
        Args:
            text: 输入文本
            
        Returns:
            str: 文本哈希值
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, text_hash: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            text_hash: 文本哈希值
            
        Returns:
            Path: 缓存文件路径
        """
        return self.cache_dir / f"{text_hash}.pkl"
    
    async def get(self, text: str) -> Optional[np.ndarray]:
        """
        从缓存中获取向量
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[np.ndarray]: 缓存的向量，如果不存在则返回None
        """
        try:
            text_hash = self._get_text_hash(text)
            
            # 首先检查内存缓存
            if text_hash in self._memory_cache:
                logger.debug(f"从内存缓存获取向量: {text[:50]}...")
                return self._memory_cache[text_hash]
            
            # 检查磁盘缓存
            cache_file = self._get_cache_file_path(text_hash)
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    vector = pickle.load(f)
                
                # 加载到内存缓存
                self._memory_cache[text_hash] = vector
                
                # 更新访问时间
                self._metadata[text_hash] = {
                    "last_access": self._get_current_timestamp(),
                    "access_count": self._metadata.get(text_hash, {}).get("access_count", 0) + 1
                }
                
                logger.debug(f"从磁盘缓存获取向量: {text[:50]}...")
                return vector
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存向量失败: {e}")
            return None
    
    async def set(self, text: str, vector: np.ndarray) -> bool:
        """
        将向量存储到缓存
        
        Args:
            text: 输入文本
            vector: 向量数据
            
        Returns:
            bool: 是否存储成功
        """
        try:
            text_hash = self._get_text_hash(text)
            
            # 存储到内存缓存
            self._memory_cache[text_hash] = vector.copy()
            
            # 存储到磁盘缓存
            cache_file = self._get_cache_file_path(text_hash)
            with open(cache_file, 'wb') as f:
                pickle.dump(vector, f)
            
            # 更新元数据
            self._metadata[text_hash] = {
                "last_access": self._get_current_timestamp(),
                "access_count": 1,
                "text_preview": text[:100]  # 保存文本预览用于调试
            }
            
            # 检查缓存大小，必要时清理
            await self._cleanup_if_needed()
            
            logger.debug(f"向量已缓存: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"存储缓存向量失败: {e}")
            return False
    
    async def clear(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            bool: 是否清空成功
        """
        try:
            # 清空内存缓存
            self._memory_cache.clear()
            
            # 清空磁盘缓存
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            
            # 清空元数据
            self._metadata.clear()
            self._save_metadata()
            
            logger.info("向量缓存已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        try:
            memory_count = len(self._memory_cache)
            disk_count = len(list(self.cache_dir.glob("*.pkl")))
            
            # 计算总访问次数
            total_access = sum(
                meta.get("access_count", 0) 
                for meta in self._metadata.values()
            )
            
            # 计算缓存大小
            cache_size = sum(
                f.stat().st_size 
                for f in self.cache_dir.glob("*.pkl")
            )
            
            return {
                "memory_cache_count": memory_count,
                "disk_cache_count": disk_count,
                "total_access_count": total_access,
                "cache_size_bytes": cache_size,
                "cache_size_mb": cache_size / (1024 * 1024),
                "max_size": self.max_size,
                "usage_ratio": disk_count / self.max_size if self.max_size > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    def _load_metadata(self) -> Dict[str, Any]:
        """
        加载缓存元数据
        
        Returns:
            Dict[str, Any]: 元数据字典
        """
        try:
            if self._metadata_file.exists():
                with open(self._metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载缓存元数据失败: {e}")
            return {}
    
    def _save_metadata(self) -> bool:
        """
        保存缓存元数据
        
        Returns:
            bool: 是否保存成功
        """
        try:
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {e}")
            return False
    
    def _get_current_timestamp(self) -> float:
        """
        获取当前时间戳
        
        Returns:
            float: 当前时间戳
        """
        import time
        return time.time()
    
    async def _cleanup_if_needed(self) -> None:
        """
        在需要时清理缓存
        """
        try:
            if len(self._metadata) <= self.max_size:
                return
            
            # 按访问时间排序，删除最旧的条目
            sorted_items = sorted(
                self._metadata.items(),
                key=lambda x: x[1].get("last_access", 0)
            )
            
            # 删除最旧的条目
            items_to_remove = len(self._metadata) - self.max_size + 100  # 多删除一些避免频繁清理
            for text_hash, _ in sorted_items[:items_to_remove]:
                # 删除磁盘文件
                cache_file = self._get_cache_file_path(text_hash)
                if cache_file.exists():
                    cache_file.unlink()
                
                # 删除内存缓存
                self._memory_cache.pop(text_hash, None)
                
                # 删除元数据
                self._metadata.pop(text_hash, None)
            
            # 保存更新后的元数据
            self._save_metadata()
            
            logger.info(f"缓存清理完成，删除了 {items_to_remove} 个条目")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
    
    async def warm_up(self, texts: List[str]) -> int:
        """
        预热缓存，批量预加载向量
        
        Args:
            texts: 要预加载的文本列表
            
        Returns:
            int: 成功预加载的数量
        """
        try:
            loaded_count = 0
            for text in texts:
                if await self.get(text) is not None:
                    loaded_count += 1
            
            logger.info(f"缓存预热完成，预加载了 {loaded_count}/{len(texts)} 个向量")
            return loaded_count
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
            return 0
