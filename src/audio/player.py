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
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._lock = threading.Lock()
        
    def __del__(self):
        """Cleanup PyAudio resources."""
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()

    def _convert_to_wav(self, audio_data: Union[str, bytes]) -> tuple[bytes, int, int, int, int]:
        """Convert audio data to WAV format."""
        if isinstance(audio_data, str):
            # Load from file
            audio = AudioSegment.from_file(audio_data)
        else:
            # Load from bytes
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            
        # Convert to WAV
        wav_data = io.BytesIO()
        audio.export(wav_data, format='wav')
        wav_data.seek(0)
        
        # Read WAV parameters
        with wave.open(wav_data, 'rb') as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
            
        return frames, rate, channels, width, len(frames)

    def play(self, audio_data: Union[str, bytes], volume: float = 1.0, block: bool = True) -> None:
        """Play audio using native PyAudio."""
        with self._lock:
            try:
                # Stop any existing playback
                self.stop()
                
                # Convert audio to WAV format
                frames, rate, channels, width, frame_count = self._convert_to_wav(audio_data)
                
                # Create a new stream
                self._stream = self._pa.open(
                    format=self._pa.get_format_from_width(width),
                    channels=channels,
                    rate=rate,
                    output=True,
                    output_device_index=self.config.output_device_index,
                    start=False,  # Don't start yet
                    stream_callback=None,  # Use blocking mode for better stability
                    frames_per_buffer=1024 * 4  # Larger buffer for stability
                )
                
                def play_audio():
                    try:
                        # Pre-buffer some data before starting
                        self._stream.start_stream()
                        
                        # Write data in chunks
                        chunk_size = 1024 * 4
                        for i in range(0, len(frames), chunk_size):
                            if not self._stream.is_active():
                                break
                            
                            chunk = frames[i:i + chunk_size]
                            if not chunk:
                                break
                                
                            if volume != 1.0:
                                # Apply volume in-place
                                chunk = b''.join(
                                    int(b * volume).to_bytes(1, byteorder='little', signed=True)
                                    for b in chunk
                                )
                            
                            try:
                                self._stream.write(chunk, exception_on_underflow=False)
                            except OSError as e:
                                logging.error(f"Stream error: {e}")
                                break
                                
                    except Exception as e:
                        logging.error(f"Playback error: {e}")
                    finally:
                        try:
                            if self._stream and self._stream.is_active():
                                self._stream.stop_stream()
                                self._stream.close()
                        except Exception as e:
                            logging.error(f"Error closing stream: {e}")
                        self._stream = None
                
                if block:
                    play_audio()
                else:
                    thread = threading.Thread(target=play_audio)
                    thread.daemon = True
                    thread.start()
                    
            except Exception as e:
                if self.on_error:
                    self.on_error(e)
                logging.error(f"Error playing audio: {e}")
                raise AudioPlayerError(f"Error playing audio: {e}")

    def stop(self):
        """Stop any currently playing audio."""
        if self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logging.error(f"Error stopping stream: {e}")
            finally:
                self._stream = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._stream is not None and self._stream.is_active()
