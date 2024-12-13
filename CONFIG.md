# PyHi Configuration Guide

This document provides a detailed breakdown of all configuration options available in PyHi and their defaults. All configurations are defined in `src/config.py`.

## Environment Variables

### Required Variables
- `OPENAI_API_KEY`: Your OpenAI API key
  - Required for ChatGPT and TTS functionality
  - Must be set in `.env` file or environment
- `PICOVOICE_API_KEY`: Your Picovoice API key
  - Required for wake word detection using Porcupine
  - Must be set in `.env` file or environment
- `ANTHROPIC_API_KEY`: Your Anthropic API key
  - Required for Claude chat functionality
  - Must be set in `.env` file or environment

## Wake Words

PyHi uses Porcupine for wake word detection. To set up your wake words:

1. Go to [Picovoice Console](https://console.picovoice.ai/ppn)
2. Create your custom wake word or select a pre-built one
3. Download the appropriate .ppn file for your platform (e.g., computer_mac.ppn)
4. Place it in `src/assets/`
5. Update `AppConfig.words` with the path to your .ppn file

Example configuration:
```python
# In config.py
self.words = [
    os.path.join(os.path.dirname(__file__), "assets", "computer_mac.ppn"),
    os.path.join(os.path.dirname(__file__), "assets", "hey_chat_mac.ppn")
]
```

You can use multiple wake words by adding multiple .ppn files to the list.

## Sound Files
Located in `src/assets/`:
- `bing.mp3`: Played when wake word is detected
- `yes.mp3`: Played when speech is successfully recognized
- `beep.mp3`: Played when ready for next question
- `bing-bong.mp3`: Played when going back to sleep mode

## AI Configuration

### AI Providers
- **OpenAI**: Used for chat completions and text-to-speech.
- **Claude (Anthropic)**: Used for chat completions.

### Configuration Options
- `chat_provider`: Determines which AI provider to use for chat completions. Options are 'openai' or 'claude'.
- `chat_model`: Specifies the model to use for chat completions. Default is 'gpt-3.5-turbo' for OpenAI and 'claude-3-opus-20240229' for Claude.

Example configuration:
```python
# In config.py
chat_provider: str = "openai"  # Options: 'openai', 'claude'
chat_model: str = "gpt-3.5-turbo"
```

## Configuration Classes

### AppConfig
Primary application settings controlling core behavior.

```python
@dataclass
class AppConfig:
    timeout_seconds: float = 10.0      # Conversation timeout
    words: list[str] | None = None     # Wake words for Porcupine
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"
    chat_provider: str = "openai"      # Options: 'openai', 'claude'
    chat_model: str = "gpt-3.5-turbo"
```

### AudioRecorderConfig
Controls when to stop recording based on detected silence.

```python
@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 0.5    # Seconds of silence for wake word detection
    response_silence_threshold: float = 2.5     # Seconds of silence before stopping response recording
    buffer_duration: float = 1.0               # Duration of audio buffer in seconds
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

### AudioConfig
Core audio processing settings.

```python
@dataclass
class AudioConfig:
    sample_rate: int = 16000          # Required by Porcupine
    channels: int = 1                 # Mono audio
    chunk_size: int = 1024           # Match Porcupine's frame length
    format: int = pyaudio.paInt16    # 16-bit audio
    input_device_index: int | None = None
    output_device_index: int | None = None
    device_config: AudioDeviceConfig = field(default_factory=AudioDeviceConfig)
    speech_config: SpeechDetectionConfig = field(default_factory=SpeechDetectionConfig)
```

### WordDetectionConfig
Controls wake word detection settings.

```python
@dataclass
class WordDetectionConfig:
    debug_detection: bool = False      # Enable debug logging for wake word detection
    frame_length_ms: int = 512        # Frame length for Porcupine processing
```

### ChatConfig
Controls ChatGPT interaction settings.

```python
@dataclass
class ChatConfig:
    model: str = "gpt-3.5-turbo"      # OpenAI model for chat
    max_completion_tokens: int = 250   # Maximum response length
    temperature: float = 0.7          # Response randomness
    system_prompt: str = "You are a voice assistant..."  # System context
```

### TTSConfig
Controls text-to-speech settings.

```python
@dataclass
class TTSConfig:
    model: str = "tts-1"              # OpenAI TTS model
    voice: str = "nova"               # Voice selection
```