import pytest
import asyncio
import tempfile
import wave
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from src.audio import AudioHandler
from src.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def audio_handler(config):
    return AudioHandler(config)


def create_test_wav_file(duration_ms=1000, sample_rate=16000):
    """Create a test WAV file"""
    num_samples = int(duration_ms * sample_rate / 1000)
    samples = np.random.randint(-32768, 32767, size=num_samples, dtype=np.int16)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        with wave.open(f, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples.tobytes())
        return f.name


class TestAudioHandler:
    def test_initialization(self, config):
        """Test AudioHandler initialization"""
        handler = AudioHandler(config)
        assert handler.config == config
        assert handler.pyaudio is None  # Not initialized until first use


    @patch('pyaudio.PyAudio')
    @patch('speech_recognition.Recognizer')
    def test_record_speech(self, mock_recognizer_class, mock_pyaudio, audio_handler):
        """Test speech recording functionality"""
        # Mock PyAudio setup
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_pa.open.return_value = mock_stream
        
        # Mock audio data that would trigger silence detection
        audio_chunks = [b'\x00' * 1024] * 10  # Silent audio data
        mock_stream.read.side_effect = audio_chunks
        
        # Mock recognizer
        mock_recognizer = Mock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_google.return_value = "test speech"
        
        # Test recording
        result = audio_handler.record_speech()
        
        # Verify stream was opened and audio was recorded
        mock_pa.open.assert_called_once()
        assert mock_stream.read.called
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()


    @patch('pyaudio.PyAudio')
    def test_play_audio_file(self, mock_pyaudio, audio_handler):
        """Test audio file playback"""
        # Create a test WAV file
        test_file = create_test_wav_file()
        
        try:
            with patch('subprocess.run') as mock_subprocess:
                audio_handler.play_audio_file(test_file)
                mock_subprocess.assert_called_once()
                # Verify the command includes the test file
                call_args = mock_subprocess.call_args[0][0]
                assert test_file in call_args
        finally:
            import os
            os.unlink(test_file)


    @patch('pyaudio.PyAudio')
    def test_play_audio_bytes(self, mock_pyaudio, audio_handler):
        """Test playing audio from bytes"""
        test_audio_data = np.random.randint(-32768, 32767, size=1024, dtype=np.int16).tobytes()
        
        with patch('subprocess.run') as mock_subprocess:
            audio_handler.play_audio_bytes(test_audio_data)
            mock_subprocess.assert_called_once()


    @pytest.mark.asyncio
    async def test_async_methods(self, audio_handler):
        """Test async wrapper methods"""
        with patch.object(audio_handler, 'record_speech', return_value="test") as mock_record:
            result = await audio_handler.record_speech_async()
            assert result == "test"
            mock_record.assert_called_once()

        with patch.object(audio_handler, 'play_audio_file') as mock_play:
            await audio_handler.play_audio_file_async("test.wav")
            mock_play.assert_called_once_with("test.wav")


    def test_cleanup(self, audio_handler):
        """Test resource cleanup"""
        # Mock PyAudio instance
        mock_pa = Mock()
        audio_handler.pyaudio = mock_pa
        
        audio_handler.cleanup()
        mock_pa.terminate.assert_called_once()
        assert audio_handler.pyaudio is None


    @patch('speech_recognition.Recognizer')
    def test_speech_recognition_error_handling(self, mock_recognizer_class, audio_handler):
        """Test speech recognition error handling"""
        import speech_recognition as sr
        
        mock_recognizer = Mock()
        mock_recognizer_class.return_value = mock_recognizer
        
        # Test UnknownValueError (no speech detected)
        mock_recognizer.recognize_google.side_effect = sr.UnknownValueError()
        
        with patch('pyaudio.PyAudio'):
            with patch.object(audio_handler, '_record_audio_chunk', return_value=b'\x00' * 1024):
                result = audio_handler.record_speech()
                assert result is None

        # Test RequestError (API error)
        mock_recognizer.recognize_google.side_effect = sr.RequestError("API Error")
        
        with patch('pyaudio.PyAudio'):
            with patch.object(audio_handler, '_record_audio_chunk', return_value=b'\x00' * 1024):
                result = audio_handler.record_speech()
                assert result is None


    @patch('pyaudio.PyAudio')
    def test_audio_device_initialization(self, mock_pyaudio, config):
        """Test audio device initialization"""
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        
        # Mock device enumeration
        mock_pa.get_device_count.return_value = 2
        mock_pa.get_device_info_by_index.side_effect = [
            {'name': 'Built-in Microphone', 'maxInputChannels': 1},
            {'name': 'Built-in Output', 'maxOutputChannels': 2}
        ]
        
        handler = AudioHandler(config)
        handler._initialize_pyaudio()
        
        assert handler.pyaudio == mock_pa
        mock_pa.get_device_count.assert_called_once()


    def test_audio_level_detection(self, audio_handler):
        """Test audio level detection for silence"""
        # Test with silent audio (all zeros)
        silent_audio = np.zeros(1024, dtype=np.int16).tobytes()
        is_silent = audio_handler._is_silence(silent_audio)
        assert is_silent is True
        
        # Test with loud audio
        loud_audio = np.full(1024, 1000, dtype=np.int16).tobytes()
        is_silent = audio_handler._is_silence(loud_audio)
        assert is_silent is False


class TestAudioErrorHandling:
    def test_pyaudio_initialization_error(self, config):
        """Test handling of PyAudio initialization errors"""
        with patch('pyaudio.PyAudio', side_effect=OSError("Audio system unavailable")):
            handler = AudioHandler(config)
            # Should not raise exception during initialization
            assert handler.pyaudio is None
            
            # Should handle error gracefully when trying to record
            with pytest.raises(RuntimeError):
                handler.record_speech()


    @patch('subprocess.run')
    def test_playback_error_handling(self, mock_subprocess, audio_handler):
        """Test playback error handling"""
        # Mock subprocess error
        mock_subprocess.side_effect = FileNotFoundError("afplay not found")
        
        # Should not raise exception, just log error
        audio_handler.play_audio_file("test.wav")
        mock_subprocess.assert_called_once()


    def test_invalid_audio_data(self, audio_handler):
        """Test handling of invalid audio data"""
        # Test with invalid bytes
        invalid_data = b"not audio data"
        
        # Should handle gracefully
        is_silent = audio_handler._is_silence(invalid_data)
        assert is_silent is True  # Should default to silent for invalid data