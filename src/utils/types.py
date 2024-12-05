from typing import Protocol, List, Optional
from dataclasses import dataclass
from ..config import AudioConfig  # Import from config instead

@dataclass
class AudioFrame:
    data: bytes
    is_speech: bool

class AudioRecorder(Protocol):
    def start_recording(self) -> None:
        """Start recording audio."""
        ...
    
    def stop_recording(self) -> bytes:
        """Stop recording and return the recorded audio data."""
        ...

class AudioAnalyzer(Protocol):
    def is_speech(self, audio_data: bytes, config: AudioConfig) -> bool:
        """Analyze audio data to determine if it contains speech."""
        ...

class WordDetector(Protocol):
    def detect(self, audio_data: bytes) -> bool:
        """Detect if the wake word is present in the audio data."""
        ...

class ConversationManager(Protocol):
    def add_user_message(self, message: str) -> None:
        """Add a user message to the conversation history."""
        ...
    
    def add_assistant_message(self, message: str) -> None:
        """Add an assistant message to the conversation history."""
        ...
    
    def get_conversation_history(self) -> List[dict]:
        """Get the full conversation history."""
        ...
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        ...

class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> bytes:
        """Convert text to speech audio data."""
        ...

class AudioPlayer(Protocol):
    def play(self, audio_data: bytes) -> None:
        """Play audio data."""
        ... 