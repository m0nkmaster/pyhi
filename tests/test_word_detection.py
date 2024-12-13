import pytest
from unittest.mock import Mock, patch
import numpy as np
import os
import tempfile
from src.word_detection.detector import PorcupineWakeWordDetector
from src.config import WordDetectionConfig, AudioConfig

@pytest.fixture
def mock_porcupine():
    with patch('pvporcupine.create') as mock:
        mock_instance = Mock()
        mock_instance.frame_length = 512
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def word_detection_config(tmp_path):
    config = WordDetectionConfig()
    # Create a temporary file to use as model
    model_file = tmp_path / "test_model.ppn"
    model_file.write_bytes(b"dummy model data")
    config.model_path = str(model_file)
    return config

@pytest.fixture
def audio_config():
    return AudioConfig()

class TestPorcupineWakeWordDetector:
    def test_initialization_success(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment variable and os.path.exists
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        
        detector = PorcupineWakeWordDetector(word_detection_config)
        assert detector.config == word_detection_config
        assert detector.porcupine == mock_porcupine

    def test_initialization_no_api_key(self, mock_porcupine, word_detection_config, monkeypatch):
        # Ensure environment variable is not set
        monkeypatch.delenv("PICOVOICE_API_KEY", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            PorcupineWakeWordDetector(word_detection_config)
        assert str(exc_info.value) == "PICOVOICE_API_KEY environment variable not set"

    def test_initialization_no_model_file(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment variable but make model file not exist
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        word_detection_config.model_path = "/nonexistent/path/model.ppn"
        
        with pytest.raises(RuntimeError) as exc_info:
            PorcupineWakeWordDetector(word_detection_config)
        assert "Failed to initialize Porcupine: Model file not found at /nonexistent/path/model.ppn" in str(exc_info.value)

    def test_detect_wake_word_found(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment and file existence
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        
        # Set up mock to indicate wake word found
        mock_porcupine.process.return_value = 0
        mock_porcupine.frame_length = 512
        
        detector = PorcupineWakeWordDetector(word_detection_config)
        
        # Create test audio data
        audio_data = np.zeros(512, dtype=np.int16).tobytes()
        
        result = detector.detect(audio_data)
        assert result is True
        mock_porcupine.process.assert_called_once()

    def test_detect_no_wake_word(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment and file existence
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        
        # Set up mock to indicate no wake word found
        mock_porcupine.process.return_value = -1
        mock_porcupine.frame_length = 512
        
        detector = PorcupineWakeWordDetector(word_detection_config)
        
        # Create test audio data
        audio_data = np.zeros(512, dtype=np.int16).tobytes()
        
        result = detector.detect(audio_data)
        assert result is False
        mock_porcupine.process.assert_called_once()

    def test_detect_error_handling(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment and file existence
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        
        # Set up mock to raise an exception
        mock_porcupine.process.side_effect = Exception("Test error")
        mock_porcupine.frame_length = 512
        
        detector = PorcupineWakeWordDetector(word_detection_config)
        
        # Create test audio data
        audio_data = np.zeros(512, dtype=np.int16).tobytes()
        
        result = detector.detect(audio_data)
        assert result is False  # Should return False on error
        mock_porcupine.process.assert_called_once()

    def test_cleanup(self, mock_porcupine, word_detection_config, monkeypatch):
        # Mock environment and file existence
        monkeypatch.setenv("PICOVOICE_API_KEY", "test_key")
        
        detector = PorcupineWakeWordDetector(word_detection_config)
        
        # Call __del__ explicitly to test cleanup
        detector.__del__()
        
        mock_porcupine.delete.assert_called_once()
