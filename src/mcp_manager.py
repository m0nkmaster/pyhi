"""
MCP Manager for handling MCP server connections and tool management.
"""

import asyncio
import json
import logging
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import asdict

try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
except ImportError:
    raise ImportError("MCP library not installed. Run: pip install mcp")

from .config import MCPConfig, MCPServerConfig


class MCPManager:
    """Manages MCP server connections and provides unified tool interface."""
    
    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP manager.
        
        Args:
            config: MCP configuration containing server definitions
        """
        self.config = config
        self.servers: Dict[str, Dict[str, Any]] = {}  # server_name -> server_info
        self.tools: List[dict] = []
        self.resources: List[dict] = []
        self.prompts: List[dict] = []
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initializing MCPManager with {len(config.servers)} servers")
        
        # Initialization will be done via the initialize() method

    async def initialize(self) -> None:
        """Initialize and connect to all enabled MCP servers."""
        if not self.config.enabled:
            self.logger.info("MCP is disabled in configuration")
            return
            
        self.logger.info("Starting MCP server connections...")
        for server_config in self.config.servers:
            if server_config.enabled:
                await self._connect_server(server_config)
        
        self.logger.info(f"MCP initialization complete. {len(self.servers)} servers connected.")

    async def _connect_server(self, server_config: MCPServerConfig) -> None:
        """
        Connect to a single MCP server.
        
        Args:
            server_config: Configuration for the server to connect to
        """
        try:
            self.logger.info(f"Connecting to MCP server: {server_config.name}")
            
            # Create server parameters for stdio transport
            server_params = StdioServerParameters(
                command=server_config.executable,
                args=server_config.args,
                env=server_config.env
            )
            
            # Create stdio client connection
            async with stdio_client(server_params) as (read_stream, write_stream):
                # Create client session
                session = ClientSession(read_stream, write_stream)
                await session.initialize()
                
                # Get server capabilities
                tools = await session.list_tools()
                resources = await session.list_resources() 
                prompts = await session.list_prompts()
                
                # Store server info
                self.servers[server_config.name] = {
                    "session": session,
                    "config": server_config,
                    "tools": tools.tools if tools else [],
                    "resources": resources.resources if resources else [],
                    "prompts": prompts.prompts if prompts else []
                }
                
                # Add to global collections
                if tools:
                    for tool in tools.tools:
                        # Convert MCP tool to OpenAI-compatible format
                        openai_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        }
                        self.tools.append(openai_tool)
                
                if resources:
                    self.resources.extend(resources.resources)
                    
                if prompts:
                    self.prompts.extend(prompts.prompts)
                
                self.logger.info(
                    f"Connected to {server_config.name}: "
                    f"{len(tools.tools) if tools else 0} tools, "
                    f"{len(resources.resources) if resources else 0} resources, "
                    f"{len(prompts.prompts) if prompts else 0} prompts"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server {server_config.name}: {e}")
            # Don't raise - continue with other servers

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the appropriate MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Result from the tool call
            
        Raises:
            ValueError: If tool is not found
        """
        # Find which server has this tool
        server_info = None
        for server_name, info in self.servers.items():
            for tool in info["tools"]:
                if tool.name == tool_name:
                    server_info = info
                    break
            if server_info:
                break
        
        if not server_info:
            self.logger.error(f"Tool {tool_name} not found in any connected MCP server")
            raise ValueError(f"Tool {tool_name} not found")
        
        try:
            self.logger.debug(f"Calling tool {tool_name} with arguments: {arguments}")
            session = server_info["session"]
            
            result = await session.call_tool(tool_name, arguments)
            
            self.logger.debug(f"Tool {tool_name} returned: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            raise

    def get_tools(self) -> List[dict]:
        """
        Return all tools in OpenAI's function calling format.
        
        Returns:
            List of tool definitions compatible with OpenAI function calling
        """
        self.logger.debug(f"Returning {len(self.tools)} tools from MCP servers")
        return self.tools

    def get_resources(self) -> List[dict]:
        """
        Return all available resources from MCP servers.
        
        Returns:
            List of resource definitions
        """
        return self.resources

    def get_prompts(self) -> List[dict]:
        """
        Return all available prompts from MCP servers.
        
        Returns:
            List of prompt definitions
        """
        return self.prompts

    async def read_resource(self, uri: str) -> str:
        """
        Read a resource from the appropriate MCP server.
        
        Args:
            uri: Resource URI to read
            
        Returns:
            Resource content as string
        """
        # Find which server has this resource
        server_info = None
        for server_name, info in self.servers.items():
            for resource in info["resources"]:
                if resource.uri == uri:
                    server_info = info
                    break
            if server_info:
                break
        
        if not server_info:
            raise ValueError(f"Resource {uri} not found")
        
        session = server_info["session"]
        result = await session.read_resource(uri)
        return result.contents[0].text if result.contents else ""

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a prompt from the appropriate MCP server.
        
        Args:
            name: Prompt name
            arguments: Optional arguments for the prompt
            
        Returns:
            Prompt content as string
        """
        # Find which server has this prompt
        server_info = None
        for server_name, info in self.servers.items():
            for prompt in info["prompts"]:
                if prompt.name == name:
                    server_info = info
                    break
            if server_info:
                break
        
        if not server_info:
            raise ValueError(f"Prompt {name} not found")
        
        session = server_info["session"]
        result = await session.get_prompt(name, arguments or {})
        return result.messages[0].content.text if result.messages else ""

    def get_system_prompt_snippet(self) -> str:
        """
        Generate a system prompt snippet describing available tools.
        
        Returns:
            A string describing the available tools
        """
        if not self.tools:
            self.logger.debug("No tools available for system prompt")
            return ""
            
        self.logger.debug(f"Generating system prompt snippet for {len(self.tools)} tools")
        prompt = "Available functions:\n\n"
        for tool in self.tools:
            func = tool["function"]
            prompt += f"- {func['name']}: {func['description']}\n"
        return prompt

    async def shutdown(self) -> None:
        """Shutdown all MCP server connections."""
        self.logger.info("Shutting down MCP server connections...")
        
        for server_name, server_info in self.servers.items():
            try:
                session = server_info["session"]
                await session.close()
                self.logger.info(f"Closed connection to {server_name}")
            except Exception as e:
                self.logger.error(f"Error closing connection to {server_name}: {e}")
        
        self.servers.clear()
        self.tools.clear()
        self.resources.clear()
        self.prompts.clear()
        
        self.logger.info("MCP shutdown complete")

    def __del__(self):
        """Cleanup when manager is destroyed."""
        if self.servers:
            # Try to cleanup synchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule cleanup
                    loop.create_task(self.shutdown())
                else:
                    # If no loop, run cleanup
                    loop.run_until_complete(self.shutdown())
            except Exception as e:
                self.logger.error(f"Error during MCPManager cleanup: {e}")


