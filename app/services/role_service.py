"""
角色服务层

提供角色专属的业务逻辑，专注于配置管理和服务初始化
Agent创建和管理由Orchestrator统一负责
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator

from sqlalchemy.orm import Session

from app.core.llm.base import BaseLLM
from app.core.roles.role_manager import role_manager
from app.core.roles.role_config import RoleConfig
from app.core.orchestrator.orchestrator import Orchestrator
from app.core.orchestrator.schemas import OrchestratorRequest
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.services.memory_service import MemoryService
from app.services.knowledge_service import KnowledgeService
from app.dao.memory_dao import MemoryDAO
from app.dao.knowledge_dao import KnowledgeDAO
from app.schemas.message import MessageSend, ChatResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RoleService:
    """
    角色服务 - 轻量级配置层
    
    职责：
    - 角色配置加载
    - 服务层初始化（记忆、知识）
    - 请求转发到Orchestrator
    - Agent创建和管理由Orchestrator统一负责
    """
    
    def __init__(
        self,
        db: Session,
        llm: BaseLLM,
        role_type: str
    ):
        """
        初始化角色服务
        
        Args:
            db: 数据库会话
            llm: 大语言模型实例
            role_type: 角色类型
        """
        self.db = db
        self.llm = llm
        self.role_type = role_type
        
        # 获取角色配置
        self.role_config = role_manager.get_role(role_type)
        
        # 初始化基础服务
        self.conversation_service = ConversationService(db)
        self.message_service = MessageService(db)
        
        # 根据角色配置初始化服务
        self._initialize_services()
        
        # 初始化编排器（统一Agent管理）
        self._initialize_orchestrator()
        
        logger.info(f"角色服务初始化完成: {self.role_config.name} ({role_type})")
    
    def _initialize_services(self):
        """
        根据角色配置初始化服务
        """
        strategy = self.role_config.memory_strategy
        
        # 记忆服务（根据策略决定是否启用）
        if strategy.short_term or strategy.long_term:
            self.memory_service = MemoryService(
                db=self.db,
                llm=self.llm
            )
        else:
            self.memory_service = None
        
        # 知识服务（仅在策略允许时启用）
        if strategy.knowledge_graph:
            knowledge_dao = KnowledgeDAO(self.db)
            memory_dao = MemoryDAO(self.db)
            self.knowledge_service = KnowledgeService(
                db=self.db,
                llm=self.llm,
                knowledge_dao=knowledge_dao,
                memory_dao=memory_dao
            )
        else:
            self.knowledge_service = None
        
        # RAG服务（预留接口）
        if strategy.rag_enabled:
            self.rag_service = None  # 待实现
            logger.info(f"角色 {self.role_type} 启用了RAG，但尚未实现")
        else:
            self.rag_service = None
        
        logger.debug(f"角色服务初始化: 记忆={self.memory_service is not None}, 知识={self.knowledge_service is not None}, RAG={self.rag_service is not None}")
    
    def _initialize_orchestrator(self):
        """
        初始化编排器（统一Agent管理）
        """
        # 创建编排器，工具权限过滤由Orchestrator内部处理
        self.orchestrator = Orchestrator(
            db=self.db,
            llm=self.llm,
            role_config=self.role_config,
            memory_service=self.memory_service,
            knowledge_service=self.knowledge_service
        )
        
        logger.debug("编排器初始化完成（统一Agent管理）")
    
    async def chat(
        self,
        request: MessageSend,
        stream: bool = False
    ) -> ChatResponse:
        """
        处理对话请求（使用编排器）
        
        Args:
            request: 消息请求
            stream: 是否流式输出
            
        Returns:
            ChatResponse: 对话响应
        """
        try:
            # 获取或创建会话
            conversation = await self.conversation_service.get_or_create_conversation(
                user_id=request.user_id,
                title=request.content[:50]
            )
            
            # 保存用户消息
            user_message = await self.message_service.create_message(
                conversation_id=conversation.id,
                role="user",
                content=request.content
            )
            
            # 使用编排器执行请求（记忆系统已集成）
            orchestrator_request = OrchestratorRequest(
                content=request.content,
                conversation_id=conversation.id,
                user_id=request.user_id,
                mode=None,  # 自动路由
                context={}
            )
            
            orchestrator_response = await self.orchestrator.execute(orchestrator_request)
            
            if not orchestrator_response.success:
                raise Exception(f"编排器执行失败: {orchestrator_response.error}")
            
            agent_response = orchestrator_response.content
            
            # 保存助手消息
            assistant_message = await self.message_service.create_message(
                conversation_id=conversation.id,
                role="assistant",
                content=agent_response,
                metadata={
                    "execution_mode": orchestrator_response.mode,
                    "execution_time": orchestrator_response.execution_time,
                    "state_history": orchestrator_response.state_history,
                    "memories_retrieved": orchestrator_response.metadata.get("memories_retrieved", 0),
                    "memory_stored": orchestrator_response.metadata.get("memory_stored", False)
                }
            )
            
            return ChatResponse(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                content=agent_response,
                role="assistant"
            )
            
        except Exception as e:
            logger.error(f"角色 {self.role_type} 对话失败: {e}")
            raise
    
    def get_role_info(self) -> Dict[str, Any]:
        """
        获取角色信息
        
        Returns:
            Dict[str, Any]: 角色信息
        """
        return {
            "name": self.role_config.name,
            "type": self.role_config.type,
            "description": self.role_config.description,
            "memory_strategy": self.role_config.memory_strategy.model_dump(),
            "tools_count": len(self.orchestrator.tool_manager.get_all_tools()) if self.orchestrator else 0
        }
