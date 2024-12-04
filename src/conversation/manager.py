from typing import List, Dict, Optional
from dataclasses import dataclass, field
from ..utils.types import ConversationManager

@dataclass
class Message:
    role: str
    content: str

@dataclass
class Conversation:
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = "You are a helpful assistant. Please respond in English."

class ChatConversationManager(ConversationManager):
    def __init__(self, system_prompt: Optional[str] = None):
        """
        Initialize the conversation manager.
        
        Args:
            system_prompt: Optional custom system prompt
        """
        self.conversation = Conversation(
            system_prompt=system_prompt or Conversation.system_prompt
        )
        # Add system message at initialization
        self.conversation.messages.append(
            Message(role="system", content=self.conversation.system_prompt)
        )
    
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
        Get the full conversation history in a format suitable for the OpenAI API.
        
        Returns:
            List[dict]: List of message dictionaries
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation.messages
        ]
    
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