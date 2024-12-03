from typing import List, Optional
import re
import os
from openai import OpenAI
import wave
from ..utils.types import WakeWordDetector, AudioConfig

class WhisperWakeWordDetector(WakeWordDetector):
    def __init__(
        self,
        client: OpenAI,
        wake_words: List[str],
        temperature: float = 0.2,
        language: str = "en"
    ):
        """
        Initialize the Whisper-based wake word detector.
        
        Args:
            client: OpenAI client instance
            wake_words: List of wake word phrases to detect
            temperature: Whisper API temperature parameter
            language: Language code for transcription
        """
        self.client = client
        # Clean wake words and create variations
        self.wake_words = self._prepare_wake_words(wake_words)
        self.temperature = temperature
        self.language = language
        self.audio_config = AudioConfig(
            sample_rate=44100,
            channels=1,
            chunk_size=1024,
            format=16  # 16-bit audio
        )
    
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
        """
        Detect if the wake word is present in the audio data.
        
        Args:
            audio_data: Raw audio data in bytes
        
        Returns:
            bool: True if wake word is detected, False otherwise
        """
        # Save audio data to temporary file with consistent format
        temp_file = "temp_wake_word.wav"
        try:
            with wave.open(temp_file, "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(audio_data)
            
            # Get file size
            file_size = os.path.getsize(temp_file)
            if file_size < 4096:  # Less than 4KB
                return False
            
            # Transcribe using Whisper
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
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def _transcribe_audio(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio file using Whisper API.
        
        Args:
            audio_file: Path to the audio file
        
        Returns:
            Optional[str]: Transcribed text or None if failed
        """
        try:
            with open(audio_file, "rb") as audio:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language=self.language,
                    response_format="text",
                    temperature=self.temperature
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None 