"""
模型单元测试
测试 ORM 模型的基本功能
"""

import pytest
from datetime import datetime, timedelta

from app.models.task import Task
from app.models.memory import MemoryStore
from app.models.knowledge import KnowledgeGraph, KnowledgeRelation


class TestTaskModel:
    """任务模型测试"""
    
    def test_task_creation(self, test_db, test_conversation):
        """测试任务创建"""
        task = Task(
            conversation_id=test_conversation.id,
            task_type="plan",
            description="Test task description",
            priority=5
        )
        
        test_db.add(task)
        test_db.commit()
        test_db.refresh(task)
        
        assert task.id is not None
        assert task.conversation_id == test_conversation.id
        assert task.task_type == "plan"
        assert task.description == "Test task description"
        assert task.status == "pending"
        assert task.priority == 5
        assert task.retry_count == 0
        assert task.created_at is not None
        assert task.updated_at is not None
    
    def test_task_status_properties(self, test_task):
        """测试任务状态属性"""
        # 测试初始状态
        assert test_task.is_pending
        assert not test_task.is_running
        assert not test_task.is_completed
        assert not test_task.is_failed
        
        # 测试状态变更
        test_task.status = "running"
        assert not test_task.is_pending
        assert test_task.is_running
        assert not test_task.is_completed
        assert not test_task.is_failed
        
        test_task.status = "completed"
        assert not test_task.is_pending
        assert not test_task.is_running
        assert test_task.is_completed
        assert not test_task.is_failed
        
        test_task.status = "failed"
        assert not test_task.is_pending
        assert not test_task.is_running
        assert not test_task.is_completed
        assert test_task.is_failed
    
    def test_task_status_methods(self, test_task):
        """测试任务状态方法"""
        # 测试标记开始
        test_task.mark_started()
        assert test_task.status == "running"
        assert test_task.started_at is not None
        
        # 测试标记完成
        test_task.mark_completed("Task completed successfully")
        assert test_task.status == "completed"
        assert test_task.completed_at is not None
        assert test_task.result == "Task completed successfully"
        
        # 测试标记失败
        test_task.mark_failed("Task failed with error")
        assert test_task.status == "failed"
        assert test_task.error_message == "Task failed with error"
        assert test_task.retry_count == 1
    
    def test_task_to_dict(self, test_task):
        """测试任务转字典"""
        task_dict = test_task.to_dict()
        
        assert isinstance(task_dict, dict)
        assert task_dict["id"] == test_task.id
        assert task_dict["conversation_id"] == test_task.conversation_id
        assert task_dict["task_type"] == test_task.task_type
        assert task_dict["description"] == test_task.description
        assert task_dict["status"] == test_task.status
        assert "created_at" in task_dict
        assert "updated_at" in task_dict


class TestMemoryModel:
    """记忆模型测试"""
    
    def test_memory_creation(self, test_db, test_conversation):
        """测试记忆创建"""
        memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="short_term",
            content="Test memory content",
            importance_score=0.7
        )
        
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)
        
        assert memory.id is not None
        assert memory.conversation_id == test_conversation.id
        assert memory.memory_type == "short_term"
        assert memory.content == "Test memory content"
        assert memory.importance_score == 0.7
        assert memory.access_count == 0
        assert memory.created_at is not None
    
    def test_memory_type_properties(self, test_db, test_conversation):
        """测试记忆类型属性"""
        # 短期记忆
        short_memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="short_term",
            content="Short term memory"
        )
        assert short_memory.is_short_term
        assert not short_memory.is_long_term
        assert not short_memory.is_episodic
        assert not short_memory.is_semantic
        
        # 长期记忆
        long_memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="long_term",
            content="Long term memory"
        )
        assert not long_memory.is_short_term
        assert long_memory.is_long_term
        assert not long_memory.is_episodic
        assert not long_memory.is_semantic
    
    def test_memory_expiration(self, test_db, test_conversation):
        """测试记忆过期"""
        # 未过期的记忆
        memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="short_term",
            content="Test memory",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        assert not memory.is_expired
        
        # 已过期的记忆
        expired_memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="short_term",
            content="Expired memory",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert expired_memory.is_expired
    
    def test_memory_methods(self, test_db, test_conversation):
        """测试记忆方法"""
        memory = MemoryStore(
            conversation_id=test_conversation.id,
            memory_type="short_term",
            content="Test memory"
        )
        
        # 测试标记访问
        initial_count = memory.access_count
        memory.mark_accessed()
        assert memory.access_count == initial_count + 1
        assert memory.last_accessed_at is not None
        
        # 测试设置重要性
        memory.set_importance(0.8)
        assert memory.importance_score == 0.8
        
        # 测试设置过期时间
        expires_at = datetime.utcnow() + timedelta(hours=2)
        memory.set_expiration(expires_at)
        assert memory.expires_at == expires_at
        
        # 测试延长过期时间
        memory.extend_expiration(hours=1)
        expected_expires = expires_at + timedelta(hours=1)
        assert memory.expires_at == expected_expires
    
    def test_memory_to_dict(self, test_memory):
        """测试记忆转字典"""
        memory_dict = test_memory.to_dict()
        
        assert isinstance(memory_dict, dict)
        assert memory_dict["id"] == test_memory.id
        assert memory_dict["conversation_id"] == test_memory.conversation_id
        assert memory_dict["memory_type"] == test_memory.memory_type
        assert memory_dict["content"] == test_memory.content
        assert memory_dict["importance_score"] == test_memory.importance_score
        assert "created_at" in memory_dict


