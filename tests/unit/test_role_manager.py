"""
角色管理器单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.roles.role_config import RoleConfig, MemoryStrategy
from app.core.roles.role_manager import RoleManager


class TestRoleConfig:
    """测试角色配置类"""
    
    def test_memory_strategy_creation(self):
        """测试记忆策略创建"""
        strategy = MemoryStrategy(
            short_term=True,
            long_term=False,
            knowledge_graph=False,
            user_isolated=False,
            rag_enabled=True,
            retention_days=1
        )
        
        assert strategy.short_term is True
        assert strategy.long_term is False
        assert strategy.knowledge_graph is False
        assert strategy.rag_enabled is True
        assert strategy.retention_days == 1
    
    def test_role_config_creation(self):
        """测试角色配置创建"""
        role = RoleConfig(
            name="测试角色",
            type="test",
            description="测试用角色",
            system_prompt="你是测试助手",
            allowed_tools=["mysql_query", "web_search"],
            memory_strategy=MemoryStrategy(
                short_term=True,
                long_term=False
            )
        )
        
        assert role.name == "测试角色"
        assert role.type == "test"
        assert len(role.allowed_tools) == 2
        assert role.memory_strategy.short_term is True
    
    def test_is_tool_allowed_wildcard(self):
        """测试工具权限检查 - 通配符"""
        role = RoleConfig(
            name="测试角色",
            type="test",
            allowed_tools=["*"]
        )
        
        assert role.is_tool_allowed("any_tool") is True
        assert role.is_tool_allowed("mysql_query") is True
    
    def test_is_tool_allowed_exact_match(self):
        """测试工具权限检查 - 精确匹配"""
        role = RoleConfig(
            name="测试角色",
            type="test",
            allowed_tools=["mysql_query", "web_search"]
        )
        
        assert role.is_tool_allowed("mysql_query") is True
        assert role.is_tool_allowed("web_search") is True
        assert role.is_tool_allowed("file_read") is False
    
    def test_is_tool_allowed_prefix_match(self):
        """测试工具权限检查 - 前缀匹配"""
        role = RoleConfig(
            name="测试角色",
            type="test",
            allowed_tools=["mysql_*", "web_*"]
        )
        
        assert role.is_tool_allowed("mysql_query") is True
        assert role.is_tool_allowed("mysql_execute") is True
        assert role.is_tool_allowed("web_search") is True
        assert role.is_tool_allowed("file_read") is False


class TestRoleManager:
    """测试角色管理器"""
    
    def test_role_manager_singleton(self):
        """测试角色管理器单例模式"""
        manager1 = RoleManager()
        manager2 = RoleManager()
        assert manager1 is manager2
    
    def test_get_role_general(self):
        """测试获取通用助手角色"""
        manager = RoleManager()
        role = manager.get_role("general")
        
        assert role is not None
        assert role.type == "general"
        assert role.name == "通用助手"
        assert role.memory_strategy.long_term is True
        assert role.memory_strategy.knowledge_graph is True
    
    def test_get_role_customer_service(self):
        """测试获取电商客服角色"""
        manager = RoleManager()
        role = manager.get_role("customer_service")
        
        assert role is not None
        assert role.type == "customer_service"
        assert role.name == "电商客服"
        assert role.memory_strategy.long_term is False
        assert role.memory_strategy.knowledge_graph is False
        assert role.memory_strategy.rag_enabled is True
    
    def test_get_role_nonexistent(self):
        """测试获取不存在的角色（应返回默认角色）"""
        manager = RoleManager()
        role = manager.get_role("nonexistent")
        
        assert role is not None
        assert role.type == "default"
        assert role.name == "默认助手"
    
    def test_list_roles(self):
        """测试列出所有角色"""
        manager = RoleManager()
        roles = manager.list_roles()
        
        assert isinstance(roles, list)
        assert len(roles) >= 2  # 至少有通用助手和电商客服
        
        # 检查角色信息结构
        for role in roles:
            assert "type" in role
            assert "name" in role
            assert "description" in role
    
    def test_filter_tools_wildcard(self):
        """测试工具过滤 - 通配符（通用助手）"""
        manager = RoleManager()
        
        # 创建模拟工具
        mock_tools = [
            Mock(name="mysql_query"),
            Mock(name="web_search"),
            Mock(name="file_read")
        ]
        
        filtered = manager.filter_tools("general", mock_tools)
        
        # 通用助手允许所有工具
        assert len(filtered) == len(mock_tools)
    
    def test_filter_tools_restricted(self):
        """测试工具过滤 - 受限（电商客服）"""
        manager = RoleManager()
        
        # 创建模拟工具
        mock_tools = [
            Mock(name="mysql_query"),
            Mock(name="web_search"),
            Mock(name="file_read"),
            Mock(name="code_execute")
        ]
        
        filtered = manager.filter_tools("customer_service", mock_tools)
        
        # 电商客服只允许mysql_query和web_search
        assert len(filtered) == 2
        filtered_names = [tool.name for tool in filtered]
        assert "mysql_query" in filtered_names
        assert "web_search" in filtered_names
        assert "file_read" not in filtered_names
    
    def test_get_memory_strategy(self):
        """测试获取记忆策略"""
        manager = RoleManager()
        
        # 通用助手策略
        general_strategy = manager.get_memory_strategy("general")
        assert general_strategy["long_term"] is True
        assert general_strategy["knowledge_graph"] is True
        
        # 电商客服策略
        cs_strategy = manager.get_memory_strategy("customer_service")
        assert cs_strategy["long_term"] is False
        assert cs_strategy["knowledge_graph"] is False
        assert cs_strategy["rag_enabled"] is True
    
    def test_get_system_prompt(self):
        """测试获取系统提示词"""
        manager = RoleManager()
        
        # 通用助手提示词
        general_prompt = manager.get_system_prompt("general")
        assert "智能通用助手" in general_prompt
        assert len(general_prompt) > 50
        
        # 电商客服提示词
        cs_prompt = manager.get_system_prompt("customer_service")
        assert "电商" in cs_prompt or "客服" in cs_prompt
        assert len(cs_prompt) > 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
