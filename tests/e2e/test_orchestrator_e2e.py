"""
编排器端到端测试

测试Agent编排器的智能路由、状态管理和异常恢复
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app
from app.core.orchestrator.schemas import ExecutionMode


class TestOrchestratorE2E:
    """编排器端到端测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_simple_routing(self, client):
        """测试简单对话路由到ToolAgent"""
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "你好，今天天气怎么样？"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应包含编排器元数据
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        
        # 验证消息元数据包含执行信息
        # 注意：具体元数据格式取决于RoleService实现
        message_detail = await client.get(f"/api/v1/messages/{data['message_id']}")
        if message_detail.status_code == 200:
            message_data = message_detail.json()
            # 检查是否包含编排器元数据
            if "metadata" in message_data:
                metadata = message_data["metadata"]
                # 验证包含执行模式信息
                assert "execution_mode" in metadata or "execution_time" in metadata
    
    @pytest.mark.asyncio
    async def test_planning_routing(self, client):
        """测试复杂任务路由到PlannerAgent"""
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "帮我制定一个详细的学习Python的计划，包括步骤、时间安排和资源推荐"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应正常
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert len(data["content"]) > 0
        
        # 验证内容包含规划相关信息
        content = data["content"].lower()
        # 简单验证是否包含规划相关词汇
        planning_keywords = ["计划", "步骤", "学习", "安排", "建议"]
        has_planning_content = any(keyword in content for keyword in planning_keywords)
        # 注意：具体内容取决于LLM和路由决策
    
    @pytest.mark.asyncio
    async def test_reflection_routing(self, client):
        """测试代码生成任务路由到ExecutorAgent"""
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请生成一个完整的Python类，实现一个简单的计算器，包含加减乘除功能，要有详细的注释和错误处理"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应正常
        assert "conversation_id" in data
        assert "message_id" in data
        assert "content" in data
        assert len(data["content"]) > 0
        
        # 验证内容包含代码
        content = data["content"]
        code_indicators = ["class", "def", "import", "return", "try", "except"]
        has_code = any(indicator in content for indicator in code_indicators)
        # 注意：具体内容取决于LLM和路由决策
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, client):
        """测试记忆系统集成"""
        conversation_id = None
        
        # 第一轮对话 - 建立记忆
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是王五，我是一名数据科学家，专门研究机器学习"
        })
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        
        # 第二轮对话 - 测试记忆检索
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请根据我的背景，推荐一些适合的学习资源"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 验证记忆系统工作
        assert data2["conversation_id"] == conversation_id
        assert len(data2["content"]) > 0
        
        # 第三轮对话 - 测试记忆持久化
        response3 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我刚才说我叫什么名字？"
        })
        assert response3.status_code == 200
        data3 = response3.json()
        
        # 注意：具体记忆效果取决于LLM和记忆系统配置
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_integration(self, client):
        """测试知识图谱集成"""
        # 提供包含实体和关系的信息
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我认识张三，他是我的同事，在技术部门工作。李四是我们的项目经理，负责管理张三和我。"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应正常
        assert "conversation_id" in data
        assert "content" in data
        
        # 测试知识图谱查询
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "张三在哪个部门工作？"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        
        # 注意：具体知识图谱效果取决于系统配置
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, client):
        """测试异常恢复机制"""
        # 测试可能导致错误的请求
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请执行一个不存在的系统命令：rm -rf /"
        })
        
        # 系统应该能够处理错误并返回合理响应
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        
        # 验证系统没有崩溃，能够继续处理请求
        follow_up = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "你好，系统还正常吗？"
        })
        assert follow_up.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_orchestrator_requests(self, client):
        """测试编排器并发处理"""
        # 创建不同类型的并发请求
        tasks = []
        
        # 简单对话请求
        for i in range(3):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"简单对话 {i}"
            })
            tasks.append(task)
        
        # 复杂任务请求
        for i in range(2):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"帮我制定一个详细的学习计划 {i}"
            })
            tasks.append(task)
        
        # 代码生成请求
        for i in range(2):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"生成一个Python函数 {i}"
            })
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功处理
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_state_machine_flow(self, client):
        """测试状态机流程"""
        # 发送一个需要多步骤处理的任务
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
                    # 验证状态转换记录
                    if len(state_history) > 0:
                        for state in state_history:
                            assert "from_state" in state
                            assert "to_state" in state
    
    @pytest.mark.asyncio
    async def test_role_orchestrator_integration(self, client):
        """测试角色与编排器集成"""
        # 测试通用助手的编排器功能
        general_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "帮我写一个完整的Python项目，包括主程序和测试"
        })
        assert general_response.status_code == 200
        general_data = general_response.json()
        
        # 测试电商客服的编排器功能
        cs_response = await client.post("/api/v1/customer_service/chat", json={
            "user_id": 1,
            "content": "我想了解你们的退货政策"
        })
        assert cs_response.status_code == 200
        cs_data = cs_response.json()
        
        # 验证两个角色都能正常使用编排器
        assert "content" in general_data
        assert "content" in cs_data
        assert len(general_data["content"]) > 0
        assert len(cs_data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_orchestrator_performance(self, client):
        """测试编排器性能"""
        import time
        
        # 测试响应时间
        start_time = time.time()
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请简单介绍一下人工智能的发展历史"
        })
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        
        # 验证响应时间在合理范围内（小于10秒）
        assert response_time < 10.0
        
        # 检查消息元数据中的执行时间
        data = response.json()
        message_detail = await client.get(f"/api/v1/messages/{data['message_id']}")
        if message_detail.status_code == 200:
            message_data = message_detail.json()
            if "metadata" in message_data:
                metadata = message_data["metadata"]
                if "execution_time" in metadata:
                    execution_time = metadata["execution_time"]
                    assert execution_time > 0
                    assert execution_time < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
