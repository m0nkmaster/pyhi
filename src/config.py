from dataclasses import dataclass

@dataclass
class AudioRecorderConfig:
    wake_word_silence_threshold: float = 1.0  # Seconds of silence before ending wake word detection
    response_silence_threshold: float = 2.0    # Seconds of silence before ending response recording
    buffer_duration: float = 1.0               # Duration of audio buffer in seconds

@dataclass
class AudioConfig:
    sample_rate: int = 44100
    channels: int = 1
    chunk_size: int = 1024
    format: int = 16  # 16-bit audio

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
class AppConfig:
    timeout_seconds: float = 30.0
    wake_words: list[str] = None

    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = [
                "hey chat", "hi chat", "hello chat",
                "hey chatbot", "hi chatbot", "hello chatbot"
            ] 