class TestKnowledgeGraphModel:
    """知识图谱模型测试"""
    
    def test_entity_creation(self, test_db, test_user):
        """测试实体创建"""
        entity = KnowledgeGraph(
            user_id=test_user.id,
            entity_type="person",
            entity_name="John Doe",
            properties={"age": 30, "city": "Beijing"}
        )
        
        test_db.add(entity)
        test_db.commit()
        test_db.refresh(entity)
        
        assert entity.id is not None
        assert entity.user_id == test_user.id
        assert entity.entity_type == "person"
        assert entity.entity_name == "John Doe"
        assert entity.properties == {"age": 30, "city": "Beijing"}
        assert entity.created_at is not None
        assert entity.updated_at is not None
    
    def test_entity_property_methods(self, test_knowledge_entity):
        """测试实体属性方法"""
        # 测试添加属性
        test_knowledge_entity.add_property("email", "john@example.com")
        assert test_knowledge_entity.properties["email"] == "john@example.com"
        
        # 测试获取属性
        age = test_knowledge_entity.get_property("age")
        assert age == 30
        
        # 测试获取不存在的属性
        phone = test_knowledge_entity.get_property("phone", "N/A")
        assert phone == "N/A"
        
        # 测试删除属性
        test_knowledge_entity.remove_property("age")
        assert "age" not in test_knowledge_entity.properties
    
    def test_entity_to_dict(self, test_knowledge_entity):
        """测试实体转字典"""
        entity_dict = test_knowledge_entity.to_dict()
        
        assert isinstance(entity_dict, dict)
        assert entity_dict["id"] == test_knowledge_entity.id
        assert entity_dict["user_id"] == test_knowledge_entity.user_id
        assert entity_dict["entity_type"] == test_knowledge_entity.entity_type
        assert entity_dict["entity_name"] == test_knowledge_entity.entity_name
        assert entity_dict["properties"] == test_knowledge_entity.properties
        assert "created_at" in entity_dict
        assert "updated_at" in entity_dict


class TestKnowledgeRelationModel:
    """知识关系模型测试"""
    
    def test_relation_creation(self, test_db, test_knowledge_entity):
        """测试关系创建"""
        # 创建另一个实体
        entity2 = KnowledgeGraph(
            user_id=test_knowledge_entity.user_id,
            entity_type="product",
            entity_name="iPhone"
        )
        test_db.add(entity2)
        test_db.commit()
        test_db.refresh(entity2)
        
        # 创建关系
        relation = KnowledgeRelation(
            from_entity_id=test_knowledge_entity.id,
            to_entity_id=entity2.id,
            relation_type="owns",
            weight=0.9,
            properties={"since": "2023-01-01"}
        )
        
        test_db.add(relation)
        test_db.commit()
        test_db.refresh(relation)
        
        assert relation.id is not None
        assert relation.from_entity_id == test_knowledge_entity.id
        assert relation.to_entity_id == entity2.id
        assert relation.relation_type == "owns"
        assert relation.weight == 0.9
        assert relation.properties == {"since": "2023-01-01"}
        assert relation.created_at is not None
    
    def test_relation_methods(self, test_knowledge_relation):
        """测试关系方法"""
        # 测试设置权重
        test_knowledge_relation.set_weight(0.7)
        assert test_knowledge_relation.weight == 0.7
        
        # 测试添加属性
        test_knowledge_relation.add_property("frequency", "daily")
        assert test_knowledge_relation.properties["frequency"] == "daily"
        
        # 测试获取属性
        since = test_knowledge_relation.get_property("since")
        assert since == "2023-01-01"
        
        # 测试删除属性
        test_knowledge_relation.remove_property("since")
        assert "since" not in test_knowledge_relation.properties
    
    def test_relation_to_dict(self, test_knowledge_relation):
        """测试关系转字典"""
        relation_dict = test_knowledge_relation.to_dict()
        
        assert isinstance(relation_dict, dict)
        assert relation_dict["id"] == test_knowledge_relation.id
        assert relation_dict["from_entity_id"] == test_knowledge_relation.from_entity_id
        assert relation_dict["to_entity_id"] == test_knowledge_relation.to_entity_id
        assert relation_dict["relation_type"] == test_knowledge_relation.relation_type
        assert relation_dict["weight"] == test_knowledge_relation.weight
        assert relation_dict["properties"] == test_knowledge_relation.properties
        assert "created_at" in relation_dict
