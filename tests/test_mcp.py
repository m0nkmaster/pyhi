import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.mcp_manager import MCPManager
from src.config import MCPConfig, MCPServerConfig


@pytest.fixture
def mcp_config():
    """Create test MCP config with servers"""
    config = MCPConfig()
    config.enabled = True
    config.servers = [
        MCPServerConfig(
            name="test-server",
            command=["python", "-m", "test_server"],
            enabled=True
        )
    ]
    return config


class TestMCPManager:
    def test_initialization(self, mcp_config):
        """Test MCPManager initialization"""
        manager = MCPManager(mcp_config)
        assert manager.config == mcp_config
        assert manager.servers == {}
        assert manager.tools == []


    @pytest.mark.asyncio
    async def test_initialize_disabled(self, mcp_config):
        """Test initialization when MCP is disabled"""
        mcp_config.enabled = False
        manager = MCPManager(mcp_config)
        await manager.initialize()
        assert len(manager.servers) == 0


    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mcp_config):
        """Test calling non-existent tool"""
        manager = MCPManager(mcp_config)
        await manager.initialize()
        
        with pytest.raises(ValueError, match="Tool nonexistent_tool not found"):
            await manager.call_tool("nonexistent_tool", {})


    def test_get_system_prompt_snippet_no_tools(self, mcp_config):
        """Test system prompt snippet with no tools"""
        manager = MCPManager(mcp_config)
        snippet = manager.get_system_prompt_snippet()
        assert snippet == ""


    @pytest.mark.asyncio
    async def test_shutdown(self, mcp_config):
        """Test cleanup of MCP resources"""
        manager = MCPManager(mcp_config)
        await manager.initialize()
        await manager.shutdown()
        assert len(manager.servers) == 0


    @pytest.mark.asyncio
    async def test_server_initialization_error(self, mcp_config):
        """Test handling of server initialization errors"""
        with patch('src.mcp_manager.stdio_client', side_effect=Exception("Connection failed")):
            manager = MCPManager(mcp_config)
            await manager.initialize()
            assert len(manager.servers) == 0