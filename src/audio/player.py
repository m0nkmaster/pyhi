import os
import platform
import subprocess
import sys
import threading
import logging
import time
from typing import Optional, Callable, Union
import pyaudio
from ..utils.types import AudioPlayer
from ..config import AudioPlayerConfig, AudioDeviceConfig

class AudioPlayerError(Exception):
    """Custom exception for audio player errors."""
    pass

class PyAudioPlayer(AudioPlayer):
    def __init__(self, on_error: Optional[Callable[[Exception], None]] = None, config: Optional[AudioPlayerConfig] = None, device_config: Optional[AudioDeviceConfig] = None):
        """Initialize the audio player."""
        self.config = config or AudioPlayerConfig()
        self.device_config = device_config
        self.on_error = on_error
        self._current_process = None
        self._lock = threading.Lock()

    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in the system."""
        return any(
            os.access(os.path.join(path, cmd), os.X_OK)
            for path in os.environ["PATH"].split(os.pathsep)
        )

    def _wait_for_process(self, process, timeout=None):
        """Wait for process to complete with timeout."""
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()

    def play(self, audio_data: Union[str, bytes], volume: float = 1.0, block: bool = True) -> None:
        """Play an audio file or audio data."""
        with self._lock:  # Ensure only one playback at a time
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
                self._wait_for_process(self._current_process, timeout=1)

            try:
                system = platform.system().lower()
                
                # Handle file path vs bytes
                temp_file = None
                if isinstance(audio_data, bytes):
                    temp_file = "temp_response.mp3"
                    with open(temp_file, "wb") as f:
                        f.write(audio_data)
                    audio_file = temp_file
                else:
                    audio_file = audio_data
                    if not os.path.exists(audio_file):
                        raise AudioPlayerError(f"Audio file not found: {audio_file}")

                # Set up command based on platform
                if system == "darwin":  # macOS
                    cmd = ['afplay', audio_file]
                    if volume != 1.0:
                        cmd.extend(['-v', str(volume)])
                else:  # Linux/Raspberry Pi
                    if self._command_exists('mpg123'):
                        # mpg123 has better quality and volume control
                        cmd = ['mpg123', '-q']
                        if volume != 1.0:
                            # mpg123 volume is in percentage (0-100)
                            vol_percent = min(100, int(volume * 100))
                            cmd.extend(['-f', str(vol_percent)])
                        cmd.append(audio_file)
                    elif self._command_exists('aplay'):
                        # aplay fallback with software volume control
                        if volume != 1.0:
                            if self._command_exists('sox'):
                                cmd = ['sox', '-v', str(volume), audio_file, '-d']
                            else:
                                cmd = ['aplay', '-q', audio_file]
                                logging.warning("Volume control not available without sox")
                        else:
                            cmd = ['aplay', '-q', audio_file]
                    else:
                        raise AudioPlayerError("No suitable audio player found (mpg123 or aplay required)")

                # Start playback
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                if block:
                    # Wait for playback to complete with a reasonable timeout
                    self._wait_for_process(self._current_process, timeout=10)
                else:
                    # Start a thread to prevent zombie processes
                    threading.Thread(
                        target=self._wait_for_process,
                        args=(self._current_process, 10),
                        daemon=True
                    ).start()

            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                logging.error(f"Error playing audio: {e}")
                raise AudioPlayerError(f"Error playing audio: {e}")
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

    def stop(self):
        """Stop any currently playing audio."""
        if self._current_process and self._current_process.poll() is None:
            self._current_process.terminate()
            self._wait_for_process(self._current_process, timeout=1)

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._current_process and self._current_process.poll() is None
