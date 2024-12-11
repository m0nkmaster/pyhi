from typing import List, Dict, Optional
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"
    max_completion_tokens: int = 150
    temperature: float = 0.7

@dataclass
class TTSConfig:
    model: str = "tts-1"
    voice: str = "nova"

class OpenAIWrapper:
    def __init__(
        self,
        client: OpenAI,
        chat_config: Optional[ChatConfig] = None,
        tts_config: Optional[TTSConfig] = None
    ):
        """
        Initialize the OpenAI wrapper.
        
        Args:
            client: OpenAI client instance
            chat_config: Configuration for chat completion
            tts_config: Configuration for text-to-speech
        """
        self.client = client
        self.chat_config = chat_config or ChatConfig()
        self.tts_config = tts_config or TTSConfig()
    
    def get_chat_completion(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Get a chat completion from the OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
        
        Returns:
            Optional[str]: The assistant's response or None if the request failed
        """
        try:
            response = self.client.chat.completions.create(
                model=self.chat_config.model,
                messages=messages,
                max_completion_tokens=self.chat_config.max_completion_tokens,
                temperature=self.chat_config.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting chat completion: {e}")
            return None
    
    def text_to_speech(self, text: str, output_file: str = "response.mp3") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI's TTS API.
        
        Args:
            text: Text to convert to speech
            output_file: Path to save the audio file
        
        Returns:
            Optional[bytes]: Audio data if successful, None if failed
        """
        if not text:
            print("No text to convert to speech")
            return None
        
        try:
            print("Requesting TTS from OpenAI...")
            response = self.client.audio.speech.create(
                model=self.tts_config.model,
                voice=self.tts_config.voice,
                input=text,
                speed=1.2,  # Slightly faster playback
                response_format="mp3"  # Explicit format
            )
            
            # Get audio data directly in memory
            audio_data = response.read()
            
            # Save to file for backup/debugging
            with open(output_file, "wb") as f:
                f.write(audio_data)
            
            return audio_data
            
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return None