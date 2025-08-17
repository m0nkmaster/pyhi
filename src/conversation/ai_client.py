"""OpenAI and Anthropic API client wrapper with MCP support."""

from typing import Optional, List, Dict, Any
import logging
import asyncio
import json
from openai import OpenAI
from anthropic import Anthropic

class AIWrapper:
    def __init__(self, config, mcp_manager=None):
        """
        Initialize the AI wrapper.
        
        Args:
            config: Configuration object with API keys and settings
            mcp_manager: Optional MCP manager for MCP-based function calling
        """
        self.config = config
        self.mcp_manager = mcp_manager
        self.openai_client = OpenAI(api_key=config.api_key)
        self.anthropic_client = Anthropic(api_key=config.api_key)
        self.provider = config.provider
        self.model = config.model

    def get_completion(self, messages: List[dict]) -> Dict[str, Any]:
        """Get completion based on the configured chat_provider."""
        # Log the messages being sent to the API
        logging.debug(f"Sending messages to API: {messages}")
        if self.provider == "openai":
            return self._get_completion_openai(messages)
        elif self.provider == "anthropic":
            return self._get_completion_anthropic(messages)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def _get_completion_openai(self, messages: List[dict]) -> Dict[str, Any]:
        """Get completion from OpenAI."""
        try:
            # Get available tools from MCP manager
            tools = None
            if self.mcp_manager:
                tools = self.mcp_manager.get_tools()
            
            # Validate tools format
            if tools:
                logging.debug(f"Using tools: {tools}")
                if not isinstance(tools, list):
                    logging.error("Tools must be a list")
                    tools = None
                else:
                    # Validate each tool has required properties
                    for tool in tools:
                        if not isinstance(tool, dict) or 'type' not in tool or 'function' not in tool:
                            logging.error(f"Invalid tool format: {tool}")
                            tools = None
                            break
            
            # Make API call with improved configuration
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Let the model decide when to call functions
                temperature=0.7,
                max_tokens=500,  # Increased to allow for function responses
                n=1,  # Ensure we only get one completion
            )
            
            # Extract response
            message = response.choices[0].message
            
            # Format response consistently
            formatted_response = {
                "content": message.content,
                "tool_calls": None
            }
            
            # Safely handle tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                formatted_response["tool_calls"] = message.tool_calls
                logging.debug(f"Tool calls in response: {message.tool_calls}")
            
            return formatted_response
            
        except Exception as e:
            logging.error(f"Error getting OpenAI completion: {str(e)}")
            return {
                "content": f"I encountered an error processing your request: {str(e)}",
                "tool_calls": None
            }

    def _get_completion_anthropic(self, messages: List[dict]) -> Dict[str, Any]:
        """Get completion from Anthropic's Claude."""
        try:
            # Get available tools from MCP manager
            tools = None
            if self.mcp_manager:
                mcp_tools = self.mcp_manager.get_tools()
                if mcp_tools:
                    # Convert OpenAI tool format to Anthropic tool format
                    tools = []
                    for tool in mcp_tools:
                        if isinstance(tool, dict) and 'function' in tool:
                            anthropic_tool = {
                                "name": tool['function']['name'],
                                "description": tool['function']['description'],
                                "input_schema": tool['function']['parameters']
                            }
                            tools.append(anthropic_tool)
            
            # Extract system message and prepare messages for Anthropic
            system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
            anthropic_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    continue  # System message handled separately
                elif msg['role'] in ['user', 'assistant']:
                    anthropic_messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
                elif msg['role'] == 'tool':
                    # Convert tool response to user message for Anthropic
                    anthropic_messages.append({
                        "role": "user",
                        "content": f"Tool '{msg.get('name', 'unknown')}' returned: {msg['content']}"
                    })
            
            # Make API call
            kwargs = {
                "model": self.model,
                "system": system_message,
                "messages": anthropic_messages,
                "max_tokens": 500
            }
            
            if tools:
                kwargs["tools"] = tools
            
            response = self.anthropic_client.messages.create(**kwargs)
            
            # Extract content and tool calls
            content = ""
            tool_calls = []
            
            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text
                elif content_block.type == "tool_use":
                    # Convert Anthropic tool use to OpenAI tool_calls format for consistency
                    tool_call = type('ToolCall', (), {
                        'id': content_block.id,
                        'type': 'function',
                        'function': type('Function', (), {
                            'name': content_block.name,
                            'arguments': json.dumps(content_block.input) if not isinstance(content_block.input, str) else content_block.input
                        })()
                    })()
                    tool_calls.append(tool_call)
            
            return {
                "content": content.strip() if content else None,
                "tool_calls": tool_calls if tool_calls else None
            }
            
        except Exception as e:
            logging.error(f"Error getting Anthropic completion: {str(e)}")
            return {
                "content": "I encountered an error processing your request.",
                "tool_calls": None
            }

    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using OpenAI's TTS."""
        # Validate input text
        if not text or not isinstance(text, str) or not text.strip():
            logging.warning("Invalid or empty text provided to text_to_speech, skipping TTS conversion")
            return None

        # Ensure text is properly stripped and has content
        text = text.strip()
        if len(text) < 1:
            logging.warning("Text is too short for TTS conversion")
            return None
        
        try:
            response = self.openai_client.audio.speech.create(
                model=self.config.voice_model,
                voice=self.config.voice,
                input=text
            )
            if not response or not response.content:
                logging.error("Empty response received from TTS API")
                return None
            return response.content
        except Exception as e:
            logging.error(f"Error converting text to speech: {str(e)}")
            return None
