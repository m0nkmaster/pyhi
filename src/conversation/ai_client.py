from typing import Optional, List
import os
from openai import OpenAI
from anthropic import Anthropic

class AIWrapper:
    def __init__(self, config):
        """Initialize the AI wrapper with configuration."""
        self.config = config
        self.openai_client = OpenAI(api_key=config.openai_api_key)
        self.anthropic_client = Anthropic(api_key=config.anthropic_api_key)
        self.chat_provider = config.chat_provider
        self.chat_model = config.chat_model

    def get_completion(self, messages: List[dict]) -> str:
        """Get completion based on the configured chat_provider."""
        if self.chat_provider == "openai":
            return self._get_completion_openai(messages)
        elif self.chat_provider == "claude":
            return self._get_completion_anthropic(messages)
        else:
            raise ValueError(f"Unsupported AI chat_provider: {self.chat_provider}")

    def _get_completion_openai(self, messages: List[dict]) -> str:
        """Get completion from OpenAI."""
        response = self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content

    def _get_completion_anthropic(self, messages: List[dict]) -> str:
        """Get completion from Anthropic's Claude."""
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
        return response.content[0].text

    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using OpenAI's TTS (always uses OpenAI regardless of chat_provider)."""
        try:
            response = self.openai_client.audio.speech.create(
                model=self.config.voice_model,
                voice=self.config.voice,
                input=text
            )
            
            return response.content
            
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return None
