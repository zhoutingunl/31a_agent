#!/bin/bash

# 容器启动脚本
# 用于初始化数据库、启动应用等

set -e

echo "=== Agent系统容器启动 ==="

# 等待数据库就绪
echo "等待数据库连接..."
python -c "
import time
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        engine = create_engine('${DATABASE_URL}')
        with engine.connect() as conn:
            conn.execute('SELECT 1')
        print('数据库连接成功!')
        break
    except OperationalError as e:
        retry_count += 1
        print(f'数据库连接失败 (尝试 {retry_count}/{max_retries}): {e}')
        if retry_count >= max_retries:
            print('数据库连接超时，退出')
            sys.exit(1)
        time.sleep(2)
"

# 初始化数据库
echo "初始化数据库..."
python scripts/init_db.py

# 创建必要的目录
echo "创建数据目录..."
mkdir -p /app/data/faiss
mkdir -p /app/data/embeddings
mkdir -p /app/logs

# 设置权限
chmod 755 /app/data/faiss
chmod 755 /app/data/embeddings
chmod 755 /app/logs

# 启动应用
echo "启动Agent系统..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --access-log \
    --log-level info
