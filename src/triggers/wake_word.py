"""Wake word detection trigger implementation."""
import threading
from dataclasses import dataclass, field
from typing import Optional, List
from openai import OpenAI

from .base import WakeTrigger, TriggerConfig
from ..word_detection.detector import WhisperWordDetector
from ..audio.recorder import PyAudioRecorder
from ..audio.analyzer import is_speech as analyze_speech
from ..config import AudioConfig, WordDetectionConfig, AudioRecorderConfig

@dataclass
class WakeWordTriggerConfig:
    """Configuration for wake word trigger."""
    words: List[str]  # List of wake words/phrases to detect
    _enabled: bool = field(default=True)  # Internal field
    audio_config: Optional[AudioConfig] = field(default=None)
    word_detection_config: Optional[WordDetectionConfig] = field(default=None)
    recorder_config: Optional[AudioRecorderConfig] = field(default=None)
    
    @property
    def enabled(self) -> bool:
        """Get enabled state."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set enabled state."""
        self._enabled = value

class WakeWordTrigger(WakeTrigger):
    """Wake word detection trigger."""
    
    def __init__(self, openai_client: OpenAI, config: Optional[WakeWordTriggerConfig] = None):
        """Initialize the wake word trigger."""
        super().__init__(config or WakeWordTriggerConfig(words=[]))
        self.config: WakeWordTriggerConfig = self.config  # type: ignore
        
        # Initialize components
        self.word_detector = WhisperWordDetector(
            client=openai_client,
            words=self.config.words,
            config=self.config.word_detection_config,
            audio_config=self.config.audio_config
        )
        
        self.audio_recorder = PyAudioRecorder(
            config=self.config.audio_config or AudioConfig(),
            analyzer=self,  # type: ignore
            recorder_config=self.config.recorder_config
        )
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def is_speech(self, audio_data: bytes, config: AudioConfig) -> bool:
        """Implement AudioAnalyzer protocol."""
        try:
            return analyze_speech(audio_data, config)
        except Exception as e:
            print(f"\rSpeech detection error: {e}", end="", flush=True)
            return False
    
    def _run_detection_loop(self) -> None:
        """Run the wake word detection loop."""
        while not self._stop_event.is_set():
            try:
                print("\rListening for wake word...", end="", flush=True)
                
                # Record audio
                self.audio_recorder.start_recording()
                audio_data = self.audio_recorder.stop_recording(is_wake_word_mode=True)
                
                if not audio_data:
                    continue
                
                # Check for wake word
                if self.word_detector.detect(audio_data):
                    print("\nWake word detected!")
                    self.notify_wake()
            
            except Exception as e:
                print(f"\nError in wake word detection: {e}")
                continue
    
    def _start_impl(self) -> None:
        """Start listening for wake words."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_detection_loop)
            self._thread.daemon = True
            self._thread.start()
    
    def _stop_impl(self) -> None:
        """Stop listening for wake words."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def start(self) -> None:
        """Start listening for wake words."""
        if not self.config.enabled:
            return
        self._start_impl()
    
    def stop(self) -> None:
        """Stop listening for wake words."""
        self._stop_impl()
    
    @property
    def is_active(self) -> bool:
        """Return whether wake word detection is currently active."""
        return bool(self._thread and self._thread.is_alive())
