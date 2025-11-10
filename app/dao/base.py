"""
文件名: base.py
功能: DAO 基类，提供通用的 CRUD 操作
"""

from typing import Generic, TypeVar, Type, List, Optional, Any, Dict

from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from app.utils.logger import get_logger
from app.utils.exceptions import DatabaseError, ResourceNotFoundError

# 定义泛型类型
T = TypeVar('T')

logger = get_logger(__name__)


class BaseDAO(Generic[T]):
    """
    DAO 基类
    
    提供通用的 CRUD（创建、读取、更新、删除）操作。
    所有 DAO 类都应继承此类以复用基础功能。
    
    属性:
        model (Type[T]): 数据模型类
        db (Session): 数据库会话
    """
    
    def __init__(self, model: Type[T], db: Session):
        """
        初始化 DAO
        
        参数:
            model (Type[T]): 数据模型类
            db (Session): 数据库会话
        """
        self.model = model  # 数据模型类
        self.db = db  # 数据库会话
        self.logger = get_logger(f"{__name__}.{model.__name__}DAO")  # 日志记录器
    
    # --- 查询操作 ---
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """
        根据 ID 获取单条记录
        
        参数:
            id: 记录ID
        
        返回:
            Optional[T]: 查询结果，如果不存在返回 None
        """
        try:
            # 使用 select 查询代替 get 方法（兼容性更好）
            stmt = select(self.model).where(
                self.model.id == id
            )
            result = self.db.execute(stmt).scalar_one_or_none()
            return result
        except Exception as e:
            self.logger.error(
                "根据ID查询失败",
                model=self.model.__name__,
                id=id,
                error=str(e)
            )
            raise DatabaseError(
                f"查询{self.model.__name__}失败",
                details={"id": id, "error": str(e)}
            )
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None
    ) -> List[T]:
        """
        获取所有记录（分页）
        
        参数:
            skip (int): 跳过的记录数
            limit (int): 返回的最大记录数
            order_by (str): 排序字段名
        
        返回:
            List[T]: 记录列表
        """
        try:
            stmt = select(self.model).offset(skip).limit(limit)
            
            # 添加排序
            if order_by and hasattr(self.model, order_by):
                stmt = stmt.order_by(getattr(self.model, order_by))
            
            result = self.db.execute(stmt).scalars().all()
            return list(result)
            
        except Exception as e:
            self.logger.error(
                "查询列表失败",
                model=self.model.__name__,
                skip=skip,
                limit=limit,
                error=str(e)
            )
            raise DatabaseError(
                f"查询{self.model.__name__}列表失败",
                details={"error": str(e)}
            )
    
    def get_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """
        根据字段值获取单条记录
        
        参数:
            field_name (str): 字段名
            field_value: 字段值
        
        返回:
            Optional[T]: 查询结果
        """
        try:
            stmt = select(self.model).where(
                getattr(self.model, field_name) == field_value
            )
            result = self.db.execute(stmt).scalar_one_or_none()
            return result
            
        except Exception as e:
            self.logger.error(
                "根据字段查询失败",
                model=self.model.__name__,
                field=field_name,
                value=field_value,
                error=str(e)
            )
            raise DatabaseError(
                f"查询{self.model.__name__}失败",
                details={"field": field_name, "value": field_value, "error": str(e)}
            )
    
    def filter_by(self, **filters) -> List[T]:
        """
        根据条件过滤查询
        
        参数:
            **filters: 过滤条件（字段名=值）
        
        返回:
            List[T]: 查询结果列表
        """
        try:
            stmt = select(self.model)
            
            # 添加过滤条件
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)
            
            result = self.db.execute(stmt).scalars().all()
            return list(result)
            
        except Exception as e:
            self.logger.error(
                "条件查询失败",
                model=self.model.__name__,
                filters=filters,
                error=str(e)
            )
            raise DatabaseError(
                f"查询{self.model.__name__}失败",
                details={"filters": filters, "error": str(e)}
            )
    
    def count(self, **filters) -> int:
        """
        统计记录数量
        
        参数:
            **filters: 过滤条件（可选）
        
        返回:
            int: 记录数量
        """
        try:
            stmt = select(func.count()).select_from(self.model)
            
            # 添加过滤条件
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)
            
            count = self.db.execute(stmt).scalar()
            return count or 0
            
        except Exception as e:
            self.logger.error(
                "统计记录数失败",
                model=self.model.__name__,
                filters=filters,
                error=str(e)
            )
            raise DatabaseError(
                f"统计{self.model.__name__}失败",
                details={"error": str(e)}
            )
    
    # --- 创建操作 ---
    
    def create(self, obj: T) -> T:
        """
        创建单条记录
        
        参数:
            obj (T): 要创建的对象
        
        返回:
            T: 创建后的对象（含ID等自动生成的字段）
        """
        try:
            self.db.add(obj)
            self.db.commit()
            self.db.refresh(obj)
            
            self.logger.info(
                "记录创建成功",
                model=self.model.__name__,
                id=getattr(obj, 'id', None)
            )
            
            return obj
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "创建记录失败",
                model=self.model.__name__,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                f"创建{self.model.__name__}失败",
                details={"error": str(e)}
            )
    
    # --- 更新操作 ---
    
    def update_by_id(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """
        根据 ID 更新记录
        
        参数:
            id: 记录ID
            data (dict): 要更新的数据
        
        返回:
            Optional[T]: 更新后的对象
        """
        try:
            # 先查询记录是否存在
            obj = self.get_by_id(id)
            if not obj:
                return None
            
            # 更新字段
            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            
            self.db.commit()
            self.db.refresh(obj)
            
            self.logger.info(
                "记录更新成功",
                model=self.model.__name__,
                id=id
            )
            
            return obj
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "更新记录失败",
                model=self.model.__name__,
                id=id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                f"更新{self.model.__name__}失败",
                details={"id": id, "error": str(e)}
            )
    
    # --- 删除操作 ---
    
    def delete_by_id(self, id: Any, soft_delete: bool = True) -> bool:
        """
        根据 ID 删除记录
        
        参数:
            id: 记录ID
            soft_delete (bool): 是否软删除（设置 status=0）
        
        返回:
            bool: 是否删除成功
        """
        try:
            obj = self.get_by_id(id)
            if not obj:
                return False
            
            if soft_delete and hasattr(obj, 'status'):
                # 软删除：设置 status=0
                obj.status = 0
                self.db.commit()
                self.logger.info(
                    "记录软删除成功",
                    model=self.model.__name__,
                    id=id
                )
            else:
                # 硬删除：直接删除记录
                self.db.delete(obj)
                self.db.commit()
                self.logger.info(
                    "记录硬删除成功",
                    model=self.model.__name__,
                    id=id
                )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(
                "删除记录失败",
                model=self.model.__name__,
                id=id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseError(
                f"删除{self.model.__name__}失败",
                details={"id": id, "error": str(e)}
            )

