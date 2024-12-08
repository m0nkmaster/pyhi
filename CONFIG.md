# PyHi Configuration Guide

This document provides a detailed breakdown of all configuration options available in PyHi and their defaults. All configurations are defined in `src/config.py`.

## Environment Variables

### Required Variables
- `OPENAI_API_KEY`: Your OpenAI API key
  - Required for ChatGPT, Whisper, and TTS functionality
  - Must be set in `.env` file or environment

## Configuration Classes

### AppConfig
Primary application settings controlling core behavior.

```python
@dataclass
class AppConfig:
    timeout_seconds: float = 10.0      # Conversation timeout
    words: list[str] | None = None     # Customizable wake word list
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"
```

### AudioRecorderConfig
Controls when to stop recording based on detected silence.

```python
@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 1.2   # Seconds of silence before stopping wake word detection
    response_silence_threshold: float = 1.0     # Seconds of silence before stopping response recording
    buffer_duration: float = 1.5               # Duration of audio buffer in seconds
```

### AudioDeviceConfig
Controls audio device selection and behavior.

```python
@dataclass
class AudioDeviceConfig:
    # Device selection
    auto_select_device: bool = True
    preferred_input_device_name: str | None = None
    preferred_output_device_name: str | None = None
    excluded_device_names: list[str] = ["BlackHole", "ZoomAudioDevice"]
    fallback_to_default: bool = True
    
    # Buffer settings
    buffer_size_ms: int = 50  # Used to calculate chunk_size based on sample rate
    
    # Error handling
    retry_on_error: bool = True
    max_retries: int = 3
    
    # Debug options
    list_devices_on_start: bool = True
    debug_audio: bool = False
```

### SpeechDetectionConfig
Controls speech detection sensitivity and thresholds.

```python
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
```

### AudioConfig
Core audio processing settings.

```python
@dataclass
class AudioConfig:
    sample_rate: int = 48000          # Audio sampling rate
    channels: int = 1                 # Mono audio
    chunk_size: int = 512            # Processing chunk size (adjusted based on buffer_size_ms)
    format: int = pyaudio.paInt16    # 16-bit audio
    input_device_index: int | None = None  # Audio input device
    output_device_index: int | None = None # Audio output device
    device_config: AudioDeviceConfig = field(default_factory=AudioDeviceConfig)
    speech_config: SpeechDetectionConfig = field(default_factory=SpeechDetectionConfig)
```

### AudioPlayerConfig
Audio output configuration.

```python
@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"           # Temporary audio file
    activation_sound_path: str = "src/assets/bing.mp3"  # Wake word sound
    volume_level: float = 1.0                      # Volume level (0.0 to 1.0)
    output_device_index: int | None = None         # Audio output device index
```

### ChatConfig
Configuration for the GPT-4-Turbo language model.

```python
@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"        # Latest GPT-4 model for improved responses
    max_completion_tokens: int = 250   # Maximum response length in tokens
    temperature: float = 0.7          # Response creativity (0.0-1.0)
    system_prompt: str = "You are a voice assistant in a lively household where people may occasionally ask you questions. Expect a mix of queries, including cooking tips, general knowledge, and advice. Respond quickly, clearly, and helpfully, keeping your answers concise and easy to understand."
```

### TTSConfig
Text-to-speech configuration using OpenAI's TTS API.

```python
@dataclass
class TTSConfig:
    model: str = "tts-1"              # OpenAI TTS model
    voice: str = "nova"               # Voice option (alloy, echo, fable, onyx, nova, shimmer)
```

### WordDetectionConfig
Configuration for wake word detection using Whisper.

```python
@dataclass
class WordDetectionConfig:
    model: str = "whisper-1"          # OpenAI Whisper model
    temperature: float = 0.0          # Transcription randomness (0.0 for consistency)
    language: str = "en"              # Expected language
    min_audio_size: int = 4096        # Minimum audio size for processing
    similarity_threshold: float = 0.75 # Threshold for wake word matching
```

[See OpenAI Chat API Documentation](https://platform.openai.com/docs/api-reference/chat)