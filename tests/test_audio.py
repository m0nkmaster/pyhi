import pytest
from unittest.mock import Mock, patch, mock_open
import wave
import io
import numpy as np
import speech_recognition as sr
from src.audio.analyzer import AudioAnalyzer
from src.audio.player import PyAudioPlayer
from src.audio.recorder import PyAudioRecorder
from src.config import AudioConfig, AudioPlayerConfig

def create_wav_data(duration_ms=1000, sample_rate=16000):
    """Create a dummy WAV file in memory"""
    num_samples = int(duration_ms * sample_rate / 1000)
    samples = np.random.randint(-32768, 32767, size=num_samples, dtype=np.int16)
    
    byte_io = io.BytesIO()
    with wave.open(byte_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    byte_io.seek(0)  # Reset file pointer to beginning
    return byte_io

@pytest.fixture
def audio_config():
    return AudioConfig()

@pytest.fixture
def player_config():
    return AudioPlayerConfig()

class TestAudioAnalyzer:
    def test_initialization(self, audio_config):
        analyzer = AudioAnalyzer(audio_config)
        assert analyzer.config == audio_config

    @patch('speech_recognition.Recognizer')
    def test_is_speech(self, mock_recognizer, audio_config):
        mock_recognizer.return_value.recognize_google.return_value = "test"
        
        # Create WAV data in memory
        wav_data = create_wav_data()
        
        analyzer = AudioAnalyzer(audio_config)
        result = analyzer.is_speech(wav_data)
        assert result is True
        mock_recognizer.return_value.recognize_google.assert_called_once()

    @patch('speech_recognition.Recognizer')
    def test_is_speech_no_speech(self, mock_recognizer, audio_config):
        mock_recognizer.return_value.recognize_google.side_effect = sr.UnknownValueError()
        
        wav_data = create_wav_data()
        
        analyzer = AudioAnalyzer(audio_config)
        result = analyzer.is_speech(wav_data)
        assert result is False

class TestPyAudioPlayer:
    def test_initialization(self, player_config):
        player = PyAudioPlayer(config=player_config)
        assert player.config == player_config

    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_play_wav_file(self, mock_system, mock_popen, player_config):
        mock_system.return_value = 'Darwin'  # macOS
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_process.poll.return_value = None
        
        player = PyAudioPlayer(config=player_config)
        wav_data = create_wav_data()
        player.play(wav_data.getvalue(), block=True)
        
        mock_popen.assert_called_once()
        cmd_args = mock_popen.call_args[0][0]
        assert cmd_args[0] == 'afplay'  # macOS command

    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_play_bytes(self, mock_system, mock_popen, player_config):
        mock_system.return_value = 'Darwin'  # macOS
        mock_process = Mock()
        mock_popen.return_value = mock_process
        mock_process.poll.return_value = None
        
        player = PyAudioPlayer(config=player_config)
        audio_bytes = np.zeros(1024, dtype=np.int16).tobytes()
        player.play(audio_bytes, block=True)
        
        mock_popen.assert_called_once()
        cmd_args = mock_popen.call_args[0][0]
        assert cmd_args[0] == 'afplay'  # macOS command

class TestPyAudioRecorder:
    def test_initialization(self, audio_config):
        recorder = PyAudioRecorder(audio_config)
        assert recorder.config == audio_config

    @patch('pyaudio.PyAudio')
    def test_record(self, mock_pyaudio, audio_config):
        mock_stream = Mock()
        mock_stream.read.return_value = np.zeros(1024, dtype=np.int16).tobytes()
        mock_pyaudio.return_value.open.return_value = mock_stream
        
        recorder = PyAudioRecorder(audio_config)
        audio_data = recorder.record_chunk()  # Use record_chunk instead of record
        
        assert isinstance(audio_data, bytes)
        mock_stream.read.assert_called_with(audio_config.chunk_size, exception_on_overflow=False)
