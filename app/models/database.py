"""
文件名: database.py
功能: 数据库连接和会话管理
"""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.utils.config import config
from app.utils.logger import get_logger
from app.utils.exceptions import DatabaseError

# 获取日志记录器
logger = get_logger(__name__)

# 创建 SQLAlchemy 声明式基类
Base = declarative_base()


def get_database_url() -> str:
    """
    构建数据库连接 URL
    
    返回:
        str: 数据库连接 URL
    
    异常:
        DatabaseError: 数据库配置缺失时抛出
    """
    try:
        # 优先使用环境变量中的DATABASE_URL
        import os
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            logger.info(f"使用环境变量中的数据库URL: {database_url}")
            return database_url
        
        # 从配置中获取数据库连接信息
        host = config.get("database.mysql.host", "localhost")
        port = config.get("database.mysql.port", 3306)
        user = config.get("database.mysql.user", "root")
        password = config.get("database.mysql.password", "")
        database = config.get("database.mysql.database", "agent_db")
        
        # 构建 MySQL 连接 URL
        # 格式: mysql+pymysql://user:password@host:port/database?charset=utf8mb4
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        
        return url
        
    except Exception as e:
        raise DatabaseError(
            "构建数据库连接 URL 失败",
            details={"error": str(e)}
        )


def create_db_engine() -> Engine:
    """
    创建数据库引擎
    
    返回:
        Engine: SQLAlchemy 数据库引擎
    """
    # 获取数据库连接 URL
    database_url = get_database_url()
    
    # 获取连接池配置
    pool_size = config.get("database.mysql.pool_size", 10)
    pool_recycle = config.get("database.mysql.pool_recycle", 3600)
    echo = config.get("database.mysql.echo", False)
    
    # 创建数据库引擎
    engine = create_engine(
        database_url,
        poolclass=QueuePool,  # 使用连接池
        pool_size=pool_size,  # 连接池大小
        pool_recycle=pool_recycle,  # 连接回收时间（秒）
        pool_pre_ping=True,  # 连接前检查连接是否可用
        echo=echo,  # 是否打印 SQL 语句
        future=True  # 使用 SQLAlchemy 2.0 风格
    )
    
    logger.info(
        "数据库引擎创建成功",
        pool_size=pool_size,
        pool_recycle=pool_recycle
    )
    
    return engine


# 创建全局数据库引擎
engine = create_db_engine()

# 创建会话工厂
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # 不自动提交
    autoflush=False,  # 不自动刷新
    expire_on_commit=False,  # 提交后不过期对象
    future=True  # 使用 SQLAlchemy 2.0 风格
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入用）
    
    这个函数用于 FastAPI 的依赖注入系统，
    自动管理数据库会话的生命周期。
    
    Yields:
        Session: 数据库会话对象
    
    示例:
        >>> from fastapi import Depends
        >>> def some_endpoint(db: Session = Depends(get_db)):
        >>>     users = db.query(User).all()
    """
    db = SessionLocal()  # 创建数据库会话
    try:
        yield db  # 返回会话给调用者
    except Exception as e:
        logger.error(
            "数据库会话异常",
            error=str(e),
            exc_info=True
        )
        db.rollback()  # 发生异常时回滚
        raise DatabaseError(
            "数据库操作失败",
            details={"error": str(e)}
        )
    finally:
        db.close()  # 关闭会话


def init_database() -> None:
    """
    初始化数据库（创建所有表）
    
    这个函数会创建所有继承自 Base 的模型对应的数据库表。
    
    异常:
        DatabaseError: 数据库初始化失败时抛出
    """
    try:
        logger.info("开始初始化数据库表...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        logger.info("数据库表创建成功")
        
    except Exception as e:
        logger.error(
            "数据库初始化失败",
            error=str(e),
            exc_info=True
        )
        raise DatabaseError(
            "数据库初始化失败",
            details={"error": str(e)}
        )


def close_database() -> None:
    """
    关闭数据库连接（应用关闭时调用）
    """
    try:
        engine.dispose()  # 释放所有连接
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(
            "关闭数据库连接失败",
            error=str(e),
            exc_info=True
        )


# SQLite 连接优化（如果使用 SQLite）
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    SQLite 连接优化配置
    
    这个事件监听器会在每次创建 SQLite 连接时执行，
    用于设置 SQLite 的性能优化参数。
    
    注意：本项目使用 MySQL，此函数仅作预留。
    """
    if "sqlite" in str(dbapi_conn):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")  # 启用外键约束
        cursor.execute("PRAGMA journal_mode=WAL")  # 启用 WAL 模式
        cursor.close()

