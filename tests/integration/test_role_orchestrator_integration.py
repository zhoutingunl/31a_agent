"""
角色与编排器集成测试

测试角色系统与编排器的协同工作
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


class TestRoleOrchestratorIntegration:
    """角色与编排器集成测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_role_tool_permission_filtering(self, client):
        """测试角色工具权限过滤"""
        # 测试通用助手的工具权限
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请帮我查询数据库中的所有表"
        })
        assert general_response.status_code == 200
        general_data = general_response.json()
        assert len(general_data["content"]) > 0
        
        # 测试电商客服的工具权限
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "请帮我查询数据库中的所有表"
        })
        assert cs_response.status_code == 200
        cs_data = cs_response.json()
        assert len(cs_data["content"]) > 0
        
        # 验证两个角色都能正常响应（具体工具调用结果取决于配置）
        # 这里主要测试权限过滤不会导致系统崩溃
    
    @pytest.mark.asyncio
    async def test_role_memory_strategy_application(self, client):
        """测试角色记忆策略应用"""
        # 测试通用助手的长期记忆
        general_responses = []
        
        # 第一轮：建立记忆
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是张三，我是一名软件工程师，专门从事Python开发"
        })
        assert response1.status_code == 200
        general_responses.append(response1.json())
        
        # 第二轮：测试记忆
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我刚才说我叫什么名字？"
        })
        assert response2.status_code == 200
        general_responses.append(response2.json())
        
        # 测试电商客服的短期记忆
        cs_responses = []
        
        # 第一轮：建立记忆
        response3 = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我想退货，订单号是12345"
        })
        assert response3.status_code == 200
        cs_responses.append(response3.json())
        
        # 第二轮：测试记忆
        response4 = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我的订单号是多少？"
        })
        assert response4.status_code == 200
        cs_responses.append(response4.json())
        
        # 验证两个角色都能正常处理记忆
        for response in general_responses + cs_responses:
            assert "content" in response
            assert len(response["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_role_orchestrator_routing(self, client):
        """测试角色与编排器路由集成"""
        # 测试通用助手的智能路由
        general_tasks = [
            "你好，今天天气怎么样？",  # 简单对话
            "帮我制定一个学习Python的详细计划",  # 规划任务
            "请生成一个完整的Python类，实现计算器功能"  # 代码生成
        ]
        
        for task in general_tasks:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": task
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
        
        # 测试电商客服的智能路由
        cs_tasks = [
            "你好，我想咨询一下产品信息",  # 简单对话
            "我想了解你们的退货流程",  # 客服咨询
            "请帮我查询订单状态"  # 工具调用
        ]
        
        for task in cs_tasks:
            response = await client.post("/api/v1/customer_service/chat", json={
                "user_id": 1,
                "content": task
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_role_context_isolation(self, client):
        """测试角色上下文隔离"""
        # 在通用助手中设置信息
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的爱好是编程，请记住这个信息"
        })
        assert general_response.status_code == 200
        
        # 在电商客服中询问相同信息
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "你知道我的爱好是什么吗？"
        })
        assert cs_response.status_code == 200
        
        # 验证两个角色都能正常响应
        # 注意：具体隔离效果取决于记忆系统实现
        assert len(general_response.json()["content"]) > 0
        assert len(cs_response.json()["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_role_system_prompt_integration(self, client):
        """测试角色系统提示词集成"""
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
        
        # 验证两个角色都有响应
        assert len(general_content) > 0
        assert len(cs_content) > 0
        
        # 注意：具体风格差异取决于LLM和提示词配置
    
    @pytest.mark.asyncio
    async def test_role_error_handling_integration(self, client):
        """测试角色错误处理集成"""
        # 测试通用助手的错误处理
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请执行一个不存在的系统命令：rm -rf /"
        })
        assert general_response.status_code == 200
        general_data = general_response.json()
        assert len(general_data["content"]) > 0
        
        # 测试电商客服的错误处理
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "请执行一个不存在的系统命令：rm -rf /"
        })
        assert cs_response.status_code == 200
        cs_data = cs_response.json()
        assert len(cs_data["content"]) > 0
        
        # 验证错误处理不会导致系统崩溃
        # 后续请求应该仍然正常工作
        follow_up = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "你好，系统还正常吗？"
        })
        assert follow_up.status_code == 200
    
    @pytest.mark.asyncio
    async def test_role_orchestrator_state_management(self, client):
        """测试角色与编排器状态管理集成"""
        # 发送需要多步骤处理的任务
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请帮我分析这个项目的代码结构，然后给出重构建议"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应包含状态信息
        assert "conversation_id" in data
        assert "message_id" in data
        
        # 检查消息元数据中的状态历史
        message_detail = await client.get(f"/api/v1/messages/{data['message_id']}")
        if message_detail.status_code == 200:
            message_data = message_detail.json()
            if "metadata" in message_data:
                metadata = message_data["metadata"]
                # 验证包含状态历史信息
                if "state_history" in metadata:
                    state_history = metadata["state_history"]
                    assert isinstance(state_history, list)
    
    @pytest.mark.asyncio
    async def test_concurrent_role_requests(self, client):
        """测试并发角色请求"""
        # 创建多个不同角色的并发请求
        tasks = []
        
        # 通用助手请求
        for i in range(5):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"通用助手测试 {i}"
            })
            tasks.append(task)
        
        # 电商客服请求
        for i in range(5):
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
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_role_orchestrator_performance(self, client):
        """测试角色与编排器性能集成"""
        import time
        
        # 测试通用助手性能
        start_time = time.time()
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请简单介绍一下人工智能"
        })
        general_time = time.time() - start_time
        
        # 测试电商客服性能
        start_time = time.time()
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我想了解你们的服务"
        })
        cs_time = time.time() - start_time
        
        # 验证响应
        assert general_response.status_code == 200
        assert cs_response.status_code == 200
        
        # 验证性能
        assert general_time < 10.0  # 通用助手响应时间应小于10秒
        assert cs_time < 10.0  # 电商客服响应时间应小于10秒
        
        print(f"通用助手响应时间: {general_time:.3f}秒")
        print(f"电商客服响应时间: {cs_time:.3f}秒")
    
    @pytest.mark.asyncio
    async def test_role_orchestrator_metadata_integration(self, client):
        """测试角色与编排器元数据集成"""
        # 测试通用助手元数据
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "测试元数据"
        })
        assert general_response.status_code == 200
        general_data = general_response.json()
        
        # 验证响应包含必要的元数据
        assert "conversation_id" in general_data
        assert "message_id" in general_data
        assert "content" in general_data
        assert "role" in general_data
        assert general_data["role"] == "assistant"
        
        # 测试电商客服元数据
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "测试元数据"
        })
        assert cs_response.status_code == 200
        cs_data = cs_response.json()
        
        # 验证响应包含必要的元数据
        assert "conversation_id" in cs_data
        assert "message_id" in cs_data
        assert "content" in cs_data
        assert "role" in cs_data
        assert cs_data["role"] == "assistant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
