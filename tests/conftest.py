"""
测试配置文件
提供测试用的 fixtures 和配置
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.models.user import User
from app.models.conversation import Conversation
from app.models.task import Task
from app.models.memory import MemoryStore
from app.models.knowledge import KnowledgeGraph, KnowledgeRelation


@pytest.fixture(scope="session")
def test_engine():
    """创建测试数据库引擎"""
    # 使用内存 SQLite 数据库进行测试
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """创建测试数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_user(test_db):
    """创建测试用户"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f"test_user_{unique_id}",
        nickname="Test User",
        status=1
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_conversation(test_db, test_user):
    """创建测试会话"""
    conversation = Conversation(
        user_id=test_user.id,
        title="Test Conversation",
        model_provider="deepseek",
        model_name="deepseek-chat",
        status=1,
        message_count=0
    )
    test_db.add(conversation)
    test_db.commit()
    test_db.refresh(conversation)
    return conversation


@pytest.fixture(scope="function")
def test_task(test_db, test_conversation):
    """创建测试任务"""
    task = Task(
        conversation_id=test_conversation.id,
        task_type="plan",
        description="Test task",
        status="pending",
        priority=1
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
    return task


@pytest.fixture(scope="function")
def test_memory(test_db, test_conversation):
    """创建测试记忆"""
    memory = MemoryStore(
        conversation_id=test_conversation.id,
        memory_type="short_term",
        content="Test memory content",
        importance_score=0.5
    )
    test_db.add(memory)
    test_db.commit()
    test_db.refresh(memory)
    return memory


@pytest.fixture(scope="function")
def test_knowledge_entity(test_db, test_user):
    """创建测试知识实体"""
    entity = KnowledgeGraph(
        user_id=test_user.id,
        entity_type="person",
        entity_name="Test Person",
        properties={"age": 30, "city": "Beijing"}
    )
    test_db.add(entity)
    test_db.commit()
    test_db.refresh(entity)
    return entity


@pytest.fixture(scope="function")
def test_knowledge_relation(test_db, test_knowledge_entity):
    """创建测试知识关系"""
    # 创建另一个实体
    entity2 = KnowledgeGraph(
        user_id=test_knowledge_entity.user_id,
        entity_type="product",
        entity_name="Test Product"
    )
    test_db.add(entity2)
    test_db.commit()
    test_db.refresh(entity2)
    
    # 创建关系
    relation = KnowledgeRelation(
        from_entity_id=test_knowledge_entity.id,
        to_entity_id=entity2.id,
        relation_type="owns",
        weight=0.8
    )
    test_db.add(relation)
    test_db.commit()
    test_db.refresh(relation)
    return relation
