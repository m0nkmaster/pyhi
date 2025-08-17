"""
Simplified unified audio handler for PyHi voice assistant.
Combines recording, playback, and speech recognition in a single module.
"""

import os
import logging
import tempfile
import asyncio
from pathlib import Path
from typing import Optional, Union
import threading

import pyaudio
import speech_recognition as sr
from pydub import AudioSegment
import io

from config import Config, AudioConfig


class AudioError(Exception):
    """Base exception for audio-related errors."""
    pass


class AudioHandler:
    """Unified audio handler for recording, playback, and speech recognition."""
    
    def __init__(self, config: AudioConfig):
        """
        Initialize the audio handler.
        
        Args:
            config: Audio configuration
        """
        self.config = config
        self._pa = pyaudio.PyAudio()
        self._recognizer = sr.Recognizer()
        self._microphone = None
        self._playback_lock = threading.Lock()
        
        # Initialize microphone
        self._setup_microphone()
        
        # Assets directory for sound files
        self._assets_dir = Path(__file__).parent / "assets"
        
    def __del__(self):
        """Cleanup PyAudio resources."""
        try:
            if hasattr(self, '_pa'):
                self._pa.terminate()
        except Exception as e:
            logging.debug(f"Error terminating PyAudio: {e}")
    
    def _setup_microphone(self):
        """Setup microphone for speech recognition."""
        try:
            # Use default microphone
            self._microphone = sr.Microphone(
                sample_rate=self.config.sample_rate,
                chunk_size=self.config.chunk_size
            )
            
            # Calibrate for ambient noise
            with self._microphone as source:
                logging.info("Calibrating microphone for ambient noise...")
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                
        except Exception as e:
            raise AudioError(f"Failed to setup microphone: {e}")
    
    def record_chunk(self) -> bytes:
        """
        Record a single audio chunk for wake word detection.
        
        Returns:
            Raw audio data as bytes
        """
        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            
            data = stream.read(self.config.chunk_size, exception_on_overflow=False)
            stream.close()
            return data
            
        except Exception as e:
            raise AudioError(f"Failed to record audio chunk: {e}")
    
    async def record_speech(self) -> str:
        """
        Record speech and convert to text.
        
        Returns:
            Transcribed text from speech
        """
        try:
            logging.info("Recording speech...")
            
            # Record audio in a separate thread to avoid blocking
            audio_data = await asyncio.get_event_loop().run_in_executor(
                None, self._record_speech_sync
            )
            
            # Transcribe audio
            text = await asyncio.get_event_loop().run_in_executor(
                None, self._transcribe_audio, audio_data
            )
            
            logging.info(f"Speech recognized: {text}")
            return text
            
        except Exception as e:
            raise AudioError(f"Failed to record speech: {e}")
    
    def _record_speech_sync(self) -> sr.AudioData:
        """Synchronous speech recording."""
        with self._microphone as source:
            # Listen for speech with timeout
            audio = self._recognizer.listen(
                source,
                timeout=10,  # Maximum wait time
                phrase_time_limit=10  # Maximum phrase length
            )
            return audio
    
    def _transcribe_audio(self, audio_data: sr.AudioData) -> str:
        """Transcribe audio data to text."""
        try:
            # Use Google Speech Recognition
            text = self._recognizer.recognize_google(audio_data)
            return text
            
        except sr.UnknownValueError:
            raise AudioError("Could not understand speech")
        except sr.RequestError as e:
            raise AudioError(f"Speech recognition service error: {e}")
    
    async def speak(self, text: str) -> None:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to convert to speech
        """
        try:
            # This will be implemented when we integrate with AI client
            # For now, just log the text
            logging.info(f"Speaking: {text}")
            
        except Exception as e:
            raise AudioError(f"Failed to speak text: {e}")
    
    def play_audio_data(self, audio_data: bytes, format_type: str = "mp3") -> None:
        """
        Play raw audio data.
        
        Args:
            audio_data: Raw audio data
            format_type: Audio format (mp3, wav, etc.)
        """
        try:
            with self._playback_lock:
                # Convert to AudioSegment
                if format_type == "mp3":
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                elif format_type == "wav":
                    audio = AudioSegment.from_wav(io.BytesIO(audio_data))
                else:
                    raise AudioError(f"Unsupported audio format: {format_type}")
                
                # Convert to wav format for playback
                wav_data = audio.export(format="wav")
                
                # Play using PyAudio
                self._play_wav_data(wav_data.read())
                
        except Exception as e:
            raise AudioError(f"Failed to play audio data: {e}")
    
    def play_sound_file(self, filename: str) -> None:
        """
        Play a sound file from the assets directory.
        
        Args:
            filename: Name of the sound file in assets directory
        """
        try:
            file_path = self._assets_dir / filename
            if not file_path.exists():
                logging.warning(f"Sound file not found: {file_path}")
                return
            
            with self._playback_lock:
                # Load and play audio file
                audio = AudioSegment.from_file(str(file_path))
                wav_data = audio.export(format="wav")
                self._play_wav_data(wav_data.read())
                
        except Exception as e:
            logging.error(f"Failed to play sound file {filename}: {e}")
    
    def _play_wav_data(self, wav_data: bytes) -> None:
        """Play WAV data using PyAudio."""
        try:
            # Parse WAV data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(wav_data)
                tmp_file.flush()
                
                # Open and play the file
                import wave
                with wave.open(tmp_file.name, 'rb') as wf:
                    # Open PyAudio stream
                    stream = self._pa.open(
                        format=self._pa.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True
                    )
                    
                    # Play audio
                    chunk_size = 1024
                    data = wf.readframes(chunk_size)
                    while data:
                        stream.write(data)
                        data = wf.readframes(chunk_size)
                    
                    stream.close()
                
                # Cleanup temp file
                os.unlink(tmp_file.name)
                
        except Exception as e:
            raise AudioError(f"Failed to play WAV data: {e}")
    
    def play_activation_sound(self) -> None:
        """Play the activation sound."""
        self.play_sound_file(self.config.activation_sound)
    
    def play_confirmation_sound(self) -> None:
        """Play the confirmation sound."""
        self.play_sound_file(self.config.confirmation_sound)
    
    def play_ready_sound(self) -> None:
        """Play the ready sound."""
        self.play_sound_file(self.config.ready_sound)
    
    def play_sleep_sound(self) -> None:
        """Play the sleep sound."""
        self.play_sound_file(self.config.sleep_sound)


def create_audio_handler(config_path: Optional[str] = None) -> AudioHandler:
    """
    Convenience function to create an AudioHandler with configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured AudioHandler instance
    """
    config = Config.load(config_path)
    return AudioHandler(config.audio)