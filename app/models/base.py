"""
文件名: base.py
功能: 数据模型基类，提供通用字段和方法
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr


class TimestampMixin:
    """
    时间戳 Mixin 类
    
    为模型添加创建时间和更新时间字段。
    所有需要时间戳的模型都应继承此类。
    """
    
    # SQLAlchemy 2.0: 允许未映射的属性（兼容性设置）
    __allow_unmapped__ = True
    
    @declared_attr
    def created_at(cls):
        """创建时间字段"""
        return Column(
            DateTime,
            nullable=False,
            default=datetime.now,
            comment="创建时间"
        )
    
    @declared_attr
    def updated_at(cls):
        """更新时间字段"""
        return Column(
            DateTime,
            nullable=False,
            default=datetime.now,
            onupdate=datetime.now,
            comment="更新时间"
        )


class BaseModelMixin:
    """
    模型基类 Mixin
    
    提供通用的实用方法，如字典转换、字符串表示等。
    """
    
    def to_dict(self, exclude_fields: list = None) -> Dict[str, Any]:
        """
        将模型转换为字典
        
        参数:
            exclude_fields (list, optional): 要排除的字段列表
        
        返回:
            Dict[str, Any]: 模型字典表示
        """
        exclude_fields = exclude_fields or []
        
        # 获取所有列
        result = {}
        for column in self.__table__.columns:
            field_name = column.name
            
            # 跳过排除的字段
            if field_name in exclude_fields:
                continue
            
            value = getattr(self, field_name)
            
            # 处理特殊类型
            if isinstance(value, datetime):
                result[field_name] = value.isoformat()
            else:
                result[field_name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        从字典更新模型字段
        
        参数:
            data (Dict[str, Any]): 更新数据
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """返回模型的字符串表示"""
        class_name = self.__class__.__name__
        
        # 尝试获取主键值
        try:
            pk_columns = self.__table__.primary_key.columns
            pk_values = [f"{col.name}={getattr(self, col.name)}" for col in pk_columns]
            pk_str = ", ".join(pk_values)
            return f"<{class_name}({pk_str})>"
        except:
            return f"<{class_name}>"

