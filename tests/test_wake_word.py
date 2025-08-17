import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.wake_word import WakeWordDetector, WakeWordError
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


class TestWakeWordDetector:
    def test_initialization_success(self, config, mock_porcupine, mock_env_vars):
        """Test successful WakeWordDetector initialization"""
        with patch('os.path.exists', return_value=True):
            detector = WakeWordDetector(config)
            assert detector.config == config.wake_word
            assert detector.porcupine == mock_porcupine


    def test_initialization_no_api_key(self, config):
        """Test initialization without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(WakeWordError, match="PICOVOICE_API_KEY environment variable not set"):
                WakeWordDetector(config)


    def test_initialization_no_model_file(self, config):
        """Test initialization with missing model file"""
        config.wake_word.model_path = "/nonexistent/model.ppn"
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with patch('os.path.exists', return_value=False):
                with pytest.raises(WakeWordError, match="Wake word model not found"):
                    WakeWordDetector(config)


    def test_detect_wake_word_found(self, config, mock_porcupine, mock_env_vars):
        """Test wake word detection when word is found"""
        mock_porcupine.process.return_value = 0  # Wake word detected
        
        with patch('os.path.exists', return_value=True):
            detector = WakeWordDetector(config)
            
            audio_data = np.zeros(1024, dtype=np.int16).tobytes()
            result = detector.detect(audio_data)
            
            assert result is True
            mock_porcupine.process.assert_called()


    def test_detect_no_wake_word(self, config, mock_porcupine, mock_env_vars):
        """Test when no wake word is detected"""
        mock_porcupine.process.return_value = -1  # No wake word
        
        with patch('os.path.exists', return_value=True):
            detector = WakeWordDetector(config)
            
            audio_data = np.zeros(1024, dtype=np.int16).tobytes()
            result = detector.detect(audio_data)
            
            assert result is False
            mock_porcupine.process.assert_called()


    def test_detect_error_handling(self, config, mock_porcupine, mock_env_vars):
        """Test error handling during detection"""
        mock_porcupine.process.side_effect = Exception("Processing error")
        
        with patch('os.path.exists', return_value=True):
            detector = WakeWordDetector(config)
            
            audio_data = np.zeros(1024, dtype=np.int16).tobytes()
            result = detector.detect(audio_data)
            
            assert result is False  # Should return False on error


    def test_cleanup(self, config, mock_porcupine, mock_env_vars):
        """Test cleanup of Porcupine resources"""
        with patch('os.path.exists', return_value=True):
            detector = WakeWordDetector(config)
            
            del detector
            
            mock_porcupine.delete.assert_called_once()


    def test_model_path_auto_detection_mac(self, config, mock_env_vars):
        """Test automatic model path detection on macOS"""
        # Test that auto-detection sets a path
        with patch('platform.system', return_value='Darwin'):
            with patch('os.path.exists', return_value=True):
                with patch('pvporcupine.create') as mock_create:
                    mock_create.return_value = Mock()
                    
                    # The config should auto-detect during __post_init__
                    assert "mac" in config.wake_word.model_path.lower()


def test_create_wake_word_detector_convenience_function():
    """Test the convenience function for creating WakeWordDetector"""
    from src.wake_word import create_wake_word_detector
    
    with patch('src.config.Config.load') as mock_load:
        mock_config = Mock()
        mock_config.wake_word = Mock()
        mock_load.return_value = mock_config
        
        with patch('src.wake_word.WakeWordDetector') as mock_detector_class:
            mock_detector = Mock()
            mock_detector_class.return_value = mock_detector
            
            result = create_wake_word_detector("test_config.yaml")
            
            assert result == mock_detector
            mock_load.assert_called_once_with("test_config.yaml")
            mock_detector_class.assert_called_once_with(mock_config.wake_word)