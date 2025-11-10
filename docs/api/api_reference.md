# API参考文档

## 概述

Agent智能体系统提供完整的RESTful API接口，支持多角色对话、任务规划、反思执行、记忆管理等功能。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1
- **认证方式**: 无需认证（开发环境）
- **数据格式**: JSON
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": {
    // 具体数据内容
  },
  "message": "操作成功",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": "详细错误信息"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 错误码说明

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `VALIDATION_ERROR` | 422 | 请求参数验证失败 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 健康检查

### 获取系统状态

```http
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "llm": "healthy"
  }
}
```

## 基础聊天API

### 发送消息

```http
POST /api/v1/chat
```

**请求参数**:
```json
{
  "user_id": 1,
  "content": "你好，请介绍一下你自己"
}
```

**响应示例**:
```json
{
  "conversation_id": 123,
  "message_id": 456,
  "content": "你好！我是一个AI智能助手...",
  "role": "assistant",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### 流式聊天

```http
POST /api/v1/chat/stream
```

**请求参数**: 同基础聊天API

**响应**: 流式文本响应，Content-Type: `text/plain`

## 角色专属API

### 通用助手

#### 发送消息

```http
POST /api/v1/general/chat
```

**请求参数**:
```json
{
  "user_id": 1,
  "content": "请帮我写一个Python函数"
}
```

**响应示例**:
```json
{
  "conversation_id": 123,
  "message_id": 456,
  "content": "好的，我来帮你写一个Python函数...",
  "role": "assistant",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 获取角色信息

```http
GET /api/v1/general/info
```

**响应示例**:
```json
{
  "role_name": "通用助手",
  "description": "一个通用的AI助手，能够处理各种任务",
  "capabilities": [
    "代码生成",
    "问题解答",
    "任务规划",
    "数据分析"
  ],
  "memory_strategy": "long_term",
  "tool_permissions": ["all"]
}
```

### 电商客服

#### 发送消息

```http
POST /api/v1/customer_service/chat
```

**请求参数**:
```json
{
  "user_id": 1,
  "content": "我想查询我的订单状态"
}
```

**响应示例**:
```json
{
  "conversation_id": 123,
  "message_id": 456,
  "content": "好的，请提供您的订单号，我来帮您查询...",
  "role": "assistant",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 获取角色信息

```http
GET /api/v1/customer_service/info
```

**响应示例**:
```json
{
  "role_name": "电商客服",
  "description": "专业的电商客服助手，处理订单、退换货等问题",
  "capabilities": [
    "订单查询",
    "退换货处理",
    "产品咨询",
    "投诉处理"
  ],
  "memory_strategy": "short_term",
  "tool_permissions": ["order_query", "product_info"]
}
```

## 任务规划API

### 创建任务计划

```http
POST /api/v1/chat/plan
```

**请求参数**:
```json
{
  "user_id": 1,
  "content": "帮我制定一个学习Python的计划"
}
```

**响应示例**:
```json
{
  "conversation_id": 123,
  "message_id": 456,
  "content": "我来为您制定一个详细的Python学习计划...",
  "role": "assistant",
  "plan": {
    "id": "plan_001",
    "title": "Python学习计划",
    "steps": [
      {
        "id": "step_1",
        "title": "基础语法学习",
        "description": "学习Python基础语法",
        "estimated_time": "2周",
        "dependencies": []
      },
      {
        "id": "step_2",
        "title": "面向对象编程",
        "description": "学习类和对象",
        "estimated_time": "1周",
        "dependencies": ["step_1"]
      }
    ],
    "total_estimated_time": "3周"
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 反思执行API

### 执行反思任务

```http
POST /api/v1/reflection/execute
```

**请求参数**:
```json
{
  "task_description": "生成一个简单的Python函数来计算斐波那契数列",
  "expected_goal": "生成可运行的Python代码",
  "constraints": [
    "代码要简洁",
    "要有详细注释",
    "包含错误处理"
  ],
  "context_info": {
    "user_level": "beginner",
    "preferred_style": "functional"
  }
}
```

**响应示例**:
```json
{
  "success": true,
  "task_id": "task_001",
  "execution_steps": [
    {
      "step": 1,
      "action": "代码生成",
      "result": "生成了基础斐波那契函数",
      "quality_score": 8.5
    },
    {
      "step": 2,
      "action": "代码优化",
      "result": "添加了错误处理和注释",
      "quality_score": 9.2
    }
  ],
  "final_output": "def fibonacci(n):\n    \"\"\"计算斐波那契数列的第n项\"\"\"\n    if n < 0:\n        raise ValueError(\"n必须为非负整数\")\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "quality_score": 9.2,
  "execution_time": 2.5,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 会话管理API

### 创建会话

```http
POST /api/v1/conversations
```

**请求参数**:
```json
{
  "user_id": 1,
  "title": "Python学习讨论"
}
```

**响应示例**:
```json
{
  "id": 123,
  "user_id": 1,
  "title": "Python学习讨论",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### 获取会话列表

```http
GET /api/v1/conversations?user_id=1&page=1&size=10
```

**查询参数**:
- `user_id` (必需): 用户ID
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认10

**响应示例**:
```json
{
  "conversations": [
    {
      "id": 123,
      "user_id": 1,
      "title": "Python学习讨论",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "message_count": 5
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

### 获取会话详情

```http
GET /api/v1/conversations/{conversation_id}
```

**路径参数**:
- `conversation_id`: 会话ID

**响应示例**:
```json
{
  "id": 123,
  "user_id": 1,
  "title": "Python学习讨论",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "messages": [
    {
      "id": 456,
      "role": "user",
      "content": "你好",
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": 457,
      "role": "assistant",
      "content": "你好！有什么可以帮助您的吗？",
      "created_at": "2024-01-01T12:00:01Z"
    }
  ]
}
```

### 更新会话

```http
PUT /api/v1/conversations/{conversation_id}
```

**请求参数**:
```json
{
  "title": "更新后的标题"
}
```

**响应示例**:
```json
{
  "id": 123,
  "user_id": 1,
  "title": "更新后的标题",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:00Z"
}
```

### 删除会话

```http
DELETE /api/v1/conversations/{conversation_id}
```

**响应示例**:
```json
{
  "message": "会话删除成功"
}
```

## 消息管理API

### 创建消息

```http
POST /api/v1/messages
```

**请求参数**:
```json
{
  "conversation_id": 123,
  "role": "user",
  "content": "这是一条测试消息"
}
```

**响应示例**:
```json
{
  "id": 456,
  "conversation_id": 123,
  "role": "user",
  "content": "这是一条测试消息",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### 获取消息列表

```http
GET /api/v1/messages?conversation_id=123&page=1&size=20
```

**查询参数**:
- `conversation_id` (必需): 会话ID
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认20

**响应示例**:
```json
{
  "messages": [
    {
      "id": 456,
      "conversation_id": 123,
      "role": "user",
      "content": "你好",
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": 457,
      "conversation_id": 123,
      "role": "assistant",
      "content": "你好！有什么可以帮助您的吗？",
      "created_at": "2024-01-01T12:00:01Z"
    }
  ],
  "total": 2,
  "page": 1,
  "size": 20
}
```

### 获取消息详情

```http
GET /api/v1/messages/{message_id}
```

**路径参数**:
- `message_id`: 消息ID

**响应示例**:
```json
{
  "id": 456,
  "conversation_id": 123,
  "role": "user",
  "content": "你好",
  "created_at": "2024-01-01T12:00:00Z",
  "metadata": {
    "execution_mode": "simple",
    "execution_time": 1.2,
    "state_history": [
      {
        "from_state": "IDLE",
        "to_state": "ROUTING",
        "timestamp": "2024-01-01T12:00:00Z"
      }
    ]
  }
}
```

### 更新消息

```http
PUT /api/v1/messages/{message_id}
```

**请求参数**:
```json
{
  "content": "更新后的消息内容"
}
```

**响应示例**:
```json
{
  "id": 456,
  "conversation_id": 123,
  "role": "user",
  "content": "更新后的消息内容",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:05:00Z"
}
```

### 删除消息

```http
DELETE /api/v1/messages/{message_id}
```

**响应示例**:
```json
{
  "message": "消息删除成功"
}
```

## 记忆管理API

### 获取记忆列表

```http
GET /api/v1/memories?user_id=1&memory_type=long_term&page=1&size=10
```

**查询参数**:
- `user_id` (必需): 用户ID
- `memory_type` (可选): 记忆类型 (`short_term`, `long_term`, `knowledge_graph`)
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认10

**响应示例**:
```json
{
  "memories": [
    {
      "id": 789,
      "user_id": 1,
      "memory_type": "long_term",
      "content": "用户喜欢Python编程",
      "importance_score": 8.5,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

### 获取记忆详情

```http
GET /api/v1/memories/{memory_id}
```

**路径参数**:
- `memory_id`: 记忆ID

**响应示例**:
```json
{
  "id": 789,
  "user_id": 1,
  "memory_type": "long_term",
  "content": "用户喜欢Python编程",
  "importance_score": 8.5,
  "metadata": {
    "source_conversation_id": 123,
    "extracted_entities": ["Python", "编程"],
    "tags": ["兴趣", "技能"]
  },
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### 更新记忆重要性

```http
PUT /api/v1/memories/{memory_id}/importance
```

**请求参数**:
```json
{
  "importance_score": 9.0
}
```

**响应示例**:
```json
{
  "id": 789,
  "importance_score": 9.0,
  "updated_at": "2024-01-01T12:05:00Z"
}
```

### 删除记忆

```http
DELETE /api/v1/memories/{memory_id}
```

**响应示例**:
```json
{
  "message": "记忆删除成功"
}
```

## 知识图谱API

### 获取实体列表

```http
GET /api/v1/knowledge/entities?user_id=1&entity_type=person&page=1&size=10
```

**查询参数**:
- `user_id` (必需): 用户ID
- `entity_type` (可选): 实体类型 (`person`, `organization`, `concept`, `skill`)
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认10

**响应示例**:
```json
{
  "entities": [
    {
      "id": 101,
      "user_id": 1,
      "entity_name": "张三",
      "entity_type": "person",
      "description": "用户的同事",
      "properties": {
        "department": "技术部",
        "position": "软件工程师"
      },
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

### 获取关系列表

```http
GET /api/v1/knowledge/relations?user_id=1&relation_type=works_with&page=1&size=10
```

**查询参数**:
- `user_id` (必需): 用户ID
- `relation_type` (可选): 关系类型 (`works_with`, `manages`, `knows`, `interested_in`)
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认10

**响应示例**:
```json
{
  "relations": [
    {
      "id": 201,
      "user_id": 1,
      "from_entity_id": 101,
      "to_entity_id": 102,
      "relation_type": "works_with",
      "description": "张三与李四一起工作",
      "confidence_score": 0.9,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

### 知识图谱查询

```http
POST /api/v1/knowledge/query
```

**请求参数**:
```json
{
  "user_id": 1,
  "query": "张三在哪个部门工作？",
  "query_type": "entity_property"
}
```

**响应示例**:
```json
{
  "query": "张三在哪个部门工作？",
  "results": [
    {
      "entity": "张三",
      "property": "department",
      "value": "技术部",
      "confidence": 0.9
    }
  ],
  "reasoning_path": [
    "找到实体：张三",
    "查询属性：department",
    "返回结果：技术部"
  ]
}
```

## 工具管理API

### 获取可用工具列表

```http
GET /api/v1/tools
```

**响应示例**:
```json
{
  "tools": [
    {
      "name": "database_query",
      "description": "查询数据库",
      "parameters": {
        "sql": {
          "type": "string",
          "description": "SQL查询语句",
          "required": true
        }
      },
      "permissions": ["admin", "developer"]
    },
    {
      "name": "file_operations",
      "description": "文件操作",
      "parameters": {
        "operation": {
          "type": "string",
          "enum": ["read", "write", "delete"],
          "description": "操作类型",
          "required": true
        },
        "path": {
          "type": "string",
          "description": "文件路径",
          "required": true
        }
      },
      "permissions": ["admin"]
    }
  ]
}
```

### 执行工具

```http
POST /api/v1/tools/execute
```

**请求参数**:
```json
{
  "tool_name": "database_query",
  "parameters": {
    "sql": "SELECT * FROM users LIMIT 10"
  }
}
```

**响应示例**:
```json
{
  "tool_name": "database_query",
  "success": true,
  "result": [
    {
      "id": 1,
      "name": "张三",
      "email": "zhangsan@example.com"
    },
    {
      "id": 2,
      "name": "李四",
      "email": "lisi@example.com"
    }
  ],
  "execution_time": 0.5,
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 系统管理API

### 获取系统统计

```http
GET /api/v1/admin/stats
```

**响应示例**:
```json
{
  "users": {
    "total": 100,
    "active_today": 25
  },
  "conversations": {
    "total": 500,
    "created_today": 15
  },
  "messages": {
    "total": 2000,
    "sent_today": 150
  },
  "memories": {
    "total": 1000,
    "short_term": 300,
    "long_term": 500,
    "knowledge_graph": 200
  },
  "system": {
    "uptime": "7 days, 12 hours",
    "memory_usage": "2.5GB",
    "cpu_usage": "45%"
  }
}
```

### 获取系统日志

```http
GET /api/v1/admin/logs?level=ERROR&page=1&size=50
```

**查询参数**:
- `level` (可选): 日志级别 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `page` (可选): 页码，默认1
- `size` (可选): 每页大小，默认50

**响应示例**:
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "ERROR",
      "logger": "app.core.orchestrator",
      "message": "数据库连接失败",
      "details": "Connection timeout after 30 seconds"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 50
}
```

## 使用示例

### Python客户端示例

```python
import requests
import json

class AgentClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def chat(self, user_id, content):
        """发送聊天消息"""
        response = self.session.post(
            f"{self.base_url}/api/v1/chat",
            json={"user_id": user_id, "content": content}
        )
        return response.json()
    
    def get_conversations(self, user_id, page=1, size=10):
        """获取会话列表"""
        response = self.session.get(
            f"{self.base_url}/api/v1/conversations",
            params={"user_id": user_id, "page": page, "size": size}
        )
        return response.json()
    
    def create_conversation(self, user_id, title):
        """创建会话"""
        response = self.session.post(
            f"{self.base_url}/api/v1/conversations",
            json={"user_id": user_id, "title": title}
        )
        return response.json()

# 使用示例
client = AgentClient()

# 发送消息
response = client.chat(1, "你好，请介绍一下你自己")
print(response["content"])

# 获取会话列表
conversations = client.get_conversations(1)
print(f"共有 {conversations['total']} 个会话")
```

### JavaScript客户端示例

```javascript
class AgentClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async chat(userId, content) {
        const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                content: content
            })
        });
        return await response.json();
    }
    
    async getConversations(userId, page = 1, size = 10) {
        const response = await fetch(
            `${this.baseUrl}/api/v1/conversations?user_id=${userId}&page=${page}&size=${size}`
        );
        return await response.json();
    }
    
    async createConversation(userId, title) {
        const response = await fetch(`${this.baseUrl}/api/v1/conversations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                title: title
            })
        });
        return await response.json();
    }
}

// 使用示例
const client = new AgentClient();

// 发送消息
client.chat(1, "你好，请介绍一下你自己")
    .then(response => console.log(response.content));

// 获取会话列表
client.getConversations(1)
    .then(conversations => console.log(`共有 ${conversations.total} 个会话`));
```

### cURL示例

```bash
# 发送聊天消息
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "content": "你好，请介绍一下你自己"
  }'

# 获取会话列表
curl "http://localhost:8000/api/v1/conversations?user_id=1&page=1&size=10"

# 创建会话
curl -X POST "http://localhost:8000/api/v1/conversations" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "测试会话"
  }'

# 获取健康状态
curl "http://localhost:8000/health"
```

## 错误处理

### 常见错误及解决方案

#### 1. 参数验证错误 (422)

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "user_id",
        "message": "user_id必须是正整数"
      }
    ]
  }
}
```

**解决方案**: 检查请求参数格式和类型

#### 2. 资源不存在 (404)

```json
{
  "success": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "会话不存在",
    "details": "conversation_id: 999"
  }
}
```

**解决方案**: 确认资源ID是否正确

#### 3. 服务不可用 (503)

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "LLM服务暂时不可用",
    "details": "DeepSeek API连接超时"
  }
}
```

**解决方案**: 稍后重试或检查服务状态

## 最佳实践

### 1. 请求频率控制

- 建议请求间隔不少于100ms
- 避免并发请求过多
- 使用连接池复用连接

### 2. 错误重试

```python
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session_with_retry():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

### 3. 分页处理

```python
def get_all_conversations(user_id):
    conversations = []
    page = 1
    size = 100
    
    while True:
        response = client.get_conversations(user_id, page, size)
        conversations.extend(response["conversations"])
        
        if len(response["conversations"]) < size:
            break
        page += 1
    
    return conversations
```

### 4. 流式响应处理

```python
def stream_chat(user_id, content):
    response = requests.post(
        f"{base_url}/api/v1/chat/stream",
        json={"user_id": user_id, "content": content},
        stream=True
    )
    
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            print(chunk.decode('utf-8'), end='')
```

## 版本更新

### API版本管理

- 当前版本: v1
- 版本兼容性: 向后兼容
- 废弃通知: 提前30天通知

### 更新日志

#### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基础聊天功能
- 支持多角色对话
- 支持任务规划和反思执行
- 支持记忆管理和知识图谱

## 联系支持

如有问题或建议，请联系：

- **邮箱**: support@agent-system.com
- **文档**: https://docs.agent-system.com
- **GitHub**: https://github.com/agent-system/api
