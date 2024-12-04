from typing import List, Dict, Optional
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class ChatConfig:
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 150
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
                max_tokens=self.chat_config.max_tokens,
                temperature=self.chat_config.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error getting chat completion: {e}")
            return None
    
    def text_to_speech(self, text: str, output_file: str = "response.mp3") -> bool:
        """
        Convert text to speech using OpenAI's TTS API.
        
        Args:
            text: Text to convert to speech
            output_file: Path to save the audio file
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not text:
            print("No text to convert to speech")
            return False
        
        try:
            print("Requesting TTS from OpenAI...")
            response = self.client.audio.speech.create(
                model=self.tts_config.model,
                voice=self.tts_config.voice,
                input=text
            )
            
            print(f"Saving audio response to {output_file}")
            response.stream_to_file(output_file)
            return True
            
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            return False
    
    def transcribe_audio(
        self,
        audio_file: str,
        language: str = "en",
        temperature: float = 0.2
    ) -> Optional[str]:
        """
        Transcribe audio using OpenAI's Whisper API.
        
        Args:
            audio_file: Path to the audio file
            language: Language code
            temperature: Sampling temperature
        
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        try:
            with open(audio_file, "rb") as audio:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language=language,
                    response_format="text",
                    temperature=temperature
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None 