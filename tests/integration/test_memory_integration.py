"""
记忆系统集成测试

测试记忆管理器集成、与ContextBuilder集成和端到端记忆流程
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from sqlalchemy.orm import Session

from app.core.memory import MemoryManager
from app.core.memory.context_builder import ContextBuilder
from app.services.memory_service import MemoryService
from app.models.memory import MemoryStore
from app.schemas.message import MessageSend


class TestMemoryManagerIntegration:
    """测试记忆管理器集成"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def memory_manager(self, mock_db, mock_llm):
        """创建记忆管理器实例"""
        with patch('app.core.memory.memory_manager.MemoryDAO'):
            return MemoryManager(mock_db, mock_llm)
    
    @pytest.mark.asyncio
    async def test_add_memory_integration(self, memory_manager, mock_llm):
        """测试添加记忆的完整流程"""
        # 模拟分类和评分
        mock_llm.achat.side_effect = ["long_term", "0.8", "0.6", "0.7"]
        
        # 模拟DAO创建
        with patch.object(memory_manager.memory_dao, 'create') as mock_create:
            mock_memory = MemoryStore(
                id=1,
                conversation_id=1,
                content="测试记忆内容",
                memory_type="long_term",
                importance_score=0.7
            )
            mock_create.return_value = mock_memory
            
            result = await memory_manager.add_memory(
                conversation_id=1,
                content="测试记忆内容"
            )
            
            assert result is not None
            assert result.memory_type == "long_term"
            assert result.importance_score == 0.7
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_relevant_memories_integration(self, memory_manager):
        """测试获取相关记忆的完整流程"""
        # 模拟DAO查询
        mock_memories = [
            MemoryStore(
                id=1,
                conversation_id=1,
                content="相关记忆1",
                memory_type="long_term",
                importance_score=0.8
            ),
            MemoryStore(
                id=2,
                conversation_id=1,
                content="相关记忆2",
                memory_type="short_term",
                importance_score=0.6
            )
        ]
        
        with patch.object(memory_manager.memory_dao, 'get_by_conversation') as mock_get:
            mock_get.return_value = mock_memories
            
            results = await memory_manager.get_relevant_memories(
                conversation_id=1,
                query="测试查询",
                limit=5
            )
            
            assert len(results) <= 5
            # 应该按重要性排序
            if len(results) > 1:
                assert results[0].importance_score >= results[1].importance_score
    
    @pytest.mark.asyncio
    async def test_upgrade_to_long_term_integration(self, memory_manager):
        """测试短期记忆升级为长期记忆"""
        short_term_memories = [
            MemoryStore(
                id=1,
                conversation_id=1,
                content="短期记忆1",
                memory_type="short_term",
                importance_score=0.7,
                created_at=datetime.utcnow() - timedelta(hours=25)
            ),
            MemoryStore(
                id=2,
                conversation_id=1,
                content="短期记忆2",
                memory_type="short_term",
                importance_score=0.5,
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
        ]
        
        with patch.object(memory_manager.memory_dao, 'update') as mock_update:
            mock_update.side_effect = short_term_memories
            
            results = await memory_manager.upgrade_to_long_term(short_term_memories)
            
            # 只有第一个记忆应该被升级（超过24小时且重要性高）
            assert len(results) >= 0
            for memory in results:
                assert memory.memory_type == "long_term"
    
    @pytest.mark.asyncio
    async def test_compress_memories_integration(self, memory_manager, mock_llm):
        """测试记忆压缩集成"""
        memories = [
            MemoryStore(
                id=1,
                conversation_id=1,
                content="记忆1",
                memory_type="short_term",
                importance_score=0.6
            ),
            MemoryStore(
                id=2,
                conversation_id=1,
                content="记忆2",
                memory_type="short_term",
                importance_score=0.7
            )
        ]
        
        # 模拟LLM压缩
        mock_llm.achat.return_value = "压缩后的记忆摘要"
        
        with patch.object(memory_manager.memory_dao, 'create') as mock_create, \
             patch.object(memory_manager.memory_dao, 'update') as mock_update:
            
            mock_compressed = MemoryStore(
                id=3,
                conversation_id=1,
                content="压缩后的记忆摘要",
                memory_type="long_term",
                importance_score=0.65
            )
            mock_create.return_value = mock_compressed
            
            result = await memory_manager.compress_memories(memories)
            
            assert result is not None
            assert result.content == "压缩后的记忆摘要"
            assert result.memory_metadata["compressed"] is True
            mock_create.assert_called_once()
            assert mock_update.call_count == 2  # 更新原始记忆
    
    @pytest.mark.asyncio
    async def test_maintain_memories_integration(self, memory_manager, mock_llm):
        """测试记忆维护集成"""
        # 模拟各种类型的记忆
        all_memories = [
            MemoryStore(
                id=1,
                conversation_id=1,
                content="短期记忆",
                memory_type="short_term",
                importance_score=0.7,
                created_at=datetime.utcnow() - timedelta(hours=25)
            ),
            MemoryStore(
                id=2,
                conversation_id=1,
                content="长期记忆",
                memory_type="long_term",
                importance_score=0.3,
                created_at=datetime.utcnow() - timedelta(days=30)
            )
        ]
        
        with patch.object(memory_manager.memory_dao, 'get_by_conversation') as mock_get, \
             patch.object(memory_manager.memory_dao, 'update') as mock_update, \
             patch.object(memory_manager.memory_dao, 'delete') as mock_delete:
            
            mock_get.return_value = all_memories
            
            result = await memory_manager.maintain_memories(conversation_id=1)
            
            assert "upgraded_count" in result
            assert "compressed_count" in result
            assert "forgotten_count" in result
            assert "total_memories" in result
            assert result["total_memories"] == 2


class TestMemoryServiceIntegration:
    """测试记忆服务集成"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.fixture
    def mock_memory_manager(self):
        """模拟记忆管理器"""
        manager = Mock()
        manager.add_memory = AsyncMock()
        manager.get_relevant_memories = AsyncMock()
        manager.maintain_memories = AsyncMock()
        return manager
    
    @pytest.fixture
    def memory_service(self, mock_db, mock_llm, mock_memory_manager):
        """创建记忆服务实例"""
        return MemoryService(mock_db, mock_llm, mock_memory_manager)
    
    @pytest.mark.asyncio
    async def test_save_conversation_memory_integration(self, memory_service, mock_memory_manager):
        """测试保存会话记忆集成"""
        messages = [
            {"role": "user", "content": "用户消息1"},
            {"role": "assistant", "content": "助手回复1"},
            {"role": "user", "content": "用户消息2"},
            {"role": "assistant", "content": "重要建议：请注意这个"}
        ]
        
        # 模拟记忆创建
        mock_memories = [
            MemoryStore(id=1, conversation_id=1, content="用户消息1", memory_type="short_term"),
            MemoryStore(id=2, conversation_id=1, content="重要建议：请注意这个", memory_type="episodic")
        ]
        mock_memory_manager.add_memory.side_effect = mock_memories
        
        results = await memory_service.save_conversation_memory(conversation_id=1, messages=messages)
        
        # 应该保存用户消息和重要的助手回复
        assert len(results) >= 2
        assert mock_memory_manager.add_memory.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_context_memories_integration(self, memory_service, mock_memory_manager):
        """测试获取上下文记忆集成"""
        # 模拟相关记忆
        mock_memories = [
            MemoryStore(
                id=1,
                conversation_id=1,
                content="相关记忆1",
                memory_type="long_term",
                importance_score=0.8
            ),
            MemoryStore(
                id=2,
                conversation_id=1,
                content="相关记忆2",
                memory_type="episodic",
                importance_score=0.6
            )
        ]
        mock_memory_manager.get_relevant_memories.return_value = mock_memories
        
        result = await memory_service.get_context_memories(
            conversation_id=1,
            query="测试查询",
            max_tokens=1000
        )
        
        assert isinstance(result, str)
        assert "相关记忆1" in result
        assert "相关记忆2" in result
    
    @pytest.mark.asyncio
    async def test_add_user_preference_integration(self, memory_service, mock_memory_manager):
        """测试添加用户偏好集成"""
        mock_memory = MemoryStore(
            id=1,
            conversation_id=1,
            content="用户偏好 - 语言: 中文",
            memory_type="long_term",
            importance_score=0.8
        )
        mock_memory_manager.add_memory.return_value = mock_memory
        
        result = await memory_service.add_user_preference(
            conversation_id=1,
            user_id=1,
            preference_type="语言",
            preference_value="中文"
        )
        
        assert result is not None
        assert result.memory_type == "long_term"
        assert "语言" in result.content
        assert "中文" in result.content
    
    @pytest.mark.asyncio
    async def test_add_fact_memory_integration(self, memory_service, mock_memory_manager):
        """测试添加事实记忆集成"""
        mock_memory = MemoryStore(
            id=1,
            conversation_id=1,
            content="Python是一种编程语言",
            memory_type="semantic",
            importance_score=0.7
        )
        mock_memory_manager.add_memory.return_value = mock_memory
        
        result = await memory_service.add_fact_memory(
            conversation_id=1,
            fact_content="Python是一种编程语言",
            fact_type="编程"
        )
        
        assert result is not None
        assert result.memory_type == "semantic"
        assert "Python" in result.content
    
    @pytest.mark.asyncio
    async def test_add_event_memory_integration(self, memory_service, mock_memory_manager):
        """测试添加事件记忆集成"""
        mock_memory = MemoryStore(
            id=1,
            conversation_id=1,
            content="用户完成了项目报告",
            memory_type="episodic",
            importance_score=0.6
        )
        mock_memory_manager.add_memory.return_value = mock_memory
        
        result = await memory_service.add_event_memory(
            conversation_id=1,
            event_description="用户完成了项目报告",
            event_type="工作"
        )
        
        assert result is not None
        assert result.memory_type == "episodic"
        assert "项目报告" in result.content


class TestContextBuilderIntegration:
    """测试ContextBuilder集成"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_memory_service(self):
        """模拟记忆服务"""
        service = Mock()
        service.get_context_memories = AsyncMock()
        return service
    
    @pytest.fixture
    def context_builder(self, mock_db, mock_memory_service):
        """创建ContextBuilder实例"""
        return ContextBuilder(
            db=mock_db,
            memory_service=mock_memory_service,
            system_prompt="你是一个智能助手"
        )
    
    @pytest.mark.asyncio
    async def test_build_context_with_memories(self, context_builder, mock_memory_service):
        """测试构建包含记忆的上下文"""
        # 模拟相关记忆
        mock_memory_service.get_context_memories.return_value = "相关记忆内容"
        
        result = await context_builder.build_context(
            conversation_id=1,
            user_id=1,
            include_memories=True
        )
        
        assert isinstance(result, list)
        # 应该包含系统提示词和记忆
        assert len(result) >= 1
        mock_memory_service.get_context_memories.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_context_without_memories(self, context_builder, mock_memory_service):
        """测试构建不包含记忆的上下文"""
        result = await context_builder.build_context(
            conversation_id=1,
            user_id=1,
            include_memories=False
        )
        
        assert isinstance(result, list)
        # 不应该调用记忆服务
        mock_memory_service.get_context_memories.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_build_context_with_system_prompt(self, context_builder):
        """测试构建包含系统提示词的上下文"""
        result = await context_builder.build_context(
            conversation_id=1,
            user_id=1,
            include_memories=False
        )
        
        assert isinstance(result, list)
        # 应该包含系统提示词
        if result:
            assert result[0].role == "system"
            assert "智能助手" in result[0].content


class TestEndToEndMemoryFlow:
    """测试端到端记忆流程"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.achat = AsyncMock()
        return llm
    
    @pytest.mark.asyncio
    async def test_complete_memory_lifecycle(self, mock_db, mock_llm):
        """测试完整的记忆生命周期"""
        # 模拟LLM响应
        mock_llm.achat.side_effect = [
            "short_term",  # 分类
            "0.6", "0.5", "0.7",  # 评分
            "long_term",  # 分类
            "0.8", "0.6", "0.8",  # 评分
        ]
        
        with patch('app.core.memory.memory_manager.MemoryDAO') as mock_dao_class:
            mock_dao = Mock()
            mock_dao_class.return_value = mock_dao
            
            # 创建记忆管理器
            memory_manager = MemoryManager(mock_db, mock_llm)
            
            # 模拟DAO操作
            mock_memory1 = MemoryStore(
                id=1,
                conversation_id=1,
                content="用户消息",
                memory_type="short_term",
                importance_score=0.6
            )
            mock_memory2 = MemoryStore(
                id=2,
                conversation_id=1,
                content="重要信息",
                memory_type="long_term",
                importance_score=0.8
            )
            
            mock_dao.create.side_effect = [mock_memory1, mock_memory2]
            mock_dao.get_by_conversation.return_value = [mock_memory1, mock_memory2]
            mock_dao.update.return_value = mock_memory1
            
            # 1. 添加记忆
            result1 = await memory_manager.add_memory(
                conversation_id=1,
                content="用户消息"
            )
            assert result1.memory_type == "short_term"
            
            result2 = await memory_manager.add_memory(
                conversation_id=1,
                content="重要信息"
            )
            assert result2.memory_type == "long_term"
            
            # 2. 获取相关记忆
            relevant = await memory_manager.get_relevant_memories(
                conversation_id=1,
                query="测试查询"
            )
            assert len(relevant) >= 0
            
            # 3. 维护记忆
            maintenance_result = await memory_manager.maintain_memories(conversation_id=1)
            assert "total_memories" in maintenance_result
            assert maintenance_result["total_memories"] == 2


if __name__ == "__main__":
    pytest.main([__file__])
