"""
记忆与知识图谱集成测试

测试记忆系统与知识图谱的协同工作
"""

import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


class TestMemoryKnowledgeIntegration:
    """记忆与知识图谱集成测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_memory_to_knowledge_upgrade(self, client):
        """测试记忆升级到知识图谱"""
        conversation_id = None
        
        # 第一轮：建立短期记忆
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是张三，我是一名软件工程师，专门从事Python开发。我住在北京，喜欢阅读和编程。"
        })
        assert response1.status_code == 200
        conversation_id = response1.json()["conversation_id"]
        
        # 第二轮：添加更多信息，触发记忆升级
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我最近在学习机器学习，特别是深度学习。我对TensorFlow和PyTorch都很感兴趣。我的同事李四也在学习AI。"
        })
        assert response2.status_code == 200
        
        # 第三轮：测试知识图谱查询
        response3 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请总结一下我的个人信息和技能"
        })
        assert response3.status_code == 200
        data3 = response3.json()
        
        # 验证响应包含个人信息
        content = data3["content"].lower()
        personal_keywords = ["张三", "工程师", "python", "机器学习", "tensorflow", "pytorch"]
        found_keywords = [kw for kw in personal_keywords if kw in content]
        
        # 至少应该找到一些关键词
        assert len(found_keywords) > 0, f"未找到预期的个人信息关键词，响应内容: {data3['content']}"
    
    @pytest.mark.asyncio
    async def test_entity_relationship_extraction(self, client):
        """测试实体和关系提取"""
        # 提供包含实体和关系的信息
        entity_info = [
            "我认识张三，他是我的同事，在技术部门工作",
            "李四是我们的项目经理，负责管理技术团队",
            "王五是产品经理，和张三经常合作",
            "我们公司使用Python、Java和Go语言",
            "我们的项目包括电商系统、数据分析平台和机器学习服务"
        ]
        
        for info in entity_info:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": info
            })
            assert response.status_code == 200
        
        # 测试实体查询
        entity_queries = [
            "张三在哪个部门工作？",
            "谁负责管理技术团队？",
            "王五和谁经常合作？",
            "我们公司使用哪些编程语言？",
            "我们的项目有哪些？"
        ]
        
        for query in entity_queries:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_reasoning(self, client):
        """测试知识图谱推理"""
        # 建立知识图谱
        knowledge_base = [
            "张三是一名软件工程师",
            "李四是项目经理",
            "张三向李四汇报工作",
            "王五是产品经理",
            "李四管理张三和王五",
            "我们公司开发电商系统",
            "张三负责电商系统的后端开发",
            "王五负责电商系统的产品设计"
        ]
        
        for knowledge in knowledge_base:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": knowledge
            })
            assert response.status_code == 200
        
        # 测试推理查询
        reasoning_queries = [
            "谁管理张三？",
            "张三的上级是谁？",
            "王五的上级是谁？",
            "谁负责电商系统的开发？",
            "张三和谁一起工作？"
        ]
        
        for query in reasoning_queries:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_memory_compression_with_knowledge(self, client):
        """测试记忆压缩与知识图谱的协同"""
        # 建立大量记忆
        for i in range(15):
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"这是第{i+1}条记忆信息，包含一些详细的内容和上下文信息，用于测试记忆压缩功能。我是一名开发者，使用Python编程。"
            })
            assert response.status_code == 200
        
        # 测试记忆压缩
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请总结一下我们之前的所有对话内容，提取关键信息"
        })
        assert response.status_code == 200
        data = response.json()
        
        # 验证压缩结果
        assert len(data["content"]) > 0
        content = data["content"].lower()
        
        # 应该包含一些关键信息
        key_indicators = ["开发者", "python", "记忆", "信息"]
        found_indicators = [indicator for indicator in key_indicators if indicator in content]
        assert len(found_indicators) > 0
    
    @pytest.mark.asyncio
    async def test_hybrid_retrieval_performance(self, client):
        """测试混合检索性能"""
        # 建立混合记忆（短期+长期+知识图谱）
        memory_data = [
            "我的名字是赵六，我是一名数据科学家",
            "我专门研究自然语言处理和机器学习",
            "我使用Python、R和SQL进行数据分析",
            "我的同事包括张三、李四和王五",
            "我们团队负责公司的AI项目",
            "我最近在研究Transformer模型",
            "我对BERT和GPT模型很感兴趣",
            "我们使用TensorFlow和PyTorch框架"
        ]
        
        for data in memory_data:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": data
            })
            assert response.status_code == 200
        
        # 测试不同类型的检索
        retrieval_queries = [
            "我的名字是什么？",  # 简单事实查询
            "我研究什么领域？",  # 技能查询
            "我的同事有哪些？",  # 关系查询
            "我们团队负责什么？",  # 团队信息查询
            "我使用什么工具？",  # 工具查询
            "我对什么模型感兴趣？"  # 兴趣查询
        ]
        
        for query in retrieval_queries:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_consistency(self, client):
        """测试知识图谱一致性"""
        # 建立初始知识
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是张三，我是一名软件工程师，在技术部门工作"
        })
        assert response1.status_code == 200
        
        # 添加更多信息
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的同事李四是项目经理，负责管理我们技术团队"
        })
        assert response2.status_code == 200
        
        # 测试一致性查询
        consistency_queries = [
            "我的名字是什么？",
            "我的职业是什么？",
            "我在哪个部门？",
            "我的同事是谁？",
            "李四的职位是什么？",
            "李四管理谁？"
        ]
        
        for query in consistency_queries:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_memory_forgetting_with_knowledge_preservation(self, client):
        """测试记忆遗忘与知识保留"""
        # 建立大量临时记忆
        for i in range(20):
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"临时信息 {i}：这是一条临时的、不重要的信息，应该被遗忘"
            })
            assert response.status_code == 200
        
        # 建立重要知识
        important_knowledge = [
            "我的名字是张三，我是一名软件工程师",
            "我专门从事Python开发",
            "我的重要技能包括：Python、Docker、Kubernetes",
            "我负责公司的核心系统开发"
        ]
        
        for knowledge in important_knowledge:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": knowledge
            })
            assert response.status_code == 200
        
        # 测试重要知识是否保留
        important_queries = [
            "我的名字是什么？",
            "我的职业是什么？",
            "我使用什么编程语言？",
            "我的技能有哪些？",
            "我负责什么工作？"
        ]
        
        for query in important_queries:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_knowledge_operations(self, client):
        """测试并发记忆和知识图谱操作"""
        # 创建并发请求，每个都涉及记忆和知识操作
        concurrent_count = 10
        tasks = []
        
        for i in range(concurrent_count):
            task = client.post("/api/v1/general/chat", json={
                "user_id": i % 3 + 1,  # 使用不同用户ID
                "content": f"并发测试 {i} - 我的名字是用户{i}，我是一名开发者，使用Python编程"
            })
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
        
        # 测试并发后的知识查询
        query_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请总结一下我们刚才的对话"
        })
        assert query_response.status_code == 200
        data = query_response.json()
        assert len(data["content"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
