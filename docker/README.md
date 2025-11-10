# Docker部署指南

## 概述

本指南介绍如何使用Docker部署Agent智能体系统。

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少4GB可用内存
- 至少10GB可用磁盘空间

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd agent-system
```

### 2. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量：

```bash
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 数据库配置（可选，默认使用docker-compose中的配置）
DATABASE_URL=mysql+pymysql://agent_user:agent_password@db:3306/agent_db

# 应用配置
APP_NAME=Agent系统
APP_VERSION=1.0.0
LOG_LEVEL=INFO
```

### 3. 启动服务

#### 开发环境

```bash
# 启动基础服务（应用+数据库）
docker-compose up -d app db

# 查看日志
docker-compose logs -f app
```

#### 生产环境

```bash
# 启动完整服务（包括Nginx）
docker-compose --profile production up -d

# 查看所有服务状态
docker-compose ps
```

### 4. 验证部署

访问以下地址验证服务：

- **应用服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 服务说明

### 应用服务 (app)

- **端口**: 8000
- **功能**: 主要的Agent系统服务
- **依赖**: MySQL数据库

### 数据库服务 (db)

- **端口**: 3306
- **类型**: MySQL 8.0
- **数据库**: agent_db
- **用户**: agent_user
- **密码**: agent_password

### Redis服务 (redis)

- **端口**: 6379
- **功能**: 会话缓存（可选）
- **用途**: 提高性能

### Nginx服务 (nginx)

- **端口**: 80, 443
- **功能**: 反向代理和负载均衡
- **用途**: 生产环境使用

## 数据持久化

以下数据会被持久化存储：

- **MySQL数据**: `mysql_data` 卷
- **FAISS索引**: `faiss_data` 卷
- **嵌入缓存**: `embedding_data` 卷
- **应用日志**: `app_logs` 卷
- **Redis数据**: `redis_data` 卷

## 常用命令

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d app db

# 前台运行（查看日志）
docker-compose up
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs app

# 实时查看日志
docker-compose logs -f app
```

### 进入容器

```bash
# 进入应用容器
docker-compose exec app bash

# 进入数据库容器
docker-compose exec db mysql -u agent_user -p agent_db
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接URL | mysql+pymysql://agent_user:agent_password@db:3306/agent_db |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | 必需 |
| `DEEPSEEK_BASE_URL` | DeepSeek API地址 | https://api.deepseek.com |
| `APP_NAME` | 应用名称 | Agent系统 |
| `APP_VERSION` | 应用版本 | 1.0.0 |
| `LOG_LEVEL` | 日志级别 | INFO |

### 端口配置

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| app | 8000 | 8000 | 应用服务 |
| db | 3306 | 3306 | MySQL数据库 |
| redis | 6379 | 6379 | Redis缓存 |
| nginx | 80/443 | 80/443 | Web服务器 |

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库服务状态
   docker-compose ps db
   
   # 查看数据库日志
   docker-compose logs db
   ```

2. **应用启动失败**
   ```bash
   # 查看应用日志
   docker-compose logs app
   
   # 检查环境变量
   docker-compose exec app env | grep DATABASE_URL
   ```

3. **端口冲突**
   ```bash
   # 修改docker-compose.yml中的端口映射
   ports:
     - "8001:8000"  # 改为其他端口
   ```

### 日志位置

- **应用日志**: `/app/logs/` (容器内)
- **数据库日志**: Docker日志
- **Nginx日志**: Docker日志

### 性能优化

1. **增加工作进程**
   ```yaml
   # 在docker-compose.yml中修改
   command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **调整数据库连接池**
   ```bash
   # 在环境变量中设置
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=30
   ```

## 生产环境部署

### 安全配置

1. **修改默认密码**
   ```yaml
   # 在docker-compose.yml中修改
   environment:
     - MYSQL_ROOT_PASSWORD=your_secure_password
     - MYSQL_PASSWORD=your_secure_password
   ```

2. **使用HTTPS**
   ```bash
   # 配置SSL证书
   mkdir -p docker/ssl
   # 将证书文件放入docker/ssl目录
   ```

3. **限制网络访问**
   ```yaml
   # 在docker-compose.yml中添加
   networks:
     agent-network:
       driver: bridge
       internal: true  # 限制外部访问
   ```

### 监控和备份

1. **健康检查**
   ```bash
   # 检查服务健康状态
   curl http://localhost:8000/health
   ```

2. **数据备份**
   ```bash
   # 备份数据库
   docker-compose exec db mysqldump -u agent_user -p agent_db > backup.sql
   
   # 备份数据卷
   docker run --rm -v agent_mysql_data:/data -v $(pwd):/backup alpine tar czf /backup/mysql_backup.tar.gz /data
   ```

## 更新和维护

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build app

# 重启服务
docker-compose up -d app
```

### 清理资源

```bash
# 清理未使用的镜像
docker image prune

# 清理未使用的数据卷
docker volume prune

# 清理所有未使用的资源
docker system prune -a
```
