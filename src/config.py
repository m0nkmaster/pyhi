from dataclasses import dataclass
import pyaudio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify API key is present
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")


@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 0.7  # More sensitive silence detection
    response_silence_threshold: float = 1.0    # Shorter silence threshold
    buffer_duration: float = 0              # Shorter buffer for quicker response


@dataclass
class AudioConfig:
    sample_rate: int = 16000  # Lower sample rate for better speech recognition
    channels: int = 1
    chunk_size: int = 512     # Smaller chunks for more frequent processing
    format: int = pyaudio.paInt16
    input_device_index: int = 2
    use_plughw: bool = False

    def __post_init__(self):
        # Make these mutable so they can be updated based on device capabilities
        self.sample_rate = self.sample_rate
        self.channels = self.channels


@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"
    activation_sound_path: str = "src/assets/bing.mp3"
    output_device: str = ""


@dataclass
class ChatConfig:
    model: str = "gpt-3.5-turbo"
    max_tokens: int = 150
    temperature: float = 0.7


@dataclass
class TTSConfig:
    model: str = "tts-1"
    voice: str = "nova"


@dataclass
class WakeWordConfig:
    model: str = "whisper-1"
    temperature: float = 0.0
    language: str = "en"
    min_audio_size: int = 2048


@dataclass
class AppConfig:
    timeout_seconds: float = 30.0
    wake_words: list[str] | None = None
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"

    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = [
                "hey chat", "hi chat", "hello chat",
                "hey chatbot", "hi chatbot", "hello chatbot",
                "chat", "chats", "hey chap", "hey chaps",
                "hey Chad", "hi Chad", "hello Chad",
                "hey Jack", "hey check", "hey chap",
                "hey shot", "hay chat", "hey chair",
                "hey that", "he chat", "hey chatty",
                "hey chat bot", "hey chat!"
            ]