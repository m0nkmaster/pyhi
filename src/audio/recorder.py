from typing import Optional, Deque
import pyaudio
import numpy as np
from ..utils.types import AudioConfig
from ..config import AudioRecorderConfig
import speech_recognition as sr
from collections import deque

class AudioRecorderError(Exception):
    """Custom exception for audio recorder errors."""
    pass

class PyAudioRecorder:
    def __init__(
        self,
        config: AudioConfig,
        recorder_config: Optional[AudioRecorderConfig] = None
    ):
        """Initialize the PyAudio recorder."""
        self.config = config
        self.recorder_config = recorder_config or AudioRecorderConfig()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recognizer = sr.Recognizer()
        
        # Calculate chunks per second more precisely
        self.chunks_per_second = self.config.sample_rate / self.config.chunk_size
        buffer_chunks = int(self.chunks_per_second * 2)  # 2 seconds buffer
        self.audio_buffer: Deque[bytes] = deque(maxlen=buffer_chunks)

    def clear_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()

    def record_chunk(self) -> bytes:
        """Record a fixed chunk of audio for wake word detection."""
        if self.stream is None:
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
        
        try:
            # Record exactly 1 chunk of audio
            data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            if data:
                self.audio_buffer.append(data)
            return data
            
        except Exception as e:
            raise AudioRecorderError(f"Error recording audio: {e}")

    def record_speech(self) -> Optional[bytes]:
        """Record speech until silence is detected."""
        if self.stream is None:
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                input_device_index=None  # Use default input device
            )
        
        try:
            frames = []
            silence_chunks = 0
            speech_detected = False
            
            # Dynamic silence threshold based on ambient noise
            # Record a short sample to determine ambient noise level
            ambient_samples = []
            for _ in range(10):  # Sample for 10 chunks
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                if data:
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    ambient_samples.append(np.abs(audio_data).mean())
            
            # Set silence threshold to 2x the average ambient noise
            ambient_level = np.mean(ambient_samples)
            silence_threshold = max(150, ambient_level * 2)  # At least 150 to avoid ultra-sensitive
            
            # Calculate silence chunks based on config
            chunks_per_second = self.config.sample_rate / self.config.chunk_size
            max_silence_chunks = round(chunks_per_second * self.recorder_config.response_silence_threshold)
            
            # First wait for speech to begin
            max_wait_chunks = round(chunks_per_second * 1)  # Wait up to 1 second for speech to start
            for _ in range(max_wait_chunks):
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                if not data:
                    continue
                    
                audio_data = np.frombuffer(data, dtype=np.int16)
                current_volume = np.abs(audio_data).mean()
                
                if current_volume > silence_threshold:
                    frames.append(data)
                    speech_detected = True
                    break
            
            # If no speech detected during wait period, return None
            if not speech_detected:
                return None
            
            # Keep recording until silence threshold is met
            while True:
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                if not data:
                    continue
                    
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                current_volume = np.abs(audio_data).mean()
                
                # Check for silence
                if current_volume < silence_threshold:
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        break
                else:
                    silence_chunks = 0  # Reset silence counter when we hear something
            
            # Only return if we captured enough frames
            if len(frames) > max_wait_chunks:  # Ensure we have more than just the initial detection
                return b''.join(frames)
            return None
            
        except Exception as e:
            raise AudioRecorderError(f"Error recording audio: {e}")

    def __del__(self):
        """Clean up resources."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass