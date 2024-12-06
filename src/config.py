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
    wake_word_silence_threshold: float = 0.7
    response_silence_threshold: float = 0.7
    buffer_duration: float = 0.5  # Added 0.5 second buffer for minimum audio length


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 512  # Restored to original value for better detection accuracy
    format: int = pyaudio.paInt16
    input_device_index: int | None = None
    use_plughw: bool = False

    def __post_init__(self):
        self.sample_rate = self.sample_rate
        self.channels = self.channels


@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"
    activation_sound_path: str = "src/assets/bing.mp3"
    output_device: str = ""


@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"  # Using faster model
    max_completion_tokens: int = 75  # Further reduced for even quicker responses
    temperature: float = 0.7
    system_prompt: str = "You are a voice assistant in a lively household where people may occasionally ask you questions. Expect a mix of queries, including cooking tips, general knowledge, and advice. Respond quickly, clearly, and helpfully, keeping your answers concise and easy to understand."  # Added system prompt for brevity


@dataclass
class TTSConfig:
    model: str = "tts-1"
    voice: str = "nova" # "alloy", "echo", "fable", "onyx", "nova", "shimmer"

@dataclass
class WordDetectionConfig:
    model: str = "whisper-1"
    temperature: float = 0.2  # Increased slightly for better word variation handling
    language: str = "en"
    min_audio_size: int = 2048  # Restored to original value for better accuracy


@dataclass
class APIConfig:
    port: int = 1010
    host: str = "0.0.0.0"


@dataclass
class AppConfig:
    timeout_seconds: float = 10.0
    words: list[str] | None = None
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"

    def __post_init__(self):
        if self.words is None:
            self.words = [
                "hey chat", "hi chat", "hello chat",
                "hey chatbot", "hi chatbot", "hello chatbot",
                "chat", "chats", "hey chap", "hey chaps",
                "hey Chad", "hi Chad", "hello Chad",
                "hey Jack", "hey check", "hey chap",
                "hey shot", "hay chat", "hey chair",
                "hey that", "he chat", "hey chatty",
                "hey chat bot", "hey chat!"
            ]