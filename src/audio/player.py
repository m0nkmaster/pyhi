import os
import platform
import threading
import logging
import time
from typing import Optional, Callable, Union
import pyaudio
import wave
import io
from pydub import AudioSegment
import numpy as np
from ..utils.types import AudioPlayer
from ..config import AudioPlayerConfig, AudioDeviceConfig

class AudioPlayerError(Exception):
    """Custom exception for audio player errors."""
    pass

class PyAudioPlayer(AudioPlayer):
    def __init__(self, config=None, device_config=None, on_error=None):
        """Initialize the audio player."""
        self.config = config or AudioPlayerConfig()
        self.device_config = device_config
        self.on_error = on_error
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._lock = threading.Lock()
        self._current_thread = None
        self._stop_requested = False
        self._chunk_size = 1024 * 4
        self._frames_per_buffer = 2048

    def __del__(self):
        """Cleanup PyAudio resources."""
        self.stop()
        if hasattr(self, '_pa'):
            try:
                self._pa.terminate()
            except Exception as e:
                logging.debug(f"Error terminating PyAudio: {e}")

    def _convert_to_wav(self, audio_data):
        """Convert audio data to WAV format with consistent parameters."""
        try:
            if isinstance(audio_data, str):
                # Load from file
                audio = AudioSegment.from_file(audio_data)
            else:
                # Raw audio data (assuming mp3 format from TTS)
                audio = AudioSegment.from_mp3(io.BytesIO(audio_data))

            # Ensure consistent format
            audio = audio.set_frame_rate(44100).set_channels(1).set_sample_width(2)
            return audio.raw_data
            
        except Exception as e:
            logging.error(f"Error converting audio: {e}")
            raise AudioPlayerError(f"Error converting audio: {e}")

    def stop(self):
        """Stop any currently playing audio."""
        self._stop_requested = True
        if self._stream:
            try:
                # Ignore PortAudio errors during cleanup
                try:
                    self._stream.stop_stream()
                except OSError as e:
                    if e.errno != -9986:  # Ignore expected PortAudio errors
                        logging.debug(f"Error stopping stream: {e}")
                
                try:
                    self._stream.close()
                except OSError as e:
                    if e.errno != -9986:  # Ignore expected PortAudio errors
                        logging.debug(f"Error closing stream: {e}")
            except Exception as e:
                logging.debug(f"Error during stream cleanup: {e}")
            finally:
                self._stream = None

    def play(self, audio_data: Union[str, bytes], volume: float = 1.0, block: bool = True) -> None:
        """Play audio using native PyAudio."""
        with self._lock:
            try:
                # Stop any existing playback
                self.stop()
                self._stop_requested = False
                
                # Convert audio to raw format
                raw_data = self._convert_to_wav(audio_data)
                
                # Create stream
                self._stream = self._pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    output=True,
                    frames_per_buffer=self._frames_per_buffer
                )
                
                def play_audio():
                    try:
                        # Write data in chunks
                        chunk_size = self._chunk_size
                        for i in range(0, len(raw_data), chunk_size):
                            if self._stop_requested:
                                break
                            
                            chunk = raw_data[i:i + chunk_size]
                            if not chunk:
                                break
                                
                            if volume != 1.0:
                                # Apply volume adjustment
                                chunk_array = np.frombuffer(chunk, dtype=np.int16)
                                chunk_array = (chunk_array * volume).astype(np.int16)
                                chunk = chunk_array.tobytes()
                            
                            if self._stream and not self._stop_requested:
                                self._stream.write(chunk, exception_on_underflow=False)
                                
                    except Exception as e:
                        logging.error(f"Playback error: {e}")
                        if self.on_error:
                            self.on_error(e)
                    finally:
                        # Only stop the stream, don't try to join the thread
                        if self._stream:
                            try:
                                self._stream.stop_stream()
                                self._stream.close()
                            except:
                                pass
                            self._stream = None
                
                if block:
                    play_audio()
                else:
                    thread = threading.Thread(target=play_audio)
                    thread.daemon = True
                    thread.start()
                    
            except Exception as e:
                logging.error(f"Error playing audio: {e}")
                if self.on_error:
                    self.on_error(e)
                self.stop()
                raise AudioPlayerError(f"Error playing audio: {e}")

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._stream is not None and self._stream.is_active()
