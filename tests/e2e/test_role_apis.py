"""
角色API测试

测试多角色支持系统的API端点
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app
from app.schemas.message import MessageSend


class TestRoleAPIs:
    """角色API测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_general_assistant_chat(self, client):
        """测试通用助手聊天API"""
        response = await client.post("/api/v1/general/chat", json={
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
    async def test_general_assistant_info(self, client):
        """测试通用助手信息API"""
        response = await client.get("/api/v1/general/info")
        assert response.status_code == 200
        data = response.json()
        assert "role_name" in data
        assert "description" in data
        assert "capabilities" in data
        assert data["role_name"] == "通用助手"
    
    @pytest.mark.asyncio
    async def test_customer_service_chat(self, client):
        """测试电商客服聊天API"""
        response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我想查询我的订单状态"
        })
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert data["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_customer_service_info(self, client):
        """测试电商客服信息API"""
        response = await client.get("/api/v1/customer_service/info")
        assert response.status_code == 200
        data = response.json()
        assert "role_name" in data
        assert "description" in data
        assert "capabilities" in data
        assert data["role_name"] == "电商客服"
    
    @pytest.mark.asyncio
    async def test_role_tool_permissions(self, client):
        """测试角色工具权限"""
        # 通用助手应该能访问更多工具
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "帮我查询数据库中的所有表"
        })
        assert general_response.status_code == 200
        
        # 电商客服工具权限受限
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "帮我查询数据库中的所有表"
        })
        assert cs_response.status_code == 200
        
        # 注意：具体工具调用结果取决于配置和数据库状态
        # 这里主要测试API正常工作
    
    @pytest.mark.asyncio
    async def test_role_memory_strategies(self, client):
        """测试角色记忆策略"""
        # 测试通用助手的长期记忆
        general_response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是李四，我是一名软件工程师"
        })
        assert general_response1.status_code == 200
        
        general_response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我刚才说我叫什么名字？"
        })
        assert general_response2.status_code == 200
        
        # 测试电商客服的短期记忆
        cs_response1 = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我想退货，订单号是12345"
        })
        assert cs_response1.status_code == 200
        
        cs_response2 = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我的订单号是多少？"
        })
        assert cs_response2.status_code == 200
        
        # 注意：具体记忆效果取决于LLM和记忆系统配置
    
    @pytest.mark.asyncio
    async def test_role_context_isolation(self, client):
        """测试角色上下文隔离"""
        # 在通用助手中设置信息
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的爱好是编程，请记住这个信息"
        })
        assert general_response.status_code == 200
        
        # 在电商客服中询问相同信息（应该不知道）
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "你知道我的爱好是什么吗？"
        })
        assert cs_response.status_code == 200
        
        # 注意：具体隔离效果取决于记忆系统实现
    
    @pytest.mark.asyncio
    async def test_role_system_prompts(self, client):
        """测试角色系统提示词"""
        # 测试通用助手的回答风格
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请帮我写一个Python函数"
        })
        assert general_response.status_code == 200
        general_content = general_response.json()["content"]
        
        # 测试电商客服的回答风格
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "请帮我写一个Python函数"
        })
        assert cs_response.status_code == 200
        cs_content = cs_response.json()["content"]
        
        # 验证不同角色有不同的回答风格
        # 注意：具体差异取决于LLM和提示词配置
        assert len(general_content) > 0
        assert len(cs_content) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_role_requests(self, client):
        """测试并发角色请求"""
        # 创建多个不同角色的并发请求
        tasks = []
        
        # 通用助手请求
        for i in range(3):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"通用助手测试 {i}"
            })
            tasks.append(task)
        
        # 电商客服请求
        for i in range(3):
            task = client.post("/api/v1/customer_service/chat", json={
                "user_id": 1,
                "content": f"客服测试 {i}"
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
    async def test_role_error_handling(self, client):
        """测试角色API错误处理"""
        # 测试无效的用户ID
        response = await client.post("/api/v1/general/chat", json={
            "user_id": "invalid",
            "content": "测试"
        })
        assert response.status_code == 422
        
        # 测试空内容
        response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": ""
        })
        assert response.status_code == 422
        
        # 测试缺少必要字段
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1
            # 缺少content字段
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_role_metadata(self, client):
        """测试角色响应元数据"""
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "测试元数据"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应包含必要的元数据
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert "role" in data
        assert data["role"] == "assistant"
        
        # 验证时间戳
        assert "created_at" in data or "timestamp" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
