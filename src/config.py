from dataclasses import dataclass, field
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
    wake_word_silence_threshold: float = 1.5
    response_silence_threshold: float = 2.0
    buffer_duration: float = 0.1


@dataclass
class AudioDeviceConfig:
    # Device selection
    auto_select_device: bool = True
    preferred_input_device_name: str | None = None  # Set to None by default
    preferred_output_device_name: str | None = None  # Set to None by default
    excluded_device_names: list[str] = field(default_factory=lambda: ["BlackHole", "ZoomAudioDevice"])
    fallback_to_default: bool = True
        
    # Buffer settings
    buffer_size_ms: int = 50  # Used to calculate chunk_size based on sample rate
    
    # Error handling
    retry_on_error: bool = True
    max_retries: int = 3
    
    # Debug options
    list_devices_on_start: bool = True
    debug_audio: bool = True  # Enable debug mode temporarily


@dataclass
class SpeechDetectionConfig:
    # Base threshold for speech detection
    base_threshold: int = 500
    
    # Multipliers for different checks
    loudness_multiplier: float = 1.0
    background_noise_multiplier: float = 1.5
    signal_to_noise_threshold: float = 2.0
    magnitude_multiplier: float = 2.0
    variation_multiplier: float = 1.0
    rms_multiplier: float = 1.2
    
    # Frequency range for speech
    min_speech_freq: int = 85
    max_speech_freq: int = 3000
    
    # Variation threshold divisor
    variation_divisor: float = 3.0


@dataclass
class AudioConfig:
    sample_rate: int = 48000
    channels: int = 1
    chunk_size: int = 512
    format: int = pyaudio.paInt16
    input_device_index: int | None = None
    output_device_index: int | None = None
    device_config: AudioDeviceConfig = field(default_factory=AudioDeviceConfig)
    speech_config: SpeechDetectionConfig = field(default_factory=SpeechDetectionConfig)

    def __post_init__(self):
        if self.chunk_size == 512:
            self.chunk_size = int(self.sample_rate * (self.device_config.buffer_size_ms / 1000))


@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"
    activation_sound_path: str = "src/assets/bing.mp3"
    volume_level: float = 1.0  # 0.0 to 1.0
    output_device_index: int | None = None


@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"
    max_completion_tokens: int = 250
    temperature: float = 0.7
    system_prompt: str = "You are a voice assistant in a lively household where people may occasionally ask you questions. Expect a mix of queries, including cooking tips, general knowledge, and advice. Respond quickly, clearly, and helpfully, keeping your answers concise and easy to understand."  # Added system prompt for brevity


@dataclass
class TTSConfig:
    model: str = "tts-1"
    voice: str = "nova" # "alloy", "echo", "fable", "onyx", "nova", "shimmer"


@dataclass
class WordDetectionConfig:
    model: str = "whisper-1"
    temperature: float = 0.0
    language: str = "en"
    min_audio_size: int = 4096
    similarity_threshold: float = 0.75


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