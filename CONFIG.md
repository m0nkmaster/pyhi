# PyHi Configuration Guide

This document provides a detailed breakdown of all configuration options available in PyHi. All configurations are defined in `src/config.py`.

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
    timeout_seconds: float = 30.0      # Conversation timeout
    wake_words: list[str] | None       # Customizable wake word list
    temp_recording_path: str = "recording.wav"
    temp_response_path: str = "response.mp3"
```

#### Default Wake Words
Includes variations like:
- "hey chat", "hi chat", "hello chat"
- "hey chatbot", "hi chatbot"
- "chat", "chats"...

### AudioRecorderConfig
Controls when to stop recording based on detected silence.

```python
@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 0.5   # Seconds of silence before stopping wake word detection
    response_silence_threshold: float = 0.5     # Seconds of silence before stopping response recording
    buffer_duration: float = 0                  # Duration of audio buffer in seconds
```

The code detects silence by analyzing the audio characteristics (amplitude and frequency) and when continuous silence is detected for the specified duration, it stops recording. Different thresholds are used for wake word detection and response recording.

#### Threshold Values
- Higher values (closer to 1.0) require more silence
- Lower values (closer to 0.0) are more sensitive

### AudioConfig
Core audio processing settings.

```python
@dataclass
class AudioConfig:
    sample_rate: int = 16000          # Audio sampling rate
    channels: int = 1                 # Mono audio
    chunk_size: int = 256            # Processing chunk size
    format: int = pyaudio.paInt16    # 16-bit audio
    input_device_index: int = 1      # Audio input device
    use_plughw: bool = False         # Linux audio config
```

#### Important Notes
- `sample_rate`: 16kHz is optimal for Whisper
- `chunk_size`: Lower values = faster processing but more CPU
- `input_device_index`: May need adjustment based on system

### AudioPlayerConfig
Audio output configuration.

```python
@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"           # Temporary audio file
    activation_sound_path: str = "src/assets/bing.mp3"  # Wake word confirmation sound
    output_device: str = ""                        # Audio output device
```

### ChatConfig
ChatGPT API configuration.

```python
@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"        # GPT model selection
    max_tokens: int = 75              # Maximum response length
    temperature: float = 0.7          # Response randomness
    system_prompt: str = "You are a helpful assistant. Respond briefly."
```

#### Model Options
- `gpt-4-turbo`: Latest GPT-4 model (recommended)
- Can be changed to other available OpenAI models

#### Temperature
- 0.0: Most deterministic
- 1.0: Most creative
- 0.7: Balanced responses

### TTSConfig
Text-to-Speech configuration.

```python
@dataclass
class TTSConfig:
    model: str = "tts-1"              # OpenAI TTS model
    voice: str = "nova"               # Voice selection
```

#### Available Voices
- "alloy": Neutral and balanced
- "echo": Mature and deep
- "fable": British accent
- "onyx": Deep and authoritative
- "nova": Warm and natural
- "shimmer": Clear and expressive

### WakeWordConfig
Wake word detection settings using Whisper.

```python
@dataclass
class WakeWordConfig:
    model: str = "whisper-1"          # Whisper model
    temperature: float = 0.0          # Transcription determinism
    language: str = "en"              # Language setting
    min_audio_size: int = 1024        # Minimum audio for processing
```

## Optimization Tips

### For Faster Response
- Reduce `chunk_size` in AudioConfig
- Lower `max_tokens` in ChatConfig
- Adjust silence thresholds in AudioRecorderConfig

### For Better Accuracy
- Increase `chunk_size` for better audio quality
- Adjust wake word silence threshold
- Use a more powerful GPT model

### For Lower Resource Usage
- Increase `chunk_size` to reduce processing frequency
- Lower `max_tokens` in ChatConfig
- Use faster GPT models

## Troubleshooting

### Audio Issues
1. Check `input_device_index` in AudioConfig
2. Verify audio format compatibility
3. Try adjusting silence thresholds

### Performance Issues
1. Adjust chunk_size based on CPU capacity
2. Reduce max_tokens for faster responses
3. Consider using faster models

### Wake Word Detection
1. Add more wake word variations
2. Adjust silence threshold
3. Check audio input configuration