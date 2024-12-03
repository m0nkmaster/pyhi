import os
import platform
import subprocess
from typing import Optional, Callable
from ..utils.types import AudioPlayer
from ..config import AudioPlayerConfig

class AudioPlayerError(Exception):
    """Custom exception for audio player errors."""
    pass

class SystemAudioPlayer(AudioPlayer):
    def __init__(
        self,
        on_error: Optional[Callable[[Exception], None]] = None,
        config: Optional[AudioPlayerConfig] = None
    ):
        """Initialize the system audio player."""
        self.on_error = on_error or (lambda e: None)
        self._platform = platform.system().lower()
        self.config = config or AudioPlayerConfig()
        
        if self._platform not in ['darwin', 'linux', 'windows']:
            raise AudioPlayerError(f"Unsupported platform: {self._platform}")
    
    def play(self, audio_data: bytes) -> None:
        """Play audio data using the system's audio player."""
        try:
            # Save audio data to a temporary file
            with open(self.config.temp_file, "wb") as f:
                f.write(audio_data)
            
            # Play using system audio player
            self._play_audio_file(self.config.temp_file)
        except Exception as e:
            self.on_error(e)
            raise AudioPlayerError(f"Failed to play audio: {e}")
        finally:
            if os.path.exists(self.config.temp_file):
                os.remove(self.config.temp_file)
    
    def _play_audio_file(self, filename: str) -> None:
        """Play an audio file using the system's audio player."""
        try:
            if self._platform == 'darwin':
                # macOS - afplay can handle both MP3 and WAV
                subprocess.run(['afplay', filename], check=True)
            elif self._platform == 'linux':
                # Linux - try mpg123 for MP3, fallback to aplay for WAV
                if filename.endswith('.mp3'):
                    subprocess.run(['mpg123', filename], check=True)
                else:
                    subprocess.run(['aplay', filename], check=True)
            elif self._platform == 'windows':
                # Windows - PowerShell can handle both MP3 and WAV
                ps_command = f'(New-Object Media.SoundPlayer "{filename}").PlaySync()'
                subprocess.run(['powershell', '-c', ps_command], check=True)
        except subprocess.CalledProcessError as e:
            raise AudioPlayerError(f"Failed to play audio file: {e}")
