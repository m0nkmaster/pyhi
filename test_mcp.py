#!/usr/bin/env python3
"""
Simple test script to verify MCP integration works.
"""

import asyncio
import logging
from src.config import AppConfig
from src.mcp_manager import MCPManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_manager():
    """Test the MCP manager functionality."""
    try:
        # Create app config with MCP enabled
        app_config = AppConfig()
        print(f"MCP enabled: {app_config.mcp_config.enabled}")
        print(f"MCP servers configured: {len(app_config.mcp_config.servers)}")
        
        if not app_config.mcp_config.enabled:
            print("MCP is disabled in configuration")
            return
        
        # Create MCP manager
        print("\nCreating MCP manager...")
        mcp_manager = MCPManager(app_config.mcp_config)
        
        # Initialize (this would normally connect to servers)
        print("MCP manager created successfully!")
        print("Note: Server connections would normally happen here, but we're just testing the setup")
        
        # Test tool listing (should be empty since no servers connected)
        tools = mcp_manager.get_tools()
        print(f"Tools available: {len(tools)}")
        
        return True
        
    except Exception as e:
        logger.error(f"MCP test failed: {e}", exc_info=True)
        return False

def test_imports():
    """Test that all required imports work."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.server import FastMCP
        print("✅ All MCP imports successful")
        return True
    except Exception as e:
        print(f"❌ MCP import failed: {e}")
        return False

def test_server_imports():
    """Test that MCP servers can be imported."""
    try:
        from src.mcp_servers.weather.__main__ import mcp as weather_mcp
        print("✅ Weather MCP server import successful")
        
        from src.mcp_servers.alarms.__main__ import mcp as alarms_mcp  
        print("✅ Alarms MCP server import successful")
        
        return True
    except Exception as e:
        print(f"❌ MCP server import failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧪 Testing PyHi MCP Integration")
    print("=" * 50)
    
    # Test basic imports
    print("\n1. Testing MCP imports...")
    if not test_imports():
        return
    
    # Test server imports
    print("\n2. Testing MCP server imports...")
    if not test_server_imports():
        return
    
    # Test MCP manager
    print("\n3. Testing MCP manager...")
    if not await test_mcp_manager():
        return
    
    print("\n🎉 All tests passed! MCP integration is ready.")
    print("\nNext steps:")
    print("- Set TOMORROW_IO_API_KEY in .env for weather functionality")
    print("- Run the main app with: python -m src.app")

if __name__ == "__main__":
    asyncio.run(main())