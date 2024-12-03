from typing import List, Optional
import re
import os
from openai import OpenAI
import wave
from ..utils.types import WakeWordDetector, AudioConfig
from ..config import WakeWordConfig

class WhisperWakeWordDetector(WakeWordDetector):
    def __init__(
        self,
        client: OpenAI,
        wake_words: List[str],
        config: Optional[WakeWordConfig] = None,
        audio_config: Optional[AudioConfig] = None
    ):
        """Initialize the Whisper-based wake word detector."""
        self.client = client
        self.wake_words = self._prepare_wake_words(wake_words)
        self.config = config or WakeWordConfig()
        self.audio_config = audio_config or AudioConfig()
    
    def _prepare_wake_words(self, wake_words: List[str]) -> List[str]:
        """Prepare wake words with variations."""
        cleaned_words = set()
        for word in wake_words:
            # Clean the original word
            cleaned = self._clean_text(word)
            cleaned_words.add(cleaned)
            
            # Add variation without punctuation
            no_punct = re.sub(r'[,.]', '', cleaned)
            cleaned_words.add(no_punct)
        
        return list(cleaned_words)
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace and converting to lowercase."""
        return ' '.join(text.lower().split())
    
    def detect(self, audio_data: bytes) -> bool:
        """Detect if the wake word is present in the audio data."""
        temp_file = "temp_wake_word.wav"
        try:
            with wave.open(temp_file, "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(audio_data)
            
            # Check minimum file size
            if os.path.getsize(temp_file) < self.config.min_audio_size:
                return False
            
            transcript = self._transcribe_audio(temp_file)
            if not transcript:
                return False
            
            # Clean transcript
            transcript = self._clean_text(transcript)
            print(f"Transcript: '{transcript}'")
            
            # Remove punctuation for comparison
            transcript_no_punct = re.sub(r'[,.]', '', transcript)
            
            # Check for exact wake word matches
            for wake_word in self.wake_words:
                if transcript == wake_word or transcript_no_punct == wake_word:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error in wake word detection: {e}")
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe audio file using Whisper API."""
        try:
            with open(audio_file, "rb") as audio:
                transcript = self.client.audio.transcriptions.create(
                    model=self.config.model,
                    file=audio,
                    language=self.config.language,
                    response_format="text",
                    temperature=self.config.temperature
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None 