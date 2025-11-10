"""
文件名: user_dao.py
功能: 用户数据访问对象，负责用户相关的数据库操作
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.dao.base import BaseDAO
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UserDAO(BaseDAO[User]):
    """
    用户 DAO 类
    
    提供用户相关的数据库操作。
    """
    
    def __init__(self, db: Session):
        """
        初始化用户 DAO
        
        参数:
            db (Session): 数据库会话
        """
        super().__init__(User, db)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名查询用户
        
        参数:
            username (str): 用户名
        
        返回:
            Optional[User]: 用户对象
        """
        return self.get_by_field("username", username)
    
    def create_user(self, username: str, nickname: str = None) -> User:
        """
        创建新用户
        
        参数:
            username (str): 用户名
            nickname (str, optional): 用户昵称
        
        返回:
            User: 创建的用户对象
        """
        user = User(
            username=username,
            nickname=nickname or username,
            status=1
        )
        return self.create(user)

