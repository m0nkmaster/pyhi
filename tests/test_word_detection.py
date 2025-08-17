import pytest
import asyncio
from unittest.mock import Mock, patch
from src.wake_word import WakeWordDetector
from src.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def mock_porcupine():
    """Mock Porcupine instance"""
    with patch('pvporcupine.create') as mock_create:
        mock_instance = Mock()
        mock_instance.frame_length = 512
        mock_instance.process.return_value = -1  # No wake word by default
        mock_instance.delete = Mock()
        mock_create.return_value = mock_instance
        yield mock_instance


class TestWakeWordDetectorCompat:
    """Compatibility tests for wake word detection - mirrors original test structure"""
    
    def test_initialization_success(self, config, mock_porcupine):
        """Test successful initialization"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            assert detector.config == config
            assert detector.porcupine == mock_porcupine


    def test_initialization_no_api_key(self, config):
        """Test initialization failure without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="PICOVOICE_API_KEY environment variable not set"):
                WakeWordDetector(config)


    def test_initialization_no_model_file(self, config):
        """Test initialization failure with missing model file"""
        config.wake_word.model_path = "/nonexistent/path/model.ppn"
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with pytest.raises(RuntimeError, match="Failed to initialize Porcupine"):
                WakeWordDetector(config)


    @patch('pyaudio.PyAudio')
    def test_detect_wake_word_found(self, mock_pyaudio, config, mock_porcupine):
        """Test wake word detection when word is found"""
        # Set up mocks
        mock_porcupine.process.return_value = 0  # Wake word detected
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            result = detector.detect()
            
            assert result is True
            mock_porcupine.process.assert_called()


    @patch('pyaudio.PyAudio')
    def test_detect_no_wake_word(self, mock_pyaudio, config, mock_porcupine):
        """Test when no wake word is detected"""
        mock_porcupine.process.return_value = -1  # No wake word
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            result = detector.detect()
            
            assert result is False


    @patch('pyaudio.PyAudio')
    def test_detect_error_handling(self, mock_pyaudio, config, mock_porcupine):
        """Test error handling during detection"""
        mock_porcupine.process.side_effect = Exception("Test error")
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            result = detector.detect()
            
            assert result is False  # Should return False on error


    def test_cleanup(self, config, mock_porcupine):
        """Test cleanup functionality"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            detector.cleanup()
            
            mock_porcupine.delete.assert_called_once()