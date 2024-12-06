import os
import platform
import subprocess
from typing import Optional, Callable
import pyaudio
from ..utils.types import AudioPlayer
from ..config import AudioPlayerConfig, AudioDeviceConfig

class AudioPlayerError(Exception):
    """Custom exception for audio player errors."""
    pass

class DeviceNotFoundError(AudioPlayerError):
    """Raised when an audio device cannot be found."""
    pass

class SystemAudioPlayer(AudioPlayer):
    def __init__(
        self,
        on_error: Optional[Callable[[Exception], None]] = None,
        config: Optional[AudioPlayerConfig] = None,
        device_config: Optional[AudioDeviceConfig] = None
    ):
        """Initialize the system audio player."""
        self.on_error = on_error or (lambda e: None)
        self._platform = platform.system().lower()
        self.config = config or AudioPlayerConfig()
        self.device_config = device_config or AudioDeviceConfig()
        self._pa = pyaudio.PyAudio()
        
        if self._platform not in ['darwin', 'linux', 'windows']:
            raise AudioPlayerError(f"Unsupported platform: {self._platform}")
        
        # Check for mpg123 on Linux
        if self._platform == 'linux':
            try:
                subprocess.run(['which', 'mpg123'], 
                             check=True, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                raise AudioPlayerError(
                    "mpg123 not found. Please install it with: sudo apt-get install mpg123"
                )

        if self.device_config.list_devices_on_start:
            self._list_audio_devices()

        if self.device_config.auto_select_device:
            self._setup_audio_device()

    def _list_audio_devices(self) -> None:
        """List all available audio devices."""
        print("\nAvailable Audio Output Devices:")
        for i in range(self._pa.get_device_count()):
            dev_info = self._pa.get_device_info_by_index(i)
            if dev_info['maxOutputChannels'] > 0:
                print(f"Index {i}: {dev_info['name']}")

    def _setup_audio_device(self) -> None:
        """Set up the audio output device based on configuration."""
        if self.config.output_device_index is not None:
            # Verify the specified device exists
            try:
                dev_info = self._pa.get_device_info_by_index(self.config.output_device_index)
                if dev_info['maxOutputChannels'] == 0:
                    raise DeviceNotFoundError("Specified output device has no output channels")
                return
            except Exception as e:
                if not self.device_config.fallback_to_default:
                    raise DeviceNotFoundError(f"Specified output device not found: {e}")

        # Try to find preferred device by name
        if self.device_config.preferred_output_device_name:
            for i in range(self._pa.get_device_count()):
                dev_info = self._pa.get_device_info_by_index(i)
                if (dev_info['maxOutputChannels'] > 0 and
                    self.device_config.preferred_output_device_name.lower() in dev_info['name'].lower()):
                    self.config.output_device_index = i
                    return

        # Fallback to default device
        if self.device_config.fallback_to_default:
            self.config.output_device_index = self._pa.get_default_output_device_info()['index']
        else:
            raise DeviceNotFoundError("No suitable output device found")

    def play(self, audio_data: bytes) -> None:
        """Play audio data using the system's audio player."""
        retries = 0
        last_exception = None
        
        while retries < (self.device_config.max_retries if self.device_config.retry_on_error else 1):
            try:
                # Save audio data to a temporary file
                with open(self.config.temp_file, "wb") as f:
                    f.write(audio_data)
                
                # Play using system audio player
                self._play_audio_file(self.config.temp_file)
                return  # Success, exit the function
                
            except Exception as e:
                last_exception = e
                retries += 1
                if self.device_config.debug_audio:
                    print(f"Retry {retries}: Failed to play audio - {e}")
            
            if os.path.exists(self.config.temp_file):
                try:
                    os.remove(self.config.temp_file)
                except:
                    pass
        
        # If we get here, all retries failed
        self.on_error(last_exception)
        raise AudioPlayerError(f"Failed to play audio after {retries} attempts: {last_exception}")
     
    def _play_audio_file(self, filename: str) -> None:
        """Play an audio file using the system's audio player."""
        try:
            if self._platform == 'darwin':
                volume = str(self.config.volume_level)
                subprocess.run(['afplay', '-v', volume, filename], check=True)
            
            elif self._platform == 'linux':
                device_arg = []
                if self.config.output_device_index is not None:
                    dev_info = self._pa.get_device_info_by_index(self.config.output_device_index)
                    device_arg = ['-a', dev_info['name']]
                subprocess.run(['mpg123', '-q'] + device_arg + [filename], check=True)
            
            elif self._platform == 'windows':
                ps_command = f'(New-Object Media.SoundPlayer "{filename}").PlaySync()'
                subprocess.run(['powershell', '-c', ps_command], check=True)
                
        except subprocess.CalledProcessError as e:
            raise AudioPlayerError(f"Failed to play audio file: {e}")

    def __del__(self):
        """Clean up PyAudio resources."""
        if hasattr(self, '_pa'):
            self._pa.terminate()
