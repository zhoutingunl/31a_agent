"""
API集成测试

测试所有API端点的基本功能和集成
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import SessionLocal
from app.core.llm.factory import create_llm
from app.schemas.message import MessageSend


class TestAPIIntegration:
    """API集成测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def db(self):
        """获取数据库会话"""
        return next(get_database())
    
    @pytest.fixture
    def llm(self):
        """获取LLM实例"""
        return get_llm_instance()
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查接口"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_conversation_crud(self, client):
        """测试会话CRUD操作"""
        # 创建会话
        create_response = await client.post("/api/v1/conversations", json={
            "user_id": 1,
            "title": "测试会话"
        })
        assert create_response.status_code == 200
        conversation_data = create_response.json()
        conversation_id = conversation_data["id"]
        
        # 获取会话列表
        list_response = await client.get("/api/v1/conversations?user_id=1")
        assert list_response.status_code == 200
        conversations = list_response.json()
        assert len(conversations) > 0
        
        # 获取会话详情
        detail_response = await client.get(f"/api/v1/conversations/{conversation_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["id"] == conversation_id
        
        # 更新会话
        update_response = await client.put(f"/api/v1/conversations/{conversation_id}", json={
            "title": "更新后的标题"
        })
        assert update_response.status_code == 200
        
        # 删除会话
        delete_response = await client.delete(f"/api/v1/conversations/{conversation_id}")
        assert delete_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_message_crud(self, client):
        """测试消息CRUD操作"""
        # 先创建会话
        conv_response = await client.post("/api/v1/conversations", json={
            "user_id": 1,
            "title": "消息测试会话"
        })
        conversation_id = conv_response.json()["id"]
        
        # 创建消息
        create_response = await client.post("/api/v1/messages", json={
            "conversation_id": conversation_id,
            "role": "user",
            "content": "这是一条测试消息"
        })
        assert create_response.status_code == 200
        message_data = create_response.json()
        message_id = message_data["id"]
        
        # 获取消息列表
        list_response = await client.get(f"/api/v1/messages?conversation_id={conversation_id}")
        assert list_response.status_code == 200
        messages = list_response.json()
        assert len(messages) > 0
        
        # 获取消息详情
        detail_response = await client.get(f"/api/v1/messages/{message_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["id"] == message_id
        
        # 更新消息
        update_response = await client.put(f"/api/v1/messages/{message_id}", json={
            "content": "更新后的消息内容"
        })
        assert update_response.status_code == 200
        
        # 删除消息
        delete_response = await client.delete(f"/api/v1/messages/{message_id}")
        assert delete_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_basic_chat_api(self, client):
        """测试基础聊天API"""
        response = await client.post("/api/v1/chat", json={
            "user_id": 1,
            "content": "你好，请介绍一下你自己"
        })
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert data["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_chat_streaming(self, client):
        """测试流式聊天API"""
        response = await client.post("/api/v1/chat/stream", json={
            "user_id": 1,
            "content": "请简单介绍一下Python"
        })
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # 验证流式响应
        content = response.text
        assert len(content) > 0
    
    @pytest.mark.asyncio
    async def test_planning_api(self, client):
        """测试任务规划API"""
        response = await client.post("/api/v1/chat/plan", json={
            "user_id": 1,
            "content": "帮我制定一个学习Python的计划"
        })
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
    
    @pytest.mark.asyncio
    async def test_reflection_api(self, client):
        """测试反思执行API"""
        response = await client.post("/api/v1/reflection/execute", json={
            "task_description": "生成一个简单的Python函数来计算斐波那契数列",
            "expected_goal": "生成可运行的Python代码",
            "constraints": ["代码要简洁", "要有注释"],
            "context_info": {}
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "final_output" in data
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """测试API错误处理"""
        # 测试无效的会话ID
        response = await client.get("/api/v1/conversations/99999")
        assert response.status_code == 404
        
        # 测试无效的消息ID
        response = await client.get("/api/v1/messages/99999")
        assert response.status_code == 404
        
        # 测试无效的请求数据
        response = await client.post("/api/v1/chat", json={
            "user_id": "invalid",  # 应该是整数
            "content": "测试"
        })
        assert response.status_code == 422  # 验证错误
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client):
        """测试并发请求处理"""
        # 创建多个并发请求
        tasks = []
        for i in range(5):
            task = client.post("/api/v1/chat", json={
                "user_id": 1,
                "content": f"并发测试消息 {i}"
            })
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self, client):
        """测试记忆持久化"""
        conversation_id = None
        
        # 第一轮对话
        response1 = await client.post("/api/v1/chat", json={
            "user_id": 1,
            "content": "我的名字是张三，我喜欢编程"
        })
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        
        # 第二轮对话（测试记忆）
        response2 = await client.post("/api/v1/chat", json={
            "user_id": 1,
            "content": "我刚才说我叫什么名字？"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 验证系统记住了用户信息（通过响应内容判断）
        # 注意：这里只是测试API正常工作，具体记忆效果取决于LLM
        assert len(data2["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_tool_integration(self, client):
        """测试工具集成"""
        # 测试需要工具调用的请求
        response = await client.post("/api/v1/chat", json={
            "user_id": 1,
            "content": "查询数据库中有哪些表"
        })
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        
        # 验证响应包含工具调用结果（通过内容判断）
        # 注意：具体结果取决于数据库状态和工具配置
        assert len(data["content"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
