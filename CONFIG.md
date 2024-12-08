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
    wake_word_silence_threshold: float = 0.0   # Seconds of silence before stopping wake word detection
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
    input_device_index: int | None = 1  # Audio input device
```

#### Important Notes
- `sample_rate`: 16kHz is standard for speech recognition and Whisper
- `chunk_size`: Set to 256 for balance between latency and CPU usage
- `input_device_index`: Device 2 is MacBook Pro Microphone (may vary by system)
  - Set to None for simple auto-detection of first available input device
  - Set to specific index (0,2,4 etc) for consistent device selection

### AudioPlayerConfig
Audio output configuration.

```python
@dataclass
class AudioPlayerConfig:
    temp_file: str = "temp_playback.mp3"           # Temporary audio file
    activation_sound_path: str = "src/assets/bing.mp3"  # Wake word sound
    output_device: str = ""                        # Linux only: ALSA output device
```

#### Important Notes
- `temp_file`: Temporary file for audio playback (automatically cleaned up)
- `activation_sound_path`: Sound played when wake word is detected
- `output_device`: Only used on Linux with mpg123. On macOS/Windows, system default is used

### ChatConfig
Configuration for the GPT-4-Turbo language model.

```python
@dataclass
class ChatConfig:
    model: str = "gpt-4-turbo"        # Latest GPT-4 model for improved responses
    max_completion_tokens: int = 75    # Maximum response length in tokens
    temperature: float = 0.7          # Response creativity (0.0-1.0)
    system_prompt: str = "You are a helpful assistant. Respond briefly."
```

#### Important Notes
- `model`: Uses GPT-4-Turbo for optimal performance and cost efficiency
- `max_completion_tokens`: Keeps responses concise and natural for voice output
- `temperature`: 0.7 provides a good balance between consistency and creativity
- `system_prompt`: Configures the AI's personality and response style

[See OpenAI Chat API Documentation](https://platform.openai.com/docs/api-reference/chat/create)

### TTSConfig
Text-to-Speech configuration.

```python
@dataclass
class TTSConfig:
    model: str = "tts-1"              # OpenAI TTS model
    voice: str = "fable"               # Voice selection
```

#### Available Voices (Dec 2024)
[See OpenAI TTS Voice Options](https://platform.openai.com/docs/api-reference/audio/createSpeech)

### WordDetectionConfig
Word detection settings using Whisper.

```python
@dataclass
class WordDetectionConfig:
    model: str = "whisper-1"          # Whisper model for speech recognition
    temperature: float = 0.0          # Transcription determinism
    language: str = "en"              # Language setting
    min_audio_size: int = 1024        # Minimum audio for processing
```

#### Important Notes
- Used for both wake word detection AND conversation transcription
- `model`: Whisper-1 is OpenAI's speech recognition model
  - Used for both wake word detection and conversation transcription
  - Provides high accuracy for English speech
- `temperature`: Set to 0.0 for most consistent transcriptions
  - Higher values (0.0-1.0) allow more transcription variations
  - Keep at 0.0 for wake word detection reliability
- `language`: Forces Whisper to expect specified language
  - "en" optimizes for English recognition
  - Can be changed for other languages
- `min_audio_size`: Minimum bytes of audio before processing
  - Prevents processing of too-short audio snippets
  - Lower values = faster response but may catch partial words
- [See Whisper Documentation](https://platform.openai.com/docs/api-reference/audio/createTranscription)

## Optimization Tips

### For Faster Response
- Reduce `chunk_size` in AudioConfig
- Lower `max_completion_tokens` in ChatConfig
- Adjust silence thresholds in AudioRecorderConfig

### For Better Accuracy
- Increase `chunk_size` for better audio quality
- Adjust wake word silence threshold
- Use a more powerful GPT model

### For Lower Resource Usage
- Increase `chunk_size` to reduce processing frequency
- Lower `max_completion_tokens` in ChatConfig
- Use faster GPT models

## Troubleshooting

### Audio Issues
1. Check `input_device_index` in AudioConfig
2. Verify audio format compatibility
3. Try adjusting silence thresholds

### Performance Issues
1. Adjust chunk_size based on CPU capacity
2. Reduce max_completion_tokens for faster responses
3. Consider using faster models

### Wake Word Detection
1. Add more wake word variations
2. Adjust silence threshold
3. Check audio input configuration