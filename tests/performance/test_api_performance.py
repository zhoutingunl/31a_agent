"""
API性能测试

测试API端点的响应时间、并发处理能力等性能指标
"""

import pytest
import asyncio
import time
import statistics
from httpx import AsyncClient

from app.main import app


class TestAPIPerformance:
    """API性能测试类"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.asyncio
    async def test_single_request_response_time(self, client):
        """测试单个请求的响应时间"""
        start_time = time.time()
        
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "你好，请简单介绍一下自己"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # 响应时间应小于5秒
        
        # 记录性能数据
        print(f"单请求响应时间: {response_time:.3f}秒")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, client):
        """测试并发请求性能"""
        concurrent_count = 10
        request_data = {
            "user_id": 1,
            "content": "请简单回答：什么是人工智能？"
        }
        
        # 记录开始时间
        start_time = time.time()
        
        # 创建并发请求
        tasks = []
        for i in range(concurrent_count):
            task = client.post("/api/v1/general/chat", json=request_data)
            tasks.append(task)
        
        # 等待所有请求完成
        responses = await asyncio.gather(*tasks)
        
        # 记录结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
        
        # 计算性能指标
        qps = concurrent_count / total_time
        avg_response_time = total_time / concurrent_count
        
        print(f"并发请求数: {concurrent_count}")
        print(f"总耗时: {total_time:.3f}秒")
        print(f"QPS: {qps:.2f}")
        print(f"平均响应时间: {avg_response_time:.3f}秒")
        
        # 性能断言
        assert qps > 1.0  # QPS应大于1
        assert avg_response_time < 10.0  # 平均响应时间应小于10秒
    
    @pytest.mark.asyncio
    async def test_response_time_distribution(self, client):
        """测试响应时间分布"""
        request_count = 20
        response_times = []
        
        for i in range(request_count):
            start_time = time.time()
            
            response = await client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"测试请求 {i}"
            })
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            response_times.append(response_time)
        
        # 计算统计指标
        mean_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        p95_time = sorted(response_times)[int(0.95 * len(response_times))]
        p99_time = sorted(response_times)[int(0.99 * len(response_times))]
        
        print(f"响应时间统计 (共{request_count}个请求):")
        print(f"  平均值: {mean_time:.3f}秒")
        print(f"  中位数: {median_time:.3f}秒")
        print(f"  P95: {p95_time:.3f}秒")
        print(f"  P99: {p99_time:.3f}秒")
        
        # 性能断言
        assert mean_time < 5.0  # 平均响应时间应小于5秒
        assert p95_time < 10.0  # P95响应时间应小于10秒
        assert p99_time < 15.0  # P99响应时间应小于15秒
    
    @pytest.mark.asyncio
    async def test_different_endpoints_performance(self, client):
        """测试不同端点的性能"""
        endpoints = [
            ("/api/v1/general/chat", {"user_id": 1, "content": "简单对话测试"}),
            ("/api/v1/customer_service/chat", {"user_id": 1, "content": "客服测试"}),
            ("/api/v1/chat", {"user_id": 1, "content": "基础聊天测试"}),
        ]
        
        performance_results = {}
        
        for endpoint, data in endpoints:
            start_time = time.time()
            
            response = await client.post(endpoint, json=data)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            performance_results[endpoint] = response_time
            
            print(f"{endpoint}: {response_time:.3f}秒")
        
        # 验证所有端点性能都在合理范围内
        for endpoint, response_time in performance_results.items():
            assert response_time < 10.0, f"{endpoint} 响应时间过长: {response_time:.3f}秒"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, client):
        """测试负载下的内存使用情况"""
        # 创建大量请求来测试内存使用
        request_count = 50
        tasks = []
        
        for i in range(request_count):
            task = client.post("/api/v1/general/chat", json={
                "user_id": 1,
                "content": f"内存测试请求 {i} - 请简单回答什么是机器学习"
            })
            tasks.append(task)
        
        # 分批执行以避免过载
        batch_size = 10
        all_responses = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_responses = await asyncio.gather(*batch)
            all_responses.extend(batch_responses)
            
            # 短暂休息
            await asyncio.sleep(0.1)
        
        # 验证所有请求都成功
        for response in all_responses:
            assert response.status_code == 200
        
        print(f"成功处理 {len(all_responses)} 个并发请求")
    
    @pytest.mark.asyncio
    async def test_streaming_performance(self, client):
        """测试流式响应性能"""
        start_time = time.time()
        
        response = await client.post("/api/v1/chat/stream", json={
            "user_id": 1,
            "content": "请详细介绍人工智能的发展历史"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # 验证流式响应内容
        content = response.text
        assert len(content) > 0
        
        print(f"流式响应时间: {response_time:.3f}秒")
        print(f"响应内容长度: {len(content)} 字符")
        
        # 流式响应应该比普通响应快
        assert response_time < 15.0
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, client):
        """测试数据库连接池性能"""
        # 创建大量需要数据库操作的请求
        request_count = 30
        tasks = []
        
        for i in range(request_count):
            # 创建会话和消息，需要数据库操作
            task = client.post("/api/v1/general/chat", json={
                "user_id": i % 5 + 1,  # 使用不同用户ID
                "content": f"数据库连接池测试 {i}"
            })
            tasks.append(task)
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
        
        total_time = end_time - start_time
        qps = request_count / total_time
        
        print(f"数据库连接池测试:")
        print(f"  请求数: {request_count}")
        print(f"  总耗时: {total_time:.3f}秒")
        print(f"  QPS: {qps:.2f}")
        
        # 验证数据库连接池性能
        assert qps > 0.5  # 至少0.5 QPS
        assert total_time < 60.0  # 总时间应小于60秒
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, client):
        """测试错误处理的性能影响"""
        # 测试正常请求
        start_time = time.time()
        normal_response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "正常请求测试"
        })
        normal_time = time.time() - start_time
        
        # 测试错误请求
        start_time = time.time()
        error_response = await client.post("/api/v1/general/chat", json={
            "user_id": "invalid",  # 无效的用户ID
            "content": "错误请求测试"
        })
        error_time = time.time() - start_time
        
        # 验证响应
        assert normal_response.status_code == 200
        assert error_response.status_code == 422
        
        print(f"正常请求响应时间: {normal_time:.3f}秒")
        print(f"错误请求响应时间: {error_time:.3f}秒")
        
        # 错误处理不应该显著影响性能
        assert error_time < normal_time * 2  # 错误处理时间不应超过正常请求的2倍
    
    @pytest.mark.asyncio
    async def test_long_running_request_performance(self, client):
        """测试长时间运行请求的性能"""
        start_time = time.time()
        
        response = await client.post("/api/v1/general/chat", json={
            "user_id": 1,
            "content": "请帮我制定一个详细的学习计划，包括：1. 学习目标 2. 时间安排 3. 学习资源 4. 评估方法 5. 具体步骤"
        })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["content"]) > 100  # 应该有详细内容
        
        print(f"长时间运行请求响应时间: {response_time:.3f}秒")
        print(f"响应内容长度: {len(data['content'])} 字符")
        
        # 长时间请求应该在合理时间内完成
        assert response_time < 30.0  # 应小于30秒


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s 显示print输出
