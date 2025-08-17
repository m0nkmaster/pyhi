import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from src.mcp_manager import MCPManager
from src.config import Config


@pytest.fixture
def config():
    """Create test config with MCP servers"""
    from src.config import Config, MCPServerConfig
    config = Config()
    config.mcp.enabled = True
    config.mcp.servers = [
        MCPServerConfig(
            name="test-server",
            command=["python", "-m", "test_server"],
            enabled=True
        ),
        MCPServerConfig(
            name="disabled-server", 
            command=["python", "-m", "disabled_server"],
            enabled=False
        )
    ]
    return config


@pytest.fixture
def mock_client_session():
    """Mock MCP client session"""
    session = Mock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=[])
    session.call_tool = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


class TestMCPManager:
    def test_initialization(self, config):
        """Test MCPManager initialization"""
        manager = MCPManager(config.mcp)
        assert manager.config == config.mcp
        assert manager.servers == {}
        assert manager.tools == []


    @pytest.mark.asyncio
    async def test_initialize_with_servers(self, config, mock_client_session):
        """Test initializing MCP manager with servers"""
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            # Should only initialize enabled servers
            assert len(manager.servers) == 1
            assert "test-server" in manager.servers
            assert "disabled-server" not in manager.servers


    @pytest.mark.asyncio 
    async def test_initialize_disabled(self, config):
        """Test initialization when MCP is disabled"""
        config.mcp.enabled = False
        manager = MCPManager(config.mcp)
        await manager.initialize()
        
        # Should not initialize any servers
        assert len(manager.servers) == 0


    @pytest.mark.asyncio
    async def test_get_available_tools(self, config, mock_client_session):
        """Test getting available tools from servers"""
        # Mock tools response
        mock_tools = [
            {
                "name": "test_tool_1",
                "description": "Test tool 1",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "test_tool_2", 
                "description": "Test tool 2",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        mock_client_session.list_tools.return_value = mock_tools
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            tools = manager.get_available_tools()
            
            # Should return tools in OpenAI format
            assert len(tools) == 2
            assert tools[0]["type"] == "function"
            assert tools[0]["function"]["name"] == "test_tool_1"
            assert tools[1]["function"]["name"] == "test_tool_2"


    @pytest.mark.asyncio
    async def test_call_tool_success(self, config, mock_client_session):
        """Test successful tool call"""
        # Mock tool response
        mock_response = Mock()
        mock_response.content = [Mock(text="Tool executed successfully")]
        mock_client_session.call_tool.return_value = mock_response
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            # Mock that the tool belongs to test-server
            manager.tool_server_map = {"test_tool": "test-server"}
            
            result = await manager.call_tool("test_tool", {"param": "value"})
            
            mock_client_session.call_tool.assert_called_once_with(
                "test_tool", {"param": "value"}
            )
            assert result == mock_response


    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, config):
        """Test calling non-existent tool"""
        manager = MCPManager(config.mcp)
        await manager.initialize()
        
        with pytest.raises(ValueError, match="Tool 'nonexistent_tool' not found"):
            await manager.call_tool("nonexistent_tool", {})


    @pytest.mark.asyncio
    async def test_call_tool_server_error(self, config, mock_client_session):
        """Test tool call when server raises error"""
        mock_client_session.call_tool.side_effect = Exception("Server error")
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            manager.tool_server_map = {"test_tool": "test-server"}
            
            with pytest.raises(Exception, match="Server error"):
                await manager.call_tool("test_tool", {})


    @pytest.mark.asyncio
    async def test_cleanup(self, config, mock_client_session):
        """Test cleanup of MCP resources"""
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            await manager.cleanup()
            
            # Should cleanup all server sessions
            assert len(manager.servers) == 0


    @pytest.mark.asyncio
    async def test_server_initialization_error(self, config):
        """Test handling of server initialization errors"""
        with patch('src.mcp_manager.stdio_client', side_effect=Exception("Connection failed")):
            manager = MCPManager(config.mcp)
            
            # Should handle error gracefully
            await manager.initialize()
            
            # Should continue with no servers initialized
            assert len(manager.servers) == 0


    def test_tool_schema_conversion(self, config):
        """Test conversion of MCP tool schema to OpenAI format"""
        manager = MCPManager(config.mcp)
        
        mcp_tool = {
            "name": "get_weather",
            "description": "Get weather information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
        
        openai_tool = manager._convert_tool_to_openai_format(mcp_tool)
        
        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "get_weather"
        assert openai_tool["function"]["description"] == "Get weather information"
        assert openai_tool["function"]["parameters"] == mcp_tool["inputSchema"]


class TestMCPServerIntegration:
    @pytest.mark.asyncio
    async def test_multiple_servers(self, config):
        """Test managing multiple MCP servers"""
        # Add more servers to config
        config.mcp.servers.extend([
            {
                "name": "weather-server",
                "command": ["python", "-m", "weather"],
                "enabled": True
            },
            {
                "name": "calendar-server", 
                "command": ["python", "-m", "calendar"],
                "enabled": True
            }
        ])
        
        # Mock multiple client sessions
        def create_mock_session(server_name):
            session = Mock()
            session.initialize = AsyncMock()
            session.list_tools = AsyncMock(return_value=[
                {
                    "name": f"{server_name}_tool",
                    "description": f"Tool from {server_name}",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ])
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            return session
        
        with patch('src.mcp_manager.stdio_client') as mock_stdio:
            # Return different sessions for different servers
            mock_stdio.side_effect = [
                create_mock_session("test"),
                create_mock_session("weather"), 
                create_mock_session("calendar")
            ]
            
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            # Should have all enabled servers
            assert len(manager.servers) == 3
            assert "test-server" in manager.servers
            assert "weather-server" in manager.servers  
            assert "calendar-server" in manager.servers
            
            # Should have tools from all servers
            tools = manager.get_available_tools()
            assert len(tools) == 3
            
            tool_names = [tool["function"]["name"] for tool in tools]
            assert "test_tool" in tool_names
            assert "weather_tool" in tool_names
            assert "calendar_tool" in tool_names


    @pytest.mark.asyncio
    async def test_server_reconnection(self, config, mock_client_session):
        """Test server reconnection after failure"""
        # First call succeeds, second fails, third succeeds
        mock_client_session.call_tool.side_effect = [
            Mock(content=[Mock(text="Success")]),
            Exception("Connection lost"),
            Mock(content=[Mock(text="Reconnected")])
        ]
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            manager.tool_server_map = {"test_tool": "test-server"}
            
            # First call should succeed
            result1 = await manager.call_tool("test_tool", {})
            assert result1.content[0].text == "Success"
            
            # Second call should fail
            with pytest.raises(Exception, match="Connection lost"):
                await manager.call_tool("test_tool", {})


    @pytest.mark.asyncio
    async def test_tool_discovery_update(self, config, mock_client_session):
        """Test updating tool discovery from servers"""
        # Initial tools
        initial_tools = [
            {
                "name": "tool1",
                "description": "Tool 1", 
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        
        # Updated tools 
        updated_tools = [
            {
                "name": "tool1",
                "description": "Tool 1",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "tool2", 
                "description": "Tool 2",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        
        mock_client_session.list_tools.side_effect = [initial_tools, updated_tools]
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            # Should have 1 tool initially
            tools = manager.get_available_tools()
            assert len(tools) == 1
            
            # Re-discover tools
            await manager._discover_tools()
            
            # Should have 2 tools after update
            tools = manager.get_available_tools()
            assert len(tools) == 2


class TestMCPManagerErrorHandling:
    @pytest.mark.asyncio
    async def test_malformed_server_config(self, config):
        """Test handling malformed server configuration"""
        # Add malformed server config
        config.mcp.servers.append({
            "name": "malformed-server"
            # Missing command and enabled
        })
        
        manager = MCPManager(config.mcp)
        
        # Should handle malformed config gracefully
        await manager.initialize()
        
        # Should still initialize valid servers
        assert "test-server" in manager.servers


    @pytest.mark.asyncio
    async def test_server_timeout(self, config):
        """Test handling server timeout"""
        with patch('src.mcp_manager.stdio_client') as mock_stdio:
            mock_stdio.side_effect = asyncio.TimeoutError("Server timeout")
            
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            # Should continue with no servers
            assert len(manager.servers) == 0


    @pytest.mark.asyncio
    async def test_invalid_tool_response(self, config, mock_client_session):
        """Test handling invalid tool response format"""
        # Mock invalid tool list response
        mock_client_session.list_tools.return_value = [
            {
                "name": "valid_tool",
                "description": "Valid tool",
                "inputSchema": {"type": "object"}
            },
            {
                # Missing required fields
                "description": "Invalid tool"
            }
        ]
        
        with patch('src.mcp_manager.stdio_client', return_value=mock_client_session):
            manager = MCPManager(config.mcp)
            await manager.initialize()
            
            tools = manager.get_available_tools()
            
            # Should only include valid tools
            assert len(tools) == 1
            assert tools[0]["function"]["name"] == "valid_tool"