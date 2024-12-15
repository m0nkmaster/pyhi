# Standard library imports
import json
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
import platform
import socket

# Third-party imports
try:
    import requests
except ImportError:
    logging.error("requests package not found. Please install it with: pip install requests")
    requests = None

# Local imports
from ..utils.types import ConversationManager

@dataclass
class Message:
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List] = None
    name: Optional[str] = None

    def __post_init__(self):
        """Validate message properties based on role."""
        valid_roles = ["system", "user", "assistant", "tool"]
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role: {self.role}. Must be one of {valid_roles}")
        
        # Validate tool-specific fields
        if self.role == "tool":
            if not self.name:
                raise ValueError("Tool messages must have a name")
            if not self.tool_call_id:
                raise ValueError("Tool messages must have a tool_call_id")
        
        # Ensure content is never None
        if self.content is None:
            self.content = ""

@dataclass
class Conversation:
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = "You are a helpful assistant. Please respond in English."

class ChatConversationManager(ConversationManager):
    def __init__(self, system_prompt: Optional[str] = None, function_manager=None):
        """
        Initialize the conversation manager.
        
        Args:
            system_prompt: Optional custom system prompt
            function_manager: Optional function manager for handling function calls
        """
        try:
            # Get current context
            current_time = datetime.now()
            timezone = self._get_timezone()
            if timezone:
                current_time = current_time.astimezone(ZoneInfo(timezone))
            
            # Format date and time
            formatted_date = current_time.strftime("%A, %B %d, %Y")
            formatted_time = current_time.strftime("%I:%M %p")
            
            # Get location information
            location = self._get_location()
            
            # Format the system prompt with current context
            try:
                formatted_prompt = (system_prompt or Conversation.system_prompt).format(
                    current_date=formatted_date,
                    current_time=formatted_time,
                    location=location,
                    timezone=timezone or "UTC"
                )
                logging.debug(f"Formatted system prompt: {formatted_prompt}")
            except KeyError as e:
                logging.warning(f"Missing placeholder in system prompt: {e}")
                formatted_prompt = system_prompt or Conversation.system_prompt
            except Exception as e:
                logging.warning(f"Error formatting system prompt: {e}")
                formatted_prompt = system_prompt or Conversation.system_prompt
            
            self.conversation = Conversation(
                system_prompt=formatted_prompt
            )
            self.function_manager = function_manager
            
            # Add system message at initialization
            self.conversation.messages.append(
                Message(role="system", content=self.conversation.system_prompt)
            )
            
        except Exception as e:
            logging.error(f"Error initializing conversation manager: {e}")
            # Fall back to default prompt if initialization fails
            self.conversation = Conversation(
                system_prompt=Conversation.system_prompt
            )
            self.function_manager = function_manager
            self.conversation.messages.append(
                Message(role="system", content=self.conversation.system_prompt)
            )
    
    def _get_timezone(self) -> Optional[str]:
        """Get the system's timezone."""
        try:
            return datetime.now().astimezone().tzname()
        except Exception as e:
            logging.warning(f"Could not determine timezone: {e}")
            return None
    
    def _get_location(self) -> str:
        """Get the approximate location based on IP address."""
        if not requests:
            logging.warning("requests package not available, using fallback location")
            return f"Location of {socket.gethostname()}"
        
        try:
            # First try to get public IP
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                ip = response.json()['ip']
                
                # Then get location from IP
                response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return f"{data.get('city', 'Unknown City')}, {data.get('region', 'Unknown Region')}, {data.get('country_name', 'Unknown Country')}"
            
            # Fallback to hostname
            return f"Location of {socket.gethostname()}"
        except Exception as e:
            logging.warning(f"Could not determine location: {e}")
            return "Unknown Location"
    
    def add_user_message(self, message: str) -> None:
        """
        Add a user message to the conversation history.
        
        Args:
            message: The user's message
        """
        self.conversation.messages.append(Message(role="user", content=message))
    
    def add_assistant_message(self, message: str) -> None:
        """
        Add an assistant message to the conversation history.
        
        Args:
            message: The assistant's message
        """
        self.conversation.messages.append(Message(role="assistant", content=message))
    
    def get_conversation_history(self) -> List[dict]:
        """
        Get the conversation history in a format suitable for the AI API.
        
        Returns:
            List of message dictionaries
        """
        history = []
        for message in self.conversation.messages:
            msg_dict = {"role": message.role, "content": message.content or ""}  # Ensure content is never None
            
            # Add tool calls if present
            if message.tool_calls:
                msg_dict["tool_calls"] = message.tool_calls
                
            # Add name for tool messages (previously function messages)
            if message.role == "tool":  # Changed from 'function' to 'tool'
                msg_dict["name"] = message.name
                
            # Add tool_call_id for tool messages if present
            if message.tool_call_id:
                msg_dict["tool_call_id"] = message.tool_call_id
                
            history.append(msg_dict)
        return history
    
    def clear_history(self) -> None:
        """Clear the conversation history, keeping only the system prompt."""
        self.conversation.messages = [
            Message(role="system", content=self.conversation.system_prompt)
        ]
    
    def get_last_user_message(self) -> Optional[str]:
        """
        Get the most recent user message.
        
        Returns:
            Optional[str]: The last user message or None if no user messages exist
        """
        for message in reversed(self.conversation.messages):
            if message.role == "user":
                return message.content
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """
        Get the most recent assistant message.
        
        Returns:
            Optional[str]: The last assistant message or None if no assistant messages exist
        """
        for message in reversed(self.conversation.messages):
            if message.role == "assistant":
                return message.content
        return None 
    
    def process_assistant_response(self, response: dict) -> str:
        """
        Process the assistant's response, handling any function calls.
        
        Args:
            response: The assistant's response dictionary containing content and tool_calls
            
        Returns:
            str: The processed response message
        """
        if not isinstance(response, dict):
            return str(response)
        
        # Get initial message content and tool calls
        message = response.get("content") or ""  # Ensure content is never None
        tool_calls = response.get("tool_calls", [])
        
        # Log the initial assistant message and tool calls
        logging.debug(f"Assistant message: {message}")
        logging.debug(f"Tool calls: {tool_calls}")
        
        # Add assistant's message to conversation history
        self.conversation.messages.append(
            Message(
                role="assistant",
                content=message,
                tool_calls=tool_calls
            )
        )
        
        # Process any tool calls
        if tool_calls and self.function_manager:
            for tool_call in tool_calls:
                if not hasattr(tool_call, 'type') or tool_call.type != "function":
                    continue
                    
                try:
                    # Safely access function properties
                    if not hasattr(tool_call, 'function'):
                        logging.error("Tool call missing function property")
                        continue
                        
                    function_name = tool_call.function.name
                    # Safely parse arguments with better error handling
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse function arguments: {e}")
                        continue
                    
                    # Call the function with unpacked arguments
                    function_response = self.function_manager.call_function(function_name, **arguments)
                    
                    # Add the tool response message immediately after the assistant message
                    self.conversation.messages.append(
                        Message(
                            role="tool",
                            name=function_name,
                            content=function_response,
                            tool_call_id=tool_call.id
                        )
                    )
                    
                except Exception as e:
                    logging.error(f"Error processing tool call: {e}")
                    continue
        
        return message