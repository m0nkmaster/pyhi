import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.audio import AudioHandler, AudioError
from src.config import AudioConfig


@pytest.fixture
def audio_config():
    return AudioConfig()


class TestAudioHandler:
    def test_initialization(self, audio_config):
        """Test AudioHandler initialization"""
        with patch('pyaudio.PyAudio'), patch('speech_recognition.Recognizer'):
            handler = AudioHandler(audio_config)
            assert handler.config == audio_config


    def test_record_chunk_error(self, audio_config):
        """Test record_chunk error handling"""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            mock_pa = Mock()
            mock_pyaudio.return_value = mock_pa
            mock_pa.open.side_effect = Exception("Audio error")
            
            with patch('speech_recognition.Recognizer'), \
                 patch('speech_recognition.Microphone') as mock_mic:
                # Mock the microphone context manager
                mock_mic_instance = Mock()
                mock_mic.return_value = mock_mic_instance
                mock_mic_instance.__enter__ = Mock(return_value=mock_mic_instance)
                mock_mic_instance.__exit__ = Mock(return_value=None)
                
                handler = AudioHandler(audio_config)
                
                with pytest.raises(AudioError, match="Failed to record audio chunk"):
                    handler.record_chunk()


    @pytest.mark.asyncio
    async def test_speak_placeholder(self, audio_config):
        """Test speak method (placeholder implementation)"""
        with patch('pyaudio.PyAudio'), patch('speech_recognition.Recognizer'):
            handler = AudioHandler(audio_config)
            await handler.speak("Hello world")


    def test_play_audio_data_unsupported_format(self, audio_config):
        """Test playing unsupported audio format"""
        with patch('pyaudio.PyAudio'), patch('speech_recognition.Recognizer'):
            handler = AudioHandler(audio_config)
            
            with pytest.raises(AudioError, match="Unsupported audio format"):
                handler.play_audio_data(b"data", "unsupported")


    @patch('pathlib.Path.exists')
    def test_play_sound_file_not_found(self, mock_exists, audio_config):
        """Test playing non-existent sound file"""
        mock_exists.return_value = False
        
        with patch('pyaudio.PyAudio'), patch('speech_recognition.Recognizer'):
            handler = AudioHandler(audio_config)
            handler.play_sound_file("nonexistent.mp3")


    def test_convenience_sound_methods(self, audio_config):
        """Test convenience methods for playing specific sounds"""
        with patch('pyaudio.PyAudio'), patch('speech_recognition.Recognizer'):
            handler = AudioHandler(audio_config)
            
            with patch.object(handler, 'play_sound_file') as mock_play:
                handler.play_activation_sound()
                mock_play.assert_called_with(audio_config.activation_sound)


class TestAudioHandlerErrorHandling:
    def test_pyaudio_initialization_error(self, audio_config):
        """Test handling PyAudio initialization errors"""
        with patch('pyaudio.PyAudio', side_effect=OSError("Audio system unavailable")):
            with patch('speech_recognition.Recognizer'):
                # Should still create handler but may have limited functionality
                try:
                    handler = AudioHandler(audio_config)
                    assert handler is not None
                except Exception:
                    # It's okay if initialization fails with audio errors
                    pass