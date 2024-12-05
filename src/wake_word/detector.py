from typing import List, Optional
import re
import os
from difflib import SequenceMatcher
from openai import OpenAI
import wave
from ..utils.types import WakeWordDetector, AudioConfig
from ..config import WakeWordConfig
import io

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
        try:
            # Check minimum size
            if len(audio_data) < self.config.min_audio_size:
                return False
            
            # Create in-memory WAV file
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(audio_data)
            
            # Get the WAV data and rewind buffer
            wav_buffer.seek(0)
            
            transcript = self._transcribe_audio(wav_buffer)
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
    
    def _transcribe_audio(self, audio_data: io.BytesIO) -> Optional[str]:
        """Transcribe audio data using Whisper API."""
        try:
            transcript = self.client.audio.transcriptions.create(
                model=self.config.model,
                file=("audio.wav", audio_data),  # Pass as tuple with filename and data
                language=self.config.language,
                response_format="text",
                temperature=self.config.temperature
            )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None