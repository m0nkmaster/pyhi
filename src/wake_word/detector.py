from typing import List, Optional
import re
import os
from difflib import SequenceMatcher
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
        self.similarity_threshold = 0.85  # Adjust this value between 0 and 1
    
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
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity ratio."""
        return SequenceMatcher(None, str1, str2).ratio()
    
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
            
            # Check for wake word matches with fuzzy matching
            for wake_word in self.wake_words:
                similarity = self._calculate_similarity(transcript, wake_word)
                if similarity >= self.similarity_threshold:
                    print(f"Wake word match: '{wake_word}' (similarity: {similarity:.2f})")
                    return True
                
                # Check if wake word is contained within a longer phrase
                if wake_word in transcript:
                    print(f"Wake word contained in transcript: '{wake_word}'")
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