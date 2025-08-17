from dataclasses import dataclass, field
import pyaudio
import os
from dotenv import load_dotenv
import platform
from typing import Optional, List, Dict, Any

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
    response_silence_threshold: float = 2.0
    buffer_duration: float = 1.0


@dataclass
class AudioDeviceConfig:
    # Device selection
    auto_select_device: bool = True
    preferred_input_device_name: str | None = "Jabra Speak2"  # More specific match
    preferred_output_device_name: str | None = "Jabra Speak2"
    excluded_device_names: list[str] = field(default_factory=lambda: ["BlackHole", "ZoomAudioDevice"])
    fallback_to_default: bool = True
        
    # Buffer settings
    buffer_size_ms: int = 75  # Slightly increased for smoother transitions
    
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
    channels: int = 1         # Required for wake word detection
    chunk_size: int = 1024    # Match Porcupine's frame length
    format: int = pyaudio.paInt16
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
    volume_level: float = 0.9  # Slightly reduced to prevent clipping
    output_device_index: int | None = None
    output_device_name: Optional[str] = "Built-in Output"  # Default to Mac's built-in output

@dataclass
class ChatConfig:
    system_prompt: str = """You are a voice assistant in a lively household. Keep your responses concise, clear, and under 2 sentences when possible. Be direct and helpful.

Current Context:
- Current Date: {current_date}
- Current Time: {current_time}
- Location: {location}
- Timezone: {timezone}

Use this context to provide more relevant and timely responses. For example, consider the time of day when making suggestions or the current season for relevant recommendations."""

@dataclass
class WordDetectionConfig:
    model_path = os.path.join(
        os.path.dirname(__file__), 
        "assets",
        "Hey-Chat_en_mac_v3_0_0.ppn" if platform.system().lower() == 'darwin' else "Hey-Chat_en_raspberry-pi_v3_0_0.ppn"
    )

@dataclass
class AIConfig:
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))# Options: 'openai', 'claude'
    voice: str = "nova"
    voice_model: str = "tts-1"
    #chat_provider: str = "claude"  
    #chat_model: str = "claude-3-opus-20240229"
    chat_provider: str = "openai"  
    chat_model: str = "gpt-4o-mini"
    max_completion_tokens: int = 250
    temperature: float = 0.7

@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    executable: str  # Path to server executable
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

@dataclass
class MCPConfig:
    """Configuration for MCP (Model Context Protocol) integration."""
    enabled: bool = False  # Temporarily disabled for testing
    transport: str = "stdio"  # "stdio" or "http"
    timeout: int = 30
    auto_start: bool = True
    servers: List[MCPServerConfig] = field(default_factory=lambda: [
        MCPServerConfig(
            name="weather",
            executable="python",
            args=["-m", "src.mcp_servers.weather"],
            env={}
        ),
        MCPServerConfig(
            name="calendar",
            executable="python", 
            args=["-m", "src.mcp_servers.calendar"],
            env={}
        ),
        MCPServerConfig(
            name="alarms",
            executable="python",
            args=["-m", "src.mcp_servers.alarms"],
            env={}
        ),
        MCPServerConfig(
            name="train_times",
            executable="python",
            args=["-m", "src.mcp_servers.train_times"],
            env={}
        ),
    ])

@dataclass
class AppConfig:
    timeout_seconds: float = 10.0
    words: list[str] | None = None
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"
    ai_config: AIConfig = field(default_factory=AIConfig)
    mcp_config: MCPConfig = field(default_factory=MCPConfig)