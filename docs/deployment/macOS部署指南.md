# macOS 部署指南

## 🍎 macOS 环境下运行 31a_agent 项目

本指南详细说明了如何在 macOS 环境下安装和运行 31a_agent 智能对话助手项目。

---

## 📋 系统要求

- **操作系统**: macOS 10.14+ (推荐 macOS 12+)
- **Python**: 3.9+ (推荐 3.10+)
- **内存**: 至少 4GB RAM (推荐 8GB+)
- **存储**: 至少 2GB 可用空间
- **网络**: 稳定的互联网连接（用于 API 调用）

---

## 🛠️ 环境准备

### 1. 安装 Homebrew（如果尚未安装）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. 安装 Python

```bash
# 使用 Homebrew 安装 Python
brew install python@3.10

# 验证安装
python3 --version
```

### 3. 安装 MySQL（选择其中一种方式）

#### 方式1：使用 Homebrew 安装（推荐）

```bash
# 安装 MySQL
brew install mysql

# 启动 MySQL 服务
brew services start mysql

# 设置 root 密码（可选）
mysql_secure_installation
```

#### 方式2：使用 Docker 运行 MySQL

```bash
# 安装 Docker Desktop for Mac
# 下载地址: https://www.docker.com/products/docker-desktop

# 运行 MySQL 容器
docker run -d \
  --name mysql-agent \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=agent_db \
  -p 3306:3306 \
  mysql:8.0
```

---

## 📦 项目安装

### 1. 克隆项目

```bash
git clone https://github.com/zhoutingunl/31a_agent.git
cd 31a_agent
```

### 2. 创建虚拟环境

```bash
# 使用 venv 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 或者使用 conda
conda create -n agent python=3.10
conda activate agent
```

### 3. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 如果遇到安装问题，可以尝试更新 pip
pip install --upgrade pip setuptools wheel
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
# 或使用其他编辑器: vim .env, code .env
```

#### 主要配置项：

```env
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=agent_db

# 七牛云 API（推荐，按照问题描述使用七牛云提供的 sk_key）
QINIU_API_KEY=sk-your-qiniu-sk-key-here
QINIU_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 其他 LLM API（可选）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
TONGYI_API_KEY=your-tongyi-api-key
```

---

## 🚀 启动服务

### 1. 初始化数据库

```bash
# 创建数据库表和初始数据
python scripts/init_database.py
```

### 2. 启动服务器

```bash
# 方式1：使用启动脚本（推荐）
python scripts/start_server.py

# 方式2：直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 验证安装

访问以下地址确认服务正常运行：

- **Web 界面**: http://localhost:8000/
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🔧 macOS 特定配置

### 1. 权限配置

某些功能可能需要额外的系统权限：

```bash
# 允许终端访问（如果使用全局快捷键功能）
# 系统偏好设置 > 安全性与隐私 > 隐私 > 辅助功能
# 添加终端应用程序到允许列表
```

### 2. 防火墙设置

如果启用了 macOS 防火墙，需要允许 Python 应用程序接受传入连接：

1. 打开"系统偏好设置" > "安全性与隐私" > "防火墙"
2. 点击"防火墙选项"
3. 如果 Python 出现在列表中，确保设置为"允许传入连接"

### 3. 环境变量配置

macOS 项目已自动配置 UTF-8 编码，无需手动设置。如需自定义：

```bash
# 在 ~/.zshrc 或 ~/.bash_profile 中添加
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

---

## 🛑 停止服务

```bash
# 使用停止脚本
python scripts/stop_server.py

# 或手动终止进程
# 按 Ctrl+C 在运行的终端中停止服务

# 停止 MySQL 服务（如果使用 Homebrew 安装）
brew services stop mysql

# 停止 Docker MySQL 容器（如果使用 Docker）
docker stop mysql-agent
```

---

## 🔍 故障排除

### 常见问题

#### 1. MySQL 连接失败

**错误信息**: `Can't connect to MySQL server`

**解决方案**:
```bash
# 检查 MySQL 服务状态
brew services list | grep mysql

# 重启 MySQL 服务
brew services restart mysql

# 检查端口是否被占用
lsof -i :3306
```

#### 2. 依赖安装失败

**错误信息**: `error: Microsoft Visual C++ 14.0 is required`

**解决方案**:
```bash
# 安装 Xcode 命令行工具
xcode-select --install

# 更新 pip 和构建工具
pip install --upgrade pip setuptools wheel

# 重新安装依赖
pip install -r requirements.txt
```

#### 3. 端口占用问题

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 查找占用端口 8000 的进程
lsof -i :8000

# 终止占用进程
kill -9 PID_NUMBER

# 或使用项目提供的停止脚本
python scripts/stop_server.py
```

#### 4. API 密钥配置

确保在 `.env` 文件中正确配置了七牛云 API 密钥：

```env
# 七牛云 API 配置
QINIU_API_KEY=sk-your-actual-qiniu-key
QINIU_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 📚 更多资源

- [项目架构文档](../项目架构.md)
- [API 参考文档](../api/api_reference.md)
- [生产环境部署指南](生产环境部署指南.md)
- [Docker 部署指南](Docker部署指南.md)

---

## 💡 提示

- 建议使用 `conda` 或 `venv` 创建独立的 Python 环境
- 定期更新依赖包以获得最新功能和安全修复
- 在生产环境中，建议使用 Docker 部署以获得更好的稳定性
- 如遇到问题，请查看日志文件 `./logs/` 目录下的详细错误信息

---

*最后更新：2024年11月*