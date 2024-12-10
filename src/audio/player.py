import os
import platform
import subprocess
from typing import Optional, Callable, Union
import pyaudio
from ..utils.types import AudioPlayer
from ..config import AudioPlayerConfig, AudioDeviceConfig

class AudioPlayerError(Exception):
    """Custom exception for audio player errors."""
    pass

class SystemAudioPlayer(AudioPlayer):
    def __init__(self, on_error: Optional[Callable[[Exception], None]] = None, config: Optional[AudioPlayerConfig] = None, device_config: Optional[AudioDeviceConfig] = None):
        """Initialize the audio player."""
        self.config = config or AudioPlayerConfig()
        self.device_config = device_config or AudioDeviceConfig()
        self.on_error = on_error
        self._current_process = None
        self._playing = False

    def play(self, audio_data: Union[bytes, str], volume: float | None = None, device: str | None = None, block: bool = True) -> None:
        """
        Play audio data using the system's audio player.
        
        Args:
            audio_data: Raw audio data in bytes or a path to an audio file
            volume: Optional volume level (0.0 to 1.0)
            device: Optional device name to play on
            block: Whether to block until playback is complete
        """
        # Stop any currently playing audio first
        self.stop()

        try:
            # Determine the appropriate command based on OS
            system = platform.system().lower()
            if system == "darwin":  # macOS
                cmd = ["afplay"]
                if volume is not None:
                    cmd.extend(["-v", str(volume)])
            elif system == "linux":
                # Try mpg123 first, fall back to aplay
                if self._command_exists("mpg123"):
                    cmd = ["mpg123"]
                    if volume is not None:
                        vol = int(volume * 100)
                        cmd.extend(["-f", str(vol)])
                elif self._command_exists("aplay"):
                    cmd = ["aplay"]
                else:
                    raise AudioPlayerError("No suitable audio player found. Please install mpg123 or aplay.")
            else:
                raise AudioPlayerError(f"Unsupported operating system: {system}")
            
            # Handle file path or bytes
            if isinstance(audio_data, str):
                if not os.path.exists(audio_data):
                    raise AudioPlayerError(f"Audio file not found: {audio_data}")
                cmd.append(audio_data)
            else:
                # Save bytes to temp file
                with open("temp_response.mp3", "wb") as f:
                    f.write(audio_data)
                cmd.append("temp_response.mp3")

            # Start playback with PIPE to prevent blocking
            self._current_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            self._playing = True

            if block:
                self._current_process.communicate()  # Wait but don't block stderr/stdout
                self._playing = False
                self._current_process = None

        except Exception as e:
            if self.on_error:
                self.on_error(e)
            raise AudioPlayerError(f"Error playing audio: {str(e)}")

    def stop(self):
        """Stop any currently playing audio."""
        if self._current_process and self._playing:
            self._current_process.terminate()
            self._current_process = None
            self._playing = False

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._playing

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in the system PATH."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
