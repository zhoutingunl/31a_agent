"""
文件名: init_database.py
功能: 统一的数据库初始化脚本
包含：基础表创建 + 智能体系统表创建 + 测试数据插入
"""

import sys
import io
from pathlib import Path

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from app.utils.config import config
from app.utils.logger import get_logger
from app.utils.exceptions import DatabaseError
from app.models import init_database, SessionLocal, User
from app.models.database import engine
from sqlalchemy import text

# 获取日志记录器
logger = get_logger(__name__)


def create_database_if_not_exists():
    """
    如果数据库不存在则创建数据库
    """
    try:
        # 获取数据库连接信息
        host = config.get("database.mysql.host", "localhost")
        port = config.get("database.mysql.port", 3306)
        user = config.get("database.mysql.user", "root")
        password = config.get("database.mysql.password", "")
        database = config.get("database.mysql.database", "agent_db")
        
        logger.info("正在检查数据库是否存在...", database=database)
        
        # 连接到 MySQL（不指定数据库）
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        try:
            with connection.cursor() as cursor:
                # 创建数据库（如果不存在）
                create_db_sql = f"""
                CREATE DATABASE IF NOT EXISTS `{database}`
                CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
                cursor.execute(create_db_sql)
                connection.commit()
                
                logger.info("数据库检查完成", database=database)
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error("创建数据库失败", error=str(e), exc_info=True)
        raise DatabaseError(f"创建数据库失败: {str(e)}")


def create_basic_tables():
    """
    创建基础数据库表（user, conversation, message）
    """
    try:
        logger.info("开始创建基础数据库表...")
        
        # 调用初始化函数创建基础表
        init_database()
        
        logger.info("基础数据库表创建完成")
        
    except Exception as e:
        logger.error("创建基础数据库表失败", error=str(e), exc_info=True)
        raise DatabaseError(f"创建基础数据库表失败: {str(e)}")


def create_agent_tables():
    """
    创建智能体系统相关表
    """
    try:
        logger.info("开始创建智能体系统表...")
        
        # SQL 文件路径
        sql_file = project_root / "scripts" / "migrations" / "001_add_agent_tables.sql"
        
        if not sql_file.exists():
            logger.error(f"SQL 文件不存在: {sql_file}")
            raise DatabaseError(f"SQL 文件不存在: {sql_file}")
        
        # 读取并执行 SQL 文件
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割 SQL 语句（按分号分割）
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        with engine.connect() as conn:
            for statement in sql_statements:
                if statement.upper().startswith('SELECT'):
                    # 对于 SELECT 语句，执行并打印结果
                    result = conn.execute(text(statement))
                    for row in result:
                        logger.info(f"SQL 结果: {row}")
                else:
                    # 对于 DDL 语句，直接执行
                    conn.execute(text(statement))
            
            conn.commit()
        
        logger.info("智能体系统表创建完成")
        
    except Exception as e:
        logger.error("创建智能体系统表失败", error=str(e), exc_info=True)
        raise DatabaseError(f"创建智能体系统表失败: {str(e)}")


def verify_tables_created():
    """
    验证所有表是否创建成功
    """
    expected_tables = [
        'user', 'conversation', 'message',  # 基础表
        'task', 'memory_store', 'knowledge_graph', 'knowledge_relation'  # 智能体表
    ]
    
    try:
        with engine.connect() as conn:
            # 查询所有表名
            result = conn.execute(text("SHOW TABLES"))
            existing_tables = [row[0] for row in result]
            
            # 检查期望的表是否存在
            missing_tables = []
            for table in expected_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
            
            if missing_tables:
                logger.error(f"缺少表: {missing_tables}")
                return False
            
            logger.info(f"所有表创建成功: {expected_tables}")
            return True
            
    except Exception as e:
        logger.error("验证表创建失败", error=str(e))
        return False


def insert_test_data():
    """
    插入测试数据
    """
    db = SessionLocal()
    try:
        logger.info("开始插入测试数据...")
        
        # 检查是否已有测试用户
        existing_user = db.query(User).filter_by(username="test_user").first()
        
        if existing_user:
            logger.info("测试用户已存在，跳过插入", user_id=existing_user.id)
            return
        
        # 创建测试用户
        test_user = User(
            username="test_user",
            nickname="测试用户",
            avatar=None,
            status=1
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        logger.info("测试用户创建成功", user_id=test_user.id, username=test_user.username)
        
    except Exception as e:
        db.rollback()
        logger.error("插入测试数据失败", error=str(e), exc_info=True)
        raise DatabaseError(f"插入测试数据失败: {str(e)}")
    finally:
        db.close()


def main():
    """
    主函数
    """
    print("\n" + "=" * 60)
    print("Agent 项目数据库完整初始化")
    print("=" * 60 + "\n")
    
    try:
        # 步骤1: 创建数据库（如果不存在）
        print("步骤 1/5: 检查并创建数据库...")
        create_database_if_not_exists()
        print("✓ 数据库就绪\n")
        
        # 步骤2: 创建基础表
        print("步骤 2/5: 创建基础数据库表...")
        create_basic_tables()
        print("✓ 基础表创建完成\n")
        
        # 步骤3: 创建智能体系统表
        print("步骤 3/5: 创建智能体系统表...")
        create_agent_tables()
        print("✓ 智能体系统表创建完成\n")
        
        # 步骤4: 验证表创建
        print("步骤 4/5: 验证表创建...")
        if not verify_tables_created():
            raise DatabaseError("表创建验证失败")
        print("✓ 所有表验证通过\n")
        
        # 步骤5: 插入测试数据
        print("步骤 5/5: 插入测试数据...")
        insert_test_data()
        print("✓ 测试数据插入完成\n")
        
        print("=" * 60)
        print("✅ 数据库完整初始化完成！")
        print("=" * 60)
        print("\n数据库信息:")
        print(f"  - 数据库: {config.get('database.mysql.database')}")
        print(f"  - 主机: {config.get('database.mysql.host')}")
        print(f"  - 端口: {config.get('database.mysql.port')}")
        print(f"  - 基础表: user, conversation, message")
        print(f"  - 智能体表: task, memory_store, knowledge_graph, knowledge_relation")
        print(f"  - 测试用户: test_user")
        print()
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        logger.error("数据库初始化失败", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
