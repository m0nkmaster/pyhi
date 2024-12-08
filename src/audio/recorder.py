from typing import Optional, Callable
import time
import pyaudio
from ..utils.types import AudioConfig, AudioFrame, AudioAnalyzer
from ..config import AudioRecorderConfig

class AudioRecorderError(Exception):
    """Custom exception for audio recorder errors."""
    pass

class DeviceNotFoundError(Exception):
    """Exception raised when no suitable audio input device is found."""
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
            # Don't call on_error here since _setup_audio_device will handle it
            raise

    def _list_audio_devices(self) -> list[dict]:
        """List all available Audio Input Devices."""
        input_devices = []
        default_input = self.audio.get_default_input_device_info()
        
        for i in range(self.audio.get_device_count()):
            try:
                dev_info = self.audio.get_device_info_by_index(i)
                name = str(dev_info['name']).lower()
                
                # Skip devices with known virtual keywords
                virtual_keywords = ['blackhole', 'virtual', 'loopback', 'teams', 'soundflower', 'aggregate']
                if any(x in name for x in virtual_keywords):
                    if hasattr(self.config, 'device_config') and getattr(self.config.device_config, 'debug_audio', False):
                        print(f"Skipping virtual device: {name}")
                    continue
                
                if dev_info['maxInputChannels'] > 0:  # Only show input devices
                    device = {
                        'index': i,
                        'name': dev_info['name'],
                        'channels': int(dev_info['maxInputChannels']),
                        'sample_rate': int(dev_info['defaultSampleRate']),
                        'is_default': i == default_input['index'],
                        'latency': float(dev_info.get('defaultLowInputLatency', 0)),
                        'is_builtin': any(x in name for x in ['built-in', 'internal', 'system'])
                    }
                    input_devices.append(device)
            except Exception as e:
                if hasattr(self.config, 'device_config') and getattr(self.config.device_config, 'debug_audio', False):
                    print(f"Error getting device info for index {i}: {e}")
                continue
                
        # Sort devices by priority (built-in first, then by latency)
        input_devices.sort(key=lambda d: (not d['is_builtin'], d['latency']))
        return input_devices

    def _find_compatible_device(self, devices: list[dict]) -> Optional[dict]:
        """Find a compatible device based on configuration preferences."""
        if not devices:
            return None
            
        # If no device config or no preferred device, use priority-based selection
        if not hasattr(self.config, 'device_config') or \
           not hasattr(self.config.device_config, 'preferred_input_device_name') or \
           not self.config.device_config.preferred_input_device_name:
            
            # First try to find a built-in device
            built_in_devices = [d for d in devices if d['is_builtin']]
            if built_in_devices:
                # Among built-in devices, prefer the one with lowest latency
                return min(built_in_devices, key=lambda d: d['latency'])
            
            # If no built-in device, use the default device if available
            default_devices = [d for d in devices if d['is_default']]
            if default_devices:
                return default_devices[0]
            
            # Last resort: use the device with the lowest latency
            return min(devices, key=lambda d: d['latency'])
            
        # If preferred device name is specified, try to find it
        preferred_name = self.config.device_config.preferred_input_device_name.lower()
        matching_devices = [d for d in devices if preferred_name in d['name'].lower()]
        if matching_devices:
            # If multiple matches, prefer built-in or lowest latency
            return min(matching_devices, key=lambda d: (not d['is_builtin'], d['latency']))
        
        # If preferred device not found, fall back to priority-based selection
        return self._find_compatible_device([d for d in devices if d != self.config.device_config.preferred_input_device_name])

    def _setup_audio_device(self) -> None:
        """Set up the audio input device based on configuration."""
        try:
            # If device index is specified, verify it first
            if self.config.input_device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.config.input_device_index)
                if device_info['maxInputChannels'] == 0:
                    raise ValueError(f"Selected device {self.config.input_device_index} has no input channels")

            # List available devices if we need to find one
            if self.config.input_device_index is None:
                devices = self._list_audio_devices()
                if not devices:
                    raise DeviceNotFoundError("No input devices found. Please connect a microphone or audio input device.")
                
                device = self._find_compatible_device(devices)
                if not device:
                    raise DeviceNotFoundError("No compatible audio input device found")
                
                self.config.input_device_index = device['index']

            # Get final device info and configure
            device_info = self.audio.get_device_info_by_index(self.config.input_device_index)
            if device_info['maxInputChannels'] == 0:
                raise ValueError(f"Selected device {self.config.input_device_index} has no input channels")
                
            # Update configuration with device capabilities
            self.config.channels = int(device_info['maxInputChannels'])
            self.config.sample_rate = int(device_info['defaultSampleRate'])
            
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
            self.is_recording = True
            self.frames = []
            self.audio_buffer = []
        except Exception as e:
            self.on_error(e)
            raise AudioRecorderError(f"Failed to start recording: {str(e)}")
    
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
                
                # Maintain rolling buffer for all modes
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
                        # Include buffer content when speech starts in any mode
                        frames.extend(self.audio_buffer[-4:])  # Include last ~100ms before speech
                    frames.append(data)
                    silence_counter = 0
                elif is_recording:
                    # Continue collecting frames after speech until silence threshold
                    frames.append(data)
                
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