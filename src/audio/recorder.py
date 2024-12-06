from typing import Optional, Callable
import time
import pyaudio
from ..utils.types import AudioConfig, AudioFrame, AudioAnalyzer
from ..config import AudioRecorderConfig

class AudioRecorderError(Exception):
    """Custom exception for audio recorder errors."""
    pass

class DeviceNotFoundError(AudioRecorderError):
    """Raised when an audio device cannot be found."""
    pass

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
            self._setup_audio_device()
            
            # Speech detection state
            self.speech_detection_buffer = []
            self.silence_counter = 0
            self.session_silence_counter = 0
            self.is_recording = False
            
            # Silence thresholds
            self.wake_word_silence_threshold = self.recorder_config.wake_word_silence_threshold
            self.response_silence_threshold = self.recorder_config.response_silence_threshold
            
            # Calculate buffer size in chunks
            chunks_per_second = self.config.sample_rate / self.config.chunk_size
            self.buffer_size = int(chunks_per_second * self.recorder_config.buffer_duration)
            
        except Exception as e:
            self.on_error(e)
            raise

    def _list_audio_devices(self) -> list[dict]:
        """List all available audio input devices."""
        input_devices = []
        print("\nAvailable audio input devices:")
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0:  # Only show input devices
                input_devices.append({
                    'index': i,
                    'name': dev_info['name'],
                    'channels': dev_info['maxInputChannels'],
                    'sample_rate': dev_info['defaultSampleRate']
                })
                if self.config.device_config.debug_audio:
                    print(f"Device {i}: {dev_info['name']}")
                    print(f"    Input channels: {dev_info['maxInputChannels']}")
                    print(f"    Sample rate: {dev_info['defaultSampleRate']}")
        return input_devices

    def _find_compatible_device(self, devices: list[dict]) -> Optional[dict]:
        """Find a compatible device based on configuration preferences."""
        # Check if preferred device name is specified
        if self.config.device_config.preferred_input_device_name:
            for device in devices:
                if self.config.device_config.preferred_input_device_name.lower() in device['name'].lower():
                    return device

        # Check for devices matching preferred sample rates and channels
        for rate in self.config.device_config.preferred_sample_rates:
            for channels in self.config.device_config.preferred_channels:
                for device in devices:
                    if (abs(device['sample_rate'] - rate) < 100 and  # Allow small sample rate difference
                        device['channels'] >= channels):
                        return device

        # Return first available device if no match found
        return devices[0] if devices else None

    def _setup_audio_device(self) -> None:
        """Set up the audio input device based on configuration."""
        # List available devices
        devices = self._list_audio_devices()
        if not devices:
            raise DeviceNotFoundError("No input devices found. Please connect a microphone or audio input device.")

        # If device index is specified, verify it
        if self.config.input_device_index is not None:
            try:
                device_info = self.audio.get_device_info_by_index(self.config.input_device_index)
                if device_info['maxInputChannels'] == 0:
                    raise DeviceNotFoundError(f"Selected device {self.config.input_device_index} has no input channels")
            except Exception as e:
                if not self.config.device_config.fallback_to_default:
                    raise DeviceNotFoundError(f"Invalid input device index: {e}")
                self.config.input_device_index = None

        # Find compatible device if no valid index specified
        if self.config.input_device_index is None:
            device = self._find_compatible_device(devices)
            if not device:
                raise DeviceNotFoundError("No compatible audio input device found")
            
            self.config.input_device_index = device['index']
            if self.config.device_config.debug_audio:
                print(f"\nSelected audio device: {device['name']}")
                print(f"Index: {device['index']}")
                print(f"Channels: {device['channels']}")
                print(f"Sample rate: {device['sample_rate']}")

        # Configure device parameters
        device_info = self.audio.get_device_info_by_index(self.config.input_device_index)
        self.config.channels = min(int(device_info['maxInputChannels']), 
                                 max(self.config.device_config.preferred_channels))
        self.config.sample_rate = int(device_info['defaultSampleRate'])
    
    def start_recording(self) -> None:
        """Start recording audio."""
        if self.stream is not None:
            return
        
        retries = 0
        while retries < (self.config.device_config.max_retries if self.config.device_config.retry_on_error else 1):
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
                break
            except Exception as e:
                retries += 1
                if retries >= self.config.device_config.max_retries or not self.config.device_config.retry_on_error:
                    self.on_error(e)
                    raise AudioRecorderError(f"Failed to start recording after {retries} attempts: {e}")
                if self.config.device_config.debug_audio:
                    print(f"Retry {retries}: Failed to start recording - {e}")
                time.sleep(0.1)  # Short delay between retries
    
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
            
            silence_threshold = (self.wake_word_silence_threshold if is_wake_word_mode 
                               else self.response_silence_threshold)
            
            if self.config.device_config.debug_audio:
                print("\nRecording..." if not is_wake_word_mode else "Listening for trigger word...")
            
            while True:
                try:
                    data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                    if not data:  # Stop if we get empty data
                        break
                except IOError as e:
                    if self.config.device_config.debug_audio:
                        print(f"IOError during recording: {e}")
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
                        if not is_wake_word_mode or is_recording:
                            break
                else:
                    silence_counter = 0
            
            self.stream.stop_stream()
            try:
                self.stream.close()
            except Exception as e:
                if self.config.device_config.debug_audio:
                    print(f"Error closing stream: {e}")
                self.on_error(e)
            self.stream = None
            
            return b''.join(frames)
            
        except Exception as e:
            self.on_error(e)
            raise AudioRecorderError(f"Error during recording: {e}")
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
        
        if hasattr(self, 'audio') and self.audio is not None:
            try:
                self.audio.terminate()
            except:
                pass 