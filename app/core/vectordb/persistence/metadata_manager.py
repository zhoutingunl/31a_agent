"""
元数据管理器

管理向量存储的元数据，包括向量ID映射、时间戳、访问统计等
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class MetadataManager:
    """
    元数据管理器
    
    负责管理向量存储的元数据信息
    """
    
    def __init__(self, persist_dir: str):
        """
        初始化元数据管理器
        
        Args:
            persist_dir: 持久化目录路径
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 元数据文件
        self.metadata_file = self.persist_dir / "vector_metadata.json"
        
        # 内存中的元数据
        self._metadata: Dict[int, Dict[str, Any]] = {}
        
        # 向量ID到索引位置的映射
        self._id_to_index: Dict[int, int] = {}
        
        # 索引位置到向量ID的映射
        self._index_to_id: Dict[int, int] = {}
        
        # 加载现有元数据
        self._load_metadata()
        
        logger.info(f"元数据管理器初始化完成: 目录={persist_dir}")
    
    def add(
        self,
        vector_id: int,
        memory_type: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        添加向量元数据
        
        Args:
            vector_id: 向量ID
            memory_type: 记忆类型
            metadata: 元数据
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 获取下一个索引位置
            index_position = len(self._metadata)
            
            # 创建元数据记录
            record = {
                "vector_id": vector_id,
                "memory_type": memory_type,
                "index_position": index_position,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "access_count": 0,
                "metadata": metadata
            }
            
            # 添加到内存
            self._metadata[vector_id] = record
            self._id_to_index[vector_id] = index_position
            self._index_to_id[index_position] = vector_id
            
            logger.debug(f"向量元数据已添加: ID={vector_id}, 位置={index_position}")
            return True
            
        except Exception as e:
            logger.error(f"添加向量元数据失败: {e}")
            return False
    
    def get(self, vector_id: int) -> Optional[Dict[str, Any]]:
        """
        获取向量元数据
        
        Args:
            vector_id: 向量ID
            
        Returns:
            Optional[Dict[str, Any]]: 元数据记录，如果不存在则返回None
        """
        try:
            record = self._metadata.get(vector_id)
            if record:
                # 更新访问信息
                record["last_accessed"] = datetime.utcnow().isoformat()
                record["access_count"] = record.get("access_count", 0) + 1
            
            return record
            
        except Exception as e:
            logger.error(f"获取向量元数据失败: {e}")
            return None
    
    def get_by_index(self, index_position: int) -> Optional[Dict[str, Any]]:
        """
        根据索引位置获取元数据
        
        Args:
            index_position: 索引位置
            
        Returns:
            Optional[Dict[str, Any]]: 元数据记录，如果不存在则返回None
        """
        try:
            vector_id = self._index_to_id.get(index_position)
            if vector_id:
                return self.get(vector_id)
            return None
            
        except Exception as e:
            logger.error(f"根据索引位置获取元数据失败: {e}")
            return None
    
    def update(
        self,
        vector_id: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        更新向量元数据
        
        Args:
            vector_id: 向量ID
            metadata: 新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if vector_id not in self._metadata:
                logger.warning(f"向量ID不存在: {vector_id}")
                return False
            
            # 更新元数据
            self._metadata[vector_id]["metadata"].update(metadata)
            self._metadata[vector_id]["last_accessed"] = datetime.utcnow().isoformat()
            
            logger.debug(f"向量元数据已更新: ID={vector_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新向量元数据失败: {e}")
            return False
    
    def remove(self, vector_id: int) -> bool:
        """
        删除向量元数据
        
        Args:
            vector_id: 向量ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if vector_id not in self._metadata:
                logger.warning(f"向量ID不存在: {vector_id}")
                return False
            
            # 获取索引位置
            index_position = self._metadata[vector_id]["index_position"]
            
            # 从内存中删除
            del self._metadata[vector_id]
            del self._id_to_index[vector_id]
            del self._index_to_id[index_position]
            
            logger.debug(f"向量元数据已删除: ID={vector_id}, 位置={index_position}")
            return True
            
        except Exception as e:
            logger.error(f"删除向量元数据失败: {e}")
            return False
    
    def get_all_ids(self) -> List[int]:
        """
        获取所有向量ID
        
        Returns:
            List[int]: 向量ID列表
        """
        return list(self._metadata.keys())
    
    def get_ids_by_type(self, memory_type: str) -> List[int]:
        """
        根据记忆类型获取向量ID列表
        
        Args:
            memory_type: 记忆类型
            
        Returns:
            List[int]: 向量ID列表
        """
        try:
            ids = []
            for vector_id, record in self._metadata.items():
                if record.get("memory_type") == memory_type:
                    ids.append(vector_id)
            return ids
            
        except Exception as e:
            logger.error(f"根据类型获取向量ID失败: {e}")
            return []
    
    def get_ids_by_filter(
        self,
        filter_func: callable
    ) -> List[int]:
        """
        根据过滤函数获取向量ID列表
        
        Args:
            filter_func: 过滤函数，接受元数据记录作为参数
            
        Returns:
            List[int]: 向量ID列表
        """
        try:
            ids = []
            for vector_id, record in self._metadata.items():
                if filter_func(record):
                    ids.append(vector_id)
            return ids
            
        except Exception as e:
            logger.error(f"根据过滤函数获取向量ID失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取元数据统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            total_vectors = len(self._metadata)
            
            # 按类型统计
            type_stats = {}
            for record in self._metadata.values():
                memory_type = record.get("memory_type", "unknown")
                type_stats[memory_type] = type_stats.get(memory_type, 0) + 1
            
            # 访问统计
            total_access = sum(
                record.get("access_count", 0) 
                for record in self._metadata.values()
            )
            
            # 时间统计
            if self._metadata:
                created_times = [
                    datetime.fromisoformat(record["created_at"])
                    for record in self._metadata.values()
                ]
                oldest = min(created_times)
                newest = max(created_times)
            else:
                oldest = newest = None
            
            return {
                "total_vectors": total_vectors,
                "type_distribution": type_stats,
                "total_access_count": total_access,
                "average_access_per_vector": total_access / total_vectors if total_vectors > 0 else 0,
                "oldest_vector": oldest.isoformat() if oldest else None,
                "newest_vector": newest.isoformat() if newest else None
            }
            
        except Exception as e:
            logger.error(f"获取元数据统计失败: {e}")
            return {}
    
    def save(self) -> bool:
        """
        保存元数据到磁盘
        
        Returns:
            bool: 是否保存成功
        """
        try:
            # 准备保存数据
            save_data = {
                "metadata": self._metadata,
                "id_to_index": self._id_to_index,
                "index_to_id": self._index_to_id,
                "saved_at": datetime.utcnow().isoformat()
            }
            
            # 保存到文件
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"元数据已保存: {len(self._metadata)} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
            return False
    
    def _load_metadata(self) -> None:
        """
        从磁盘加载元数据
        """
        try:
            if not self.metadata_file.exists():
                logger.info("元数据文件不存在，使用空元数据")
                return
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # 恢复数据
            self._metadata = save_data.get("metadata", {})
            self._id_to_index = save_data.get("id_to_index", {})
            self._index_to_id = save_data.get("index_to_id", {})
            
            logger.info(f"元数据已加载: {len(self._metadata)} 条记录")
            
        except Exception as e:
            logger.error(f"加载元数据失败: {e}")
            # 使用空数据
            self._metadata = {}
            self._id_to_index = {}
            self._index_to_id = {}
    
    def clear(self) -> bool:
        """
        清空所有元数据
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self._metadata.clear()
            self._id_to_index.clear()
            self._index_to_id.clear()
            
            logger.info("元数据已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空元数据失败: {e}")
            return False
    
    def cleanup_old_metadata(self, max_age_days: int = 30) -> int:
        """
        清理旧元数据
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            int: 清理的记录数量
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            cleaned_count = 0
            
            # 找到需要清理的向量ID
            ids_to_remove = []
            for vector_id, record in self._metadata.items():
                created_at = datetime.fromisoformat(record["created_at"])
                if created_at < cutoff_date:
                    ids_to_remove.append(vector_id)
            
            # 删除旧记录
            for vector_id in ids_to_remove:
                if self.remove(vector_id):
                    cleaned_count += 1
            
            logger.info(f"清理了 {cleaned_count} 条旧元数据")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧元数据失败: {e}")
            return 0
