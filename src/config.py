from dataclasses import dataclass, field
import pyaudio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify API key is present
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")


# Audio file paths relative to src/assets
ACTIVATION_SOUND = "bing.mp3"
CONFIRMATION_SOUND = "elevator.mp3"  
READY_SOUND = "beep.mp3"
SLEEP_SOUND = "bing-bong.mp3"  # Reusing activation sound for now

# Base directory for audio assets
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

def get_sound_path(filename: str) -> str:
    """Get the absolute path for a sound file in the assets directory."""
    return os.path.join(ASSETS_DIR, filename)


@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 0.5
    response_silence_threshold: float = 1.0  # Increased from default
    buffer_duration: float = 1.0


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
    debug_audio: bool = False  # Set to False by default for production


@dataclass
class SpeechDetectionConfig:
    # Base threshold for speech detection
    base_threshold: int = 1000
    
    # Multipliers for different checks
    loudness_multiplier: float = 1.2
    background_noise_multiplier: float = 2.0
    signal_to_noise_threshold: float = 3.0
    magnitude_multiplier: float = 2.5
    variation_multiplier: float = 1.2
    rms_multiplier: float = 1.5
    
    # Frequency range for speech
    min_speech_freq: int = 85
    max_speech_freq: int = 3000
    
    # Variation threshold divisor
    variation_divisor: float = 2.0


@dataclass
class AudioConfig:
    sample_rate: int = 16000  # Required by Porcupine
    channels: int = 1
    chunk_size: int = 1024     # Match Porcupine's frame length
    format: int = pyaudio.paInt16  # 16-bit linear PCM
    input_device_index: int | None = None
    output_device_index: int | None = None
    device_config: AudioDeviceConfig = field(default_factory=AudioDeviceConfig)
    speech_config: SpeechDetectionConfig = field(default_factory=SpeechDetectionConfig)
    
    def __post_init__(self):
        # Ensure chunk size matches Porcupine's frame length
        if self.chunk_size != 1024:
            print("Warning: chunk_size should be 1024 for Porcupine wake word detection")


@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"
    activation_sound_path: str = "src/assets/bing.mp3"
    volume_level: float = 1.0  # 0.0 to 1.0
    output_device_index: int | None = None


@dataclass
class ChatConfig:
    model: str = "gpt-3.5-turbo"
    max_completion_tokens: int = 250
    temperature: float = 0.7
    system_prompt: str = "You are a voice assistant in a lively household. Keep your responses concise, clear, and under 2 sentences when possible. Be direct and helpful."


@dataclass
class TTSConfig:
    model: str = "tts-1"
    voice: str = "nova" # "alloy", "echo", "fable", "onyx", "nova", "shimmer"


@dataclass
class WordDetectionConfig:
    # Debug options
    debug_detection: bool = False
    # Frame length in milliseconds
    frame_length_ms: int = 512


@dataclass
class AppConfig:
    timeout_seconds: float = 10.0
    words: list[str] | None = None
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"

    def __post_init__(self):
        if self.words is None:
            # Use the Hey Chat wake word model for Mac
            model_path = os.path.join(os.path.dirname(__file__), "assets", "Hey-Chat_en_mac_v3_0_0.ppn")
            self.words = [model_path]