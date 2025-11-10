# MCP 工具开发指南

> 如何为 Agent 添加 MCP (Model Context Protocol) 工具

---

## 📋 添加新 MCP 工具的步骤

### 步骤1：编辑 MCP 配置文件

**配置文件位置**：项目根目录下的 `mcp.json`

**当前配置**：
```json
{
  "mcpServers": {
    "mysql": {
      "command": "npx",
      "args": ["-y", "@data_wise/database-mcp"],
      "env": {
        "DB_TYPE": "mysql",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "123456",
        "DB_NAME": "agent_db",
        "DB_CHARSET": "utf8mb4"
      }
    }
  }
}
```

**可选的 MCP 服务器示例**（暂时注释）：
```json
{
  "mcpServers": {
    "mysql": {...},
    
    // 以下是可选的 MCP 服务器，需要时可以取消注释
    /*
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", 
               "postgresql://user:pass@host:port/database"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp", "--api-key", "your-key"]
    }
    */
  }
}
```

### 步骤2：添加新的 MCP 服务器

只需在 `mcpServers` 中添加新的配置：

```json
{
  "mcpServers": {
    // ... 现有配置 ...
    
    "新服务器名称": {
      "command": "npx",              // 启动命令
      "args": [                      // 命令参数
        "-y",                        // 自动确认安装
        "@包名/mcp-服务器"            // npm 包名
      ],
      "env": {                       // 环境变量（可选）
        "API_KEY": "your-api-key",
        "CONFIG": "value"
      }
    }
  }
}
```

### 步骤3：重启 Agent 服务

```bash
# 停止旧服务
Get-Job | Stop-Job

# 重启服务
python scripts/run_dev.py
```

**完成！** 新工具会自动加载并可用。

---

## 📚 常用 MCP 工具示例

### 数据库工具
```json
"mysql": {
  "command": "npx",
  "args": ["-y", "@data_wise/database-mcp"],
  "env": {
    "DB_TYPE": "mysql",
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "3306",
    "DB_USER": "root",
    "DB_PASSWORD": "123456",
    "DB_NAME": "agent_db"
  }
}
```

### 文件系统工具
```json
"filesystem": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
}
```

### GitHub 集成
```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_TOKEN": "your-github-token"
  }
}
```

---

## ⚙️ 配置说明

### 必需字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `command` | 启动命令 | `"npx"` |
| `args` | 命令参数（数组） | `["-y", "@pkg/mcp"]` |

### 可选字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `env` | 环境变量 | `{"API_KEY": "xxx"}` |

---

## 🧪 测试 MCP 工具

### 运行测试脚本
```bash
python scripts/test_mcp_integration.py
```

### 在对话中测试
```
用户: 请列出 MySQL 数据库中的所有表
Agent: (自动调用 mcp_mysql_listTables 工具)
```

---

## ⚠️ 注意事项

### 需要 Node.js 环境
MCP 工具需要 Node.js，安装后验证：`node --version`

### 环境变量安全
- 不要将敏感信息提交到 Git
- 使用 `mcp.json.example` 作为模板
- `mcp.json` 已被 `.gitignore` 忽略

### 工具命名
MCP 工具会自动添加 `mcp_` 前缀，避免与自定义工具冲突

---

## 📖 相关文档

- **添加自定义工具**：`docs/添加新工具指南.md`
- **项目架构**：`docs/项目架构.md`
- **MCP 官方文档**：https://modelcontextprotocol.io


