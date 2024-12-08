from typing import List, Optional
import re
import os
from difflib import SequenceMatcher
from openai import OpenAI
import wave
from ..utils.types import WordDetector, AudioConfig
from ..config import WordDetectionConfig
import io

class WhisperWordDetector(WordDetector):
    def __init__(
        self,
        client: OpenAI,
        words: List[str],
        config: Optional[WordDetectionConfig] = None,
        audio_config: Optional[AudioConfig] = None
    ):
        """Initialize the Whisper-based word detector."""
        self.client = client
        self.words = self._prepare_words(words)
        self.config = config or WordDetectionConfig()
        self.audio_config = audio_config or AudioConfig()
        self.similarity_threshold = self.config.similarity_threshold
    
    def _prepare_words(self, words: List[str]) -> List[str]:
        """Prepare words with variations."""
        cleaned_words = set()
        for word in words:
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
        """Detect if the word is present in the audio data."""
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
            print(f"DEBUG - Raw transcript: '{transcript}'")
            
            # Remove repeated words (e.g., "hey hey hey")
            words = transcript.split()
            if len(words) > 0:
                unique_words = []
                prev_word = None
                for word in words:
                    if word != prev_word:
                        unique_words.append(word)
                        prev_word = word
                transcript = " ".join(unique_words)
                print(f"DEBUG - Cleaned transcript: '{transcript}'")
            
            # First check for exact matches
            for word in self.words:
                if word == transcript:
                    print(f"DEBUG - Exact match: '{word}'")
                    return True
            
            # Then check if any wake word is fully contained
            for word in self.words:
                if word in transcript and len(word.split()) > 1:  # Only match multi-word phrases
                    print(f"DEBUG - Contains match: '{word}'")
                    return True
            
            # Finally check for fuzzy matches, but only for longer phrases
            for word in self.words:
                if len(word.split()) > 1:  # Only fuzzy match multi-word phrases
                    similarity = self._calculate_similarity(transcript, word)
                    if similarity >= self.similarity_threshold:
                        print(f"DEBUG - Fuzzy match: '{word}' (similarity: {similarity:.2f})")
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error in word detection: {e}")
            return False
    
    def _transcribe_audio(self, audio_data: io.BytesIO) -> Optional[str]:
        """Transcribe audio data using Whisper API."""
        try:
            # Add prompt to help with wake word recognition
            transcript = self.client.audio.transcriptions.create(
                model=self.config.model,
                file=("audio.wav", audio_data),
                language=self.config.language,
                response_format="text",
                temperature=self.config.temperature,
                prompt="The audio may contain wake words like 'hey chat' or 'hi chat'. Listen carefully for these specific phrases."
            )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None