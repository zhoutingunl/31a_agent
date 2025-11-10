"""
记忆系统性能测试

测试记忆系统的检索性能、存储性能等
"""

import pytest
import asyncio
import time
import statistics
from httpx import AsyncClient

from app.main import app


class TestMemoryPerformance:
    """记忆系统性能测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_memory_storage_performance(self, client):
        """测试记忆存储性能"""
        # 创建包含大量信息的对话来测试记忆存储
        conversation_id = None
        storage_times = []
        
        # 第一轮：建立基础记忆
        start_time = time.time()
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是张三，我是一名软件工程师，专门从事Python开发。我住在北京，喜欢阅读和编程。"
        })
        storage_time1 = time.time() - start_time
        storage_times.append(storage_time1)
        
        assert response1.status_code == 200
        conversation_id = response1.json()["conversation_id"]
        
        # 第二轮：添加更多记忆
        start_time = time.time()
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我最近在学习机器学习，特别是深度学习。我对TensorFlow和PyTorch都很感兴趣。"
        })
        storage_time2 = time.time() - start_time
        storage_times.append(storage_time2)
        
        assert response2.status_code == 200
        
        # 第三轮：添加复杂记忆
        start_time = time.time()
        response3 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的工作项目包括：1. 电商系统后端开发 2. 数据分析平台 3. 机器学习模型部署。我使用Docker和Kubernetes进行部署。"
        })
        storage_time3 = time.time() - start_time
        storage_times.append(storage_time3)
        
        assert response3.status_code == 200
        
        # 计算存储性能统计
        avg_storage_time = statistics.mean(storage_times)
        max_storage_time = max(storage_times)
        
        print(f"记忆存储性能测试:")
        print(f"  平均存储时间: {avg_storage_time:.3f}秒")
        print(f"  最大存储时间: {max_storage_time:.3f}秒")
        
        # 验证存储性能
        assert avg_storage_time < 3.0  # 平均存储时间应小于3秒
        assert max_storage_time < 5.0  # 最大存储时间应小于5秒
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_performance(self, client):
        """测试记忆检索性能"""
        conversation_id = None
        
        # 先建立一些记忆
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的名字是李四，我是一名数据科学家，专门研究自然语言处理。我使用Python和R进行数据分析。"
        })
        conversation_id = response1.json()["conversation_id"]
        
        # 测试记忆检索性能
        retrieval_queries = [
            "我刚才说我叫什么名字？",
            "我的职业是什么？",
            "我使用什么编程语言？",
            "我研究什么领域？",
            "请总结一下我的背景信息"
        ]
        
        retrieval_times = []
        
        for query in retrieval_queries:
            start_time = time.time()
            
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            
            retrieval_time = time.time() - start_time
            retrieval_times.append(retrieval_time)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["content"]) > 0
        
        # 计算检索性能统计
        avg_retrieval_time = statistics.mean(retrieval_times)
        max_retrieval_time = max(retrieval_times)
        min_retrieval_time = min(retrieval_times)
        
        print(f"记忆检索性能测试:")
        print(f"  平均检索时间: {avg_retrieval_time:.3f}秒")
        print(f"  最大检索时间: {max_retrieval_time:.3f}秒")
        print(f"  最小检索时间: {min_retrieval_time:.3f}秒")
        
        # 验证检索性能
        assert avg_retrieval_time < 2.0  # 平均检索时间应小于2秒
        assert max_retrieval_time < 4.0  # 最大检索时间应小于4秒
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, client):
        """测试向量搜索性能"""
        # 建立包含多个主题的记忆
        topics = [
            "人工智能和机器学习的发展历史",
            "Python编程语言的特点和优势",
            "数据库设计和优化技巧",
            "Web开发的最佳实践",
            "软件测试的方法和工具"
        ]
        
        for topic in topics:
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"请详细介绍{topic}"
            })
            assert response.status_code == 200
        
        # 测试向量搜索性能
        search_queries = [
            "关于AI的信息",
            "Python相关内容",
            "数据库相关",
            "Web开发",
            "测试方法"
        ]
        
        search_times = []
        
        for query in search_queries:
            start_time = time.time()
            
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"根据我们之前的对话，{query}"
            })
            
            search_time = time.time() - start_time
            search_times.append(search_time)
            
            assert response.status_code == 200
        
        # 计算搜索性能统计
        avg_search_time = statistics.mean(search_times)
        max_search_time = max(search_times)
        
        print(f"向量搜索性能测试:")
        print(f"  平均搜索时间: {avg_search_time:.3f}秒")
        print(f"  最大搜索时间: {max_search_time:.3f}秒")
        
        # 验证搜索性能
        assert avg_search_time < 3.0  # 平均搜索时间应小于3秒
        assert max_search_time < 5.0  # 最大搜索时间应小于5秒
    
    @pytest.mark.asyncio
    async def test_knowledge_graph_performance(self, client):
        """测试知识图谱性能"""
        # 建立包含实体和关系的信息
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
        
        # 测试知识图谱查询性能
        graph_queries = [
            "张三在哪个部门工作？",
            "谁负责管理技术团队？",
            "王五和谁经常合作？",
            "我们公司使用哪些编程语言？",
            "我们的项目有哪些？"
        ]
        
        graph_times = []
        
        for query in graph_queries:
            start_time = time.time()
            
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": query
            })
            
            graph_time = time.time() - start_time
            graph_times.append(graph_time)
            
            assert response.status_code == 200
        
        # 计算知识图谱性能统计
        avg_graph_time = statistics.mean(graph_times)
        max_graph_time = max(graph_times)
        
        print(f"知识图谱性能测试:")
        print(f"  平均查询时间: {avg_graph_time:.3f}秒")
        print(f"  最大查询时间: {max_graph_time:.3f}秒")
        
        # 验证知识图谱性能
        assert avg_graph_time < 2.5  # 平均查询时间应小于2.5秒
        assert max_graph_time < 4.0  # 最大查询时间应小于4秒
    
    @pytest.mark.asyncio
    async def test_memory_compression_performance(self, client):
        """测试记忆压缩性能"""
        # 建立大量记忆数据
        for i in range(20):
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"这是第{i+1}条记忆信息，包含一些详细的内容和上下文信息，用于测试记忆压缩功能。"
            })
            assert response.status_code == 200
        
        # 测试记忆压缩性能
        start_time = time.time()
        
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请总结一下我们之前的所有对话内容"
        })
        
        compression_time = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["content"]) > 0
        
        print(f"记忆压缩性能测试:")
        print(f"  压缩时间: {compression_time:.3f}秒")
        print(f"  压缩后内容长度: {len(data['content'])} 字符")
        
        # 验证压缩性能
        assert compression_time < 5.0  # 压缩时间应小于5秒
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, client):
        """测试并发记忆操作性能"""
        # 创建多个并发请求，每个都涉及记忆操作
        concurrent_count = 15
        tasks = []
        
        for i in range(concurrent_count):
            task = client.post("/api/v1/general/chat", json={
                "user_id": i % 3 + 1,  # 使用不同用户ID
                "content": f"并发记忆测试 {i} - 我的名字是用户{i}，我是一名开发者"
            })
            tasks.append(task)
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
        
        total_time = end_time - start_time
        qps = concurrent_count / total_time
        
        print(f"并发记忆操作性能测试:")
        print(f"  并发数: {concurrent_count}")
        print(f"  总耗时: {total_time:.3f}秒")
        print(f"  QPS: {qps:.2f}")
        
        # 验证并发性能
        assert qps > 0.5  # 至少0.5 QPS
        assert total_time < 30.0  # 总时间应小于30秒
    
    @pytest.mark.asyncio
    async def test_memory_persistence_performance(self, client):
        """测试记忆持久化性能"""
        # 建立一些记忆
        response1 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "我的重要信息：姓名张三，职业工程师，技能Python、Java、Docker"
        })
        assert response1.status_code == 200
        
        # 等待一段时间确保持久化
        await asyncio.sleep(1)
        
        # 测试记忆持久化后的检索性能
        start_time = time.time()
        
        response2 = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请告诉我我的重要信息"
        })
        
        retrieval_time = time.time() - start_time
        
        assert response2.status_code == 200
        data = response2.json()
        assert len(data["content"]) > 0
        
        print(f"记忆持久化性能测试:")
        print(f"  持久化后检索时间: {retrieval_time:.3f}秒")
        
        # 验证持久化性能
        assert retrieval_time < 3.0  # 持久化后检索时间应小于3秒


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s 显示print输出
