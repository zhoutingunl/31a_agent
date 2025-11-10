"""
FAISS索引持久化管理

实现FAISS索引的保存和加载功能
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)


class FAISSPersister:
    """
    FAISS索引持久化管理
    
    负责FAISS索引的保存、加载和管理
    """
    
    def __init__(self, persist_dir: str):
        """
        初始化FAISS持久化管理器
        
        Args:
            persist_dir: 持久化目录路径
        """
        if faiss is None:
            raise ImportError(
                "faiss-cpu库未安装。请运行: pip install faiss-cpu"
            )
        
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 索引配置文件
        self.config_file = self.persist_dir / "index_config.json"
        
        logger.info(f"FAISS持久化管理器初始化完成: 目录={persist_dir}")
    
    async def save_index(
        self,
        index_name: str,
        index: 'faiss.Index',
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存FAISS索引
        
        Args:
            index_name: 索引名称
            index: FAISS索引对象
            metadata: 索引元数据
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存索引文件
            index_path = self.persist_dir / f"{index_name}.faiss"
            faiss.write_index(index, str(index_path))
            
            # 保存元数据
            if metadata is not None:
                metadata_path = self.persist_dir / f"{index_name}_metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 更新配置文件
            await self._update_config(index_name, metadata)
            
            logger.info(f"FAISS索引已保存: {index_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存FAISS索引失败: {e}")
            return False
    
    async def load_index(
        self,
        index_name: str
    ) -> Optional['faiss.Index']:
        """
        加载FAISS索引
        
        Args:
            index_name: 索引名称
            
        Returns:
            Optional[faiss.Index]: 加载的索引对象，如果不存在则返回None
        """
        try:
            index_path = self.persist_dir / f"{index_name}.faiss"
            if not index_path.exists():
                logger.warning(f"FAISS索引文件不存在: {index_path}")
                return None
            
            index = faiss.read_index(str(index_path))
            logger.info(f"FAISS索引已加载: {index_path}")
            return index
            
        except Exception as e:
            logger.error(f"加载FAISS索引失败: {e}")
            return None
    
    async def load_index_metadata(
        self,
        index_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        加载索引元数据
        
        Args:
            index_name: 索引名称
            
        Returns:
            Optional[Dict[str, Any]]: 元数据字典，如果不存在则返回None
        """
        try:
            metadata_path = self.persist_dir / f"{index_name}_metadata.json"
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"加载索引元数据失败: {e}")
            return None
    
    async def delete_index(self, index_name: str) -> bool:
        """
        删除索引
        
        Args:
            index_name: 索引名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            deleted_files = []
            
            # 删除索引文件
            index_path = self.persist_dir / f"{index_name}.faiss"
            if index_path.exists():
                index_path.unlink()
                deleted_files.append(str(index_path))
            
            # 删除元数据文件
            metadata_path = self.persist_dir / f"{index_name}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()
                deleted_files.append(str(metadata_path))
            
            # 更新配置文件
            await self._remove_from_config(index_name)
            
            logger.info(f"FAISS索引已删除: {deleted_files}")
            return True
            
        except Exception as e:
            logger.error(f"删除FAISS索引失败: {e}")
            return False
    
    async def list_indices(self) -> List[str]:
        """
        列出所有可用的索引
        
        Returns:
            List[str]: 索引名称列表
        """
        try:
            indices = []
            for faiss_file in self.persist_dir.glob("*.faiss"):
                index_name = faiss_file.stem
                indices.append(index_name)
            
            return indices
            
        except Exception as e:
            logger.error(f"列出索引失败: {e}")
            return []
    
    async def get_index_info(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        获取索引信息
        
        Args:
            index_name: 索引名称
            
        Returns:
            Optional[Dict[str, Any]]: 索引信息，如果不存在则返回None
        """
        try:
            index_path = self.persist_dir / f"{index_name}.faiss"
            if not index_path.exists():
                return None
            
            # 获取文件信息
            stat = index_path.stat()
            
            # 加载元数据
            metadata = await self.load_index_metadata(index_name)
            
            # 加载索引获取基本信息
            index = await self.load_index(index_name)
            index_info = None
            if index is not None:
                index_info = {
                    "dimension": index.d,
                    "total_vectors": index.ntotal,
                    "is_trained": index.is_trained
                }
            
            return {
                "name": index_name,
                "file_size": stat.st_size,
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "metadata": metadata,
                "index_info": index_info
            }
            
        except Exception as e:
            logger.error(f"获取索引信息失败: {e}")
            return None
    
    async def _update_config(
        self,
        index_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新配置文件
        
        Args:
            index_name: 索引名称
            metadata: 元数据
        """
        try:
            # 加载现有配置
            config = await self._load_config()
            
            # 更新配置
            config[index_name] = {
                "created_time": self._get_current_timestamp(),
                "metadata": metadata or {}
            }
            
            # 保存配置
            await self._save_config(config)
            
        except Exception as e:
            logger.error(f"更新配置文件失败: {e}")
    
    async def _remove_from_config(self, index_name: str) -> None:
        """
        从配置文件中移除索引
        
        Args:
            index_name: 索引名称
        """
        try:
            # 加载现有配置
            config = await self._load_config()
            
            # 移除索引
            config.pop(index_name, None)
            
            # 保存配置
            await self._save_config(config)
            
        except Exception as e:
            logger.error(f"从配置文件移除索引失败: {e}")
    
    async def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    async def _save_config(self, config: Dict[str, Any]) -> None:
        """
        保存配置文件
        
        Args:
            config: 配置字典
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _get_current_timestamp(self) -> float:
        """
        获取当前时间戳
        
        Returns:
            float: 当前时间戳
        """
        import time
        return time.time()
    
    async def cleanup_old_indices(self, max_age_days: int = 30) -> int:
        """
        清理旧索引
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            int: 清理的索引数量
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 3600
            
            cleaned_count = 0
            for faiss_file in self.persist_dir.glob("*.faiss"):
                file_age = current_time - faiss_file.stat().st_mtime
                if file_age > max_age_seconds:
                    index_name = faiss_file.stem
                    if await self.delete_index(index_name):
                        cleaned_count += 1
            
            logger.info(f"清理了 {cleaned_count} 个旧索引")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧索引失败: {e}")
            return 0
