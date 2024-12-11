from typing import Optional, Deque
import pyaudio
import numpy as np
from ..utils.types import AudioConfig
from ..config import AudioRecorderConfig
import speech_recognition as sr
from collections import deque
import logging

class AudioRecorderError(Exception):
    """Custom exception for audio recorder errors."""
    pass

class PyAudioRecorder:
    def __init__(
        self,
        config: AudioConfig,
        recorder_config: Optional[AudioRecorderConfig] = None
    ):
        """Initialize the PyAudio recorder using SpeechRecognition."""
        self.config = config
        self.recorder_config = recorder_config or AudioRecorderConfig()
        self.recognizer = sr.Recognizer()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.input_device_index = None

    def clear_buffer(self):
        """Clear the audio buffer."""
        # Removed buffer management

    def record_chunk(self) -> bytes:
        """Record a fixed chunk of audio for wake word detection."""
        if self.stream is None:
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size,
                input_device_index=self.input_device_index
            )
        try:
            audio_data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
            return audio_data
        except IOError as e:
            if e.errno == pyaudio.paInputOverflowed:
                logging.warning("Input overflowed, skipping this chunk.")
                return b''  # Return empty bytes to indicate no data was captured
            else:
                raise

    def recognize_speech_from_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """Recognize speech from an audio chunk using the SpeechRecognition library."""
        audio_data = sr.AudioData(audio_chunk, self.config.sample_rate, self.config.format)
        try:
            return self.recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            logging.warning("Google Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logging.error(f"Could not request results from Google Speech Recognition service; {e}")
            return None

    def record_speech(self) -> Optional[bytes]:
        """Record speech until silence is detected."""
        if self.stream is None or not self.stream.is_active():
            try:
                if self.stream:
                    self.stream.stop_stream()
                    self.stream.close()
                
                self.stream = self.audio.open(
                    format=self.config.format,
                    channels=self.config.channels,
                    rate=self.config.sample_rate,
                    input=True,
                    frames_per_buffer=self.config.chunk_size,
                    input_device_index=self.input_device_index,
                    start=True  # Start stream immediately
                )
            except Exception as e:
                raise AudioRecorderError(f"Error opening audio stream: {e}")
        
        try:
            frames = []
            silence_chunks = 0
            speech_detected = False
            
            # Calibrate silence threshold from ambient noise
            ambient_levels = []
            for _ in range(5):  # Sample ambient noise for 5 chunks
                data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                if data:
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    ambient_levels.append(np.abs(audio_data).mean())
            
            # Set threshold to 2x the average ambient level
            silence_threshold = max(300, np.mean(ambient_levels) * 2 if ambient_levels else 300)
            
            # Calculate timing parameters
            chunks_per_second = self.config.sample_rate / self.config.chunk_size
            max_silence_chunks = round(chunks_per_second * self.recorder_config.response_silence_threshold)
            max_wait_chunks = round(chunks_per_second * 2)  # Wait up to 2 seconds for speech to start
            
            # First wait for speech to begin
            for _ in range(max_wait_chunks):
                try:
                    data = self.stream.read(self.config.chunk_size, exception_on_overflow=False)
                    if not data:
                        continue
                    
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    current_volume = np.abs(audio_data).mean()
                    
                    if current_volume > silence_threshold:
                        frames.append(data)
                        speech_detected = True
                        break
                except IOError as e:
                    if "Input overflowed" in str(e):
                        continue
                    raise
            
            # If no speech detected during wait period, return None
            if not speech_detected:
                return None
            
            # Keep recording until silence threshold is met
            while True:
                try:
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
                except IOError as e:
                    # Handle ALSA buffer overrun
                    if "Input overflowed" in str(e):
                        continue
                    raise
            
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