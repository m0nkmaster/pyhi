from typing import Optional, Callable
import time
import pyaudio
from ..utils.types import AudioConfig, AudioFrame, AudioAnalyzer
from ..config import AudioRecorderConfig

class PyAudioRecorder:
    def __init__(
        self,
        config: AudioConfig,
        analyzer: AudioAnalyzer,
        on_error: Optional[Callable[[Exception], None]] = None,
        recorder_config: Optional[AudioRecorderConfig] = None
    ):
        """
        Initialize the PyAudio recorder.
        """
        # Initialize basic attributes first to avoid __del__ errors
        self.stream = None
        self.frames = []
        self.audio_buffer = []
        
        # Then initialize the rest
        self.config = config
        self.analyzer = analyzer
        self.on_error = on_error or (lambda e: None)
        self.recorder_config = recorder_config or AudioRecorderConfig()
        
        try:
            self.audio = pyaudio.PyAudio()
            
            # List all available devices
            print("\nAvailable audio devices:")
            input_devices = []
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:  # Only show input devices
                    input_devices.append(i)
                    print(f"Device {i}: {dev_info['name']}")
                    print(f"    Input channels: {dev_info['maxInputChannels']}")
                    print(f"    Sample rate: {dev_info['defaultSampleRate']}")
            print()
            
            # If no device index specified, use the first available input device
            if self.config.input_device_index is None:
                if not input_devices:
                    raise ValueError("No input devices found. Please connect a microphone or audio input device.")
                self.config.input_device_index = input_devices[0]
            
            # Get info for configured device
            device_info = self.audio.get_device_info_by_index(self.config.input_device_index)
            print(f"Selected device info: {device_info}")
            
            if device_info['maxInputChannels'] == 0:
                raise ValueError(f"Selected device {self.config.input_device_index} has no input channels. Please choose a valid input device.")
            
            # Use the device's native channels and sample rate
            self.config.channels = int(device_info['maxInputChannels'])
            self.config.sample_rate = int(device_info['defaultSampleRate'])
            
            # Speech detection state
            self.speech_detection_buffer = []
            self.silence_counter = 0
            self.session_silence_counter = 0
            self.is_recording = False
            
            # Silence thresholds
            self.wake_word_silence_threshold = recorder_config.wake_word_silence_threshold
            self.response_silence_threshold = recorder_config.response_silence_threshold
            
            # Calculate buffer size in chunks
            chunks_per_second = self.config.sample_rate / self.config.chunk_size
            self.buffer_size = int(chunks_per_second * self.recorder_config.buffer_duration)
            
        except Exception as e:
            self.on_error(e)
            raise
    
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
                input_device_index=self.config.input_device_index,
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
            is_wake_word_mode: Whether we're recording for word detection
        
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
            min_frames = int(self.config.sample_rate * self.recorder_config.buffer_duration / self.config.chunk_size)
            
            silence_threshold = (self.recorder_config.wake_word_silence_threshold if is_wake_word_mode 
                           else self.recorder_config.response_silence_threshold)
            
            print("\nRecording..." if not is_wake_word_mode else "Listening for trigger word...")
            
            while True:
                try:
                    data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                    if not data:  # Stop if we get empty data
                        break
                except IOError:
                    continue
                
                # Always collect frames in non-wake-word mode
                if not is_wake_word_mode:
                    frames.append(data)
                
                # Maintain rolling buffer for word detection
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
                            frames.append(data)
                    elif is_wake_word_mode:
                        frames.append(data)
                    silence_counter = 0
                
                # Handle silence detection
                if len(speech_detection_buffer) >= 2 and not any(speech_detection_buffer[-2:]):
                    silence_counter += self.config.chunk_size / self.config.sample_rate
                    if silence_counter >= silence_threshold:
                        if not is_wake_word_mode or (is_recording and len(frames) >= min_frames):
                            break
                else:
                    silence_counter = 0
            
            self.stream.stop_stream()
            try:
                self.stream.close()
            except Exception as e:
                self.on_error(e)
            self.stream = None
            
            # Ensure minimum frame count for wake word detection
            if is_wake_word_mode and len(frames) < min_frames:
                print("Recording too short, extending with silence...")
                silence_frame = b'\x00' * self.config.chunk_size
                frames.extend([silence_frame] * (min_frames - len(frames)))
            
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