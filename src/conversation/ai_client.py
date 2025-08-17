"""OpenAI and Anthropic API client wrapper with MCP support."""

from typing import Optional, List, Dict, Any
import logging
import asyncio
from openai import OpenAI
from anthropic import Anthropic

class AIWrapper:
    def __init__(self, config, function_manager=None, mcp_manager=None):
        """
        Initialize the AI wrapper.
        
        Args:
            config: Configuration object with API keys and settings
            function_manager: Optional legacy function manager for backward compatibility
            mcp_manager: Optional MCP manager for MCP-based function calling
        """
        self.config = config
        self.function_manager = function_manager  # Legacy support
        self.mcp_manager = mcp_manager  # New MCP support
        self.openai_client = OpenAI(api_key=config.openai_api_key)
        self.anthropic_client = Anthropic(api_key=config.anthropic_api_key)
        self.chat_provider = config.chat_provider
        self.chat_model = config.chat_model

    def get_completion(self, messages: List[dict]) -> Dict[str, Any]:
        """Get completion based on the configured chat_provider."""
        # Log the messages being sent to the API
        logging.debug(f"Sending messages to API: {messages}")
        if self.chat_provider == "openai":
            return self._get_completion_openai(messages)
        elif self.chat_provider == "claude":
            return self._get_completion_anthropic(messages)
        else:
            raise ValueError(f"Unsupported AI chat_provider: {self.chat_provider}")

    def _get_completion_openai(self, messages: List[dict]) -> Dict[str, Any]:
        """Get completion from OpenAI."""
        try:
            # Get available tools from MCP manager or legacy function manager
            tools = None
            if self.mcp_manager:
                tools = self.mcp_manager.get_tools()
            elif self.function_manager:
                tools = self.function_manager.get_tools()
            
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
                model=self.chat_model,
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
            # Extract system message and user messages
            system_message = next((msg['content'] for msg in messages if msg['role'] == 'system'), None)
            user_messages = [
                {"role": "user", "content": msg['content']}
                for msg in messages if msg['role'] == 'user'
            ]
            
            response = self.anthropic_client.messages.create(
                model=self.chat_model,
                system=system_message,
                messages=user_messages,
                max_tokens=150
            )
            
            # Format response consistently
            return {
                "content": response.content[0].text,
                "tool_calls": None  # Anthropic doesn't support function calling yet
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
