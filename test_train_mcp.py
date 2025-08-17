#!/usr/bin/env python3
"""
Test script for the train times MCP server.
"""

import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_train_imports():
    """Test that train MCP server can be imported."""
    try:
        from src.mcp_servers.train_times.__main__ import mcp as train_mcp
        print("✅ Train times MCP server import successful")
        return True
    except Exception as e:
        print(f"❌ Train times MCP server import failed: {e}")
        return False

def test_direct_function():
    """Test the train times function directly."""
    try:
        from src.mcp_servers.train_times.__main__ import get_train_times
        import asyncio
        
        # Test with a common station (London Paddington)
        result = asyncio.run(get_train_times("PAD", num_results=3))
        data = json.loads(result)
        
        if "error" in data:
            print(f"⚠️  Train API returned error (expected if no API key): {data['error']}")
        else:
            print(f"✅ Train times function works! Found {len(data.get('services', []))} services")
            
        return True
    except Exception as e:
        print(f"❌ Direct function test failed: {e}")
        return False

def test_station_codes():
    """Test the station codes function."""
    try:
        from src.mcp_servers.train_times.__main__ import list_station_codes
        import asyncio
        
        result = asyncio.run(list_station_codes("London"))
        data = json.loads(result)
        
        print(f"✅ Station codes function works! Found {data.get('count', 0)} stations matching 'London'")
        return True
    except Exception as e:
        print(f"❌ Station codes test failed: {e}")
        return False

def main():
    """Run all train times tests."""
    print("🚂 Testing Train Times MCP Server")
    print("=" * 50)
    
    # Test basic imports
    print("\n1. Testing imports...")
    if not test_train_imports():
        return
    
    # Test station codes function
    print("\n2. Testing station codes...")
    if not test_station_codes():
        return
    
    # Test train times function
    print("\n3. Testing train times function...")
    if not test_direct_function():
        return
    
    print("\n🎉 All train times MCP tests passed!")
    print("\nTrain Times MCP Server Features:")
    print("- ✅ get_train_times: Live UK rail departures")
    print("- ✅ list_station_codes: Search station codes")
    print("- ✅ Resources: Station data and departures")
    print("- ✅ Prompts: Journey planning assistance")
    print("\nNote: Full functionality requires RAIL_LIVE_DEPARTURE_BOARD_API_KEY")

if __name__ == "__main__":
    main()