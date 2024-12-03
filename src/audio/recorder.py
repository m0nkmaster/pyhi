from typing import Optional, Callable
import time
import pyaudio
from ..utils.types import AudioConfig, AudioFrame, AudioAnalyzer

class PyAudioRecorder:
    def __init__(
        self,
        config: AudioConfig,
        analyzer: AudioAnalyzer,
        on_error: Optional[Callable[[Exception], None]] = None,
        wake_word_silence_threshold: float = 1.0,
        response_silence_threshold: float = 2.0,
        buffer_duration: float = 1.0  # Duration of audio buffer in seconds
    ):
        """
        Initialize the PyAudio recorder.
        
        Args:
            config: Audio configuration parameters
            analyzer: Audio analyzer for speech detection
            on_error: Optional callback for error handling
            wake_word_silence_threshold: Seconds of silence before ending wake word detection
            response_silence_threshold: Seconds of silence before ending response recording
            buffer_duration: Duration of audio buffer in seconds
        """
        self.config = config
        self.analyzer = analyzer
        self.on_error = on_error or (lambda e: None)
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.frames: list[bytes] = []
        
        # Speech detection state
        self.speech_detection_buffer: list[bool] = []
        self.silence_counter = 0
        self.session_silence_counter = 0
        self.is_recording = False
        
        # Silence thresholds
        self.wake_word_silence_threshold = wake_word_silence_threshold
        self.response_silence_threshold = response_silence_threshold
        
        # Calculate buffer size in chunks
        chunks_per_second = self.config.sample_rate / self.config.chunk_size
        self.buffer_size = int(chunks_per_second * buffer_duration)
        self.audio_buffer: list[bytes] = []
    
    def start_recording(self) -> None:
        """Start recording audio."""
        if self.stream is not None:
            return
        
        try:
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            self.frames = []
            self.speech_detection_buffer = []
            self.silence_counter = 0
            self.session_silence_counter = 0
            self.is_recording = False
        except Exception as e:
            self.on_error(e)
            raise
    
    def stop_recording(self, is_wake_word_mode: bool = False) -> bytes:
        """
        Stop recording and return the recorded audio data.
        
        Args:
            is_wake_word_mode: Whether we're recording for wake word detection
        
        Returns:
            bytes: The recorded audio data
        """
        if self.stream is None:
            return b''
        
        try:
            frames = []
            silence_counter = 0
            session_silence_counter = 0
            speech_detection_buffer = []
            is_recording = False
            
            silence_threshold = (self.wake_word_silence_threshold if is_wake_word_mode 
                               else self.response_silence_threshold)
            
            print("\nRecording..." if not is_wake_word_mode else "Listening for wake word...")
            
            while True:
                try:
                    data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                except IOError:
                    continue
                
                # Maintain rolling buffer for wake word detection
                if is_wake_word_mode:
                    self.audio_buffer.append(data)
                    if len(self.audio_buffer) > self.buffer_size:
                        self.audio_buffer.pop(0)
                
                # Detect speech
                is_speech = self.analyzer.is_speech(data, self.config)
                speech_detection_buffer.append(is_speech)
                if len(speech_detection_buffer) > 3:
                    speech_detection_buffer.pop(0)
                
                # Update recording state based on speech detection
                if any(speech_detection_buffer):
                    if not is_recording:
                        is_recording = True
                        if is_wake_word_mode:
                            # Include buffer content when speech starts
                            frames.extend(self.audio_buffer)
                        silence_counter = 0
                
                if is_recording:
                    frames.append(data)
                
                # Handle silence detection
                if not any(speech_detection_buffer[-2:]):  # Use last 2 chunks for silence detection
                    silence_counter += self.config.chunk_size / self.config.sample_rate
                    if silence_counter >= silence_threshold:
                        break
                else:
                    silence_counter = 0
            
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
            return b''.join(frames)
            
        except Exception as e:
            self.on_error(e)
            raise
        finally:
            self.frames = []
            self.speech_detection_buffer = []
            self.silence_counter = 0
            self.session_silence_counter = 0
            self.is_recording = False
    
    def read_frame(self) -> AudioFrame:
        """
        Read a single frame of audio data.
        
        Returns:
            AudioFrame: The audio frame with speech detection result
        """
        if self.stream is None:
            raise RuntimeError("Recording not started")
        
        try:
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            is_speech = self.analyzer.is_speech(data, self.config)
            return AudioFrame(data=data, is_speech=is_speech)
        except Exception as e:
            self.on_error(e)
            raise
    
    def __del__(self):
        """Cleanup resources."""
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if self.audio is not None:
            try:
                self.audio.terminate()
            except:
                pass 