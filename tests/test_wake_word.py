import pytest
import asyncio
import tempfile
from unittest.mock import Mock, patch, AsyncMock
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


class TestWakeWordDetector:
    def test_initialization(self, config, mock_porcupine):
        """Test WakeWordDetector initialization"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            assert detector.config == config.wake_word
            assert detector.porcupine == mock_porcupine


    def test_initialization_no_api_key(self, config):
        """Test initialization without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="PICOVOICE_API_KEY environment variable not set"):
                WakeWordDetector(config)


    def test_initialization_no_model_file(self, config):
        """Test initialization with missing model file"""
        config.wake_word.model_path = "/nonexistent/model.ppn"
        
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
        mock_stream.read.return_value = b'\x00' * 1024  # Silent audio data
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Test detection
            result = detector.detect()
            
            assert result is True
            mock_porcupine.process.assert_called()


    @patch('pyaudio.PyAudio')
    def test_detect_no_wake_word(self, mock_pyaudio, config, mock_porcupine):
        """Test when no wake word is detected"""
        # Set up mocks
        mock_porcupine.process.return_value = -1  # No wake word
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Test detection
            result = detector.detect()
            
            assert result is False
            mock_porcupine.process.assert_called()


    @pytest.mark.asyncio
    @patch('pyaudio.PyAudio')
    async def test_detect_async(self, mock_pyaudio, config, mock_porcupine):
        """Test async wake word detection"""
        # Set up mocks
        mock_porcupine.process.return_value = 0  # Wake word detected
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Test async detection
            result = await detector.detect_async()
            
            assert result is True


    @patch('pyaudio.PyAudio')
    def test_detect_error_handling(self, mock_pyaudio, config, mock_porcupine):
        """Test error handling during detection"""
        # Set up mocks to raise exception
        mock_porcupine.process.side_effect = Exception("Porcupine error")
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Should handle error gracefully
            result = detector.detect()
            assert result is False


    @patch('pyaudio.PyAudio')
    def test_pyaudio_initialization_error(self, mock_pyaudio, config, mock_porcupine):
        """Test PyAudio initialization error handling"""
        # Mock PyAudio to raise exception
        mock_pyaudio.side_effect = OSError("Audio system unavailable")
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Should handle error gracefully
            result = detector.detect()
            assert result is False


    def test_cleanup(self, config, mock_porcupine):
        """Test cleanup of resources"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Test cleanup
            detector.cleanup()
            
            mock_porcupine.delete.assert_called_once()


    def test_context_manager(self, config, mock_porcupine):
        """Test context manager functionality"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with WakeWordDetector(config) as detector:
                assert detector.porcupine == mock_porcupine
            
            # Should cleanup on exit
            mock_porcupine.delete.assert_called_once()


    def test_model_path_auto_detection(self, config):
        """Test automatic model path detection"""
        config.wake_word.model_path = ""  # Empty to trigger auto-detection
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with patch('platform.system', return_value='Darwin'):  # macOS
                with patch('os.path.exists', return_value=True):
                    detector = WakeWordDetector(config)
                    # Should not raise error with auto-detection


    @patch('pyaudio.PyAudio')
    def test_audio_chunk_processing(self, mock_pyaudio, config, mock_porcupine):
        """Test audio chunk processing"""
        # Set up mocks
        audio_chunks = [
            b'\x00' * 1024,  # Silent chunk
            b'\xff' * 1024,  # Loud chunk
            b'\x00' * 1024,  # Silent chunk again
        ]
        
        mock_porcupine.process.side_effect = [-1, -1, 0]  # Wake word on third chunk
        
        mock_pa = Mock()
        mock_pyaudio.return_value = mock_pa
        mock_stream = Mock()
        mock_stream.read.side_effect = audio_chunks
        mock_pa.open.return_value = mock_stream
        
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            detector = WakeWordDetector(config)
            
            # Should detect wake word after processing chunks
            result = detector.detect()
            
            assert result is True
            assert mock_porcupine.process.call_count == 3


class TestWakeWordDetectorIntegration:
    def test_audio_stream_configuration(self, config):
        """Test audio stream is configured correctly"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with patch('pvporcupine.create') as mock_create:
                mock_porcupine = Mock()
                mock_porcupine.frame_length = 512
                mock_porcupine.sample_rate = 16000
                mock_create.return_value = mock_porcupine
                
                with patch('pyaudio.PyAudio') as mock_pyaudio:
                    mock_pa = Mock()
                    mock_pyaudio.return_value = mock_pa
                    
                    detector = WakeWordDetector(config)
                    detector.detect()
                    
                    # Verify stream configuration
                    mock_pa.open.assert_called_once()
                    call_args = mock_pa.open.call_args[1]
                    assert call_args['format'] == mock_pyaudio.return_value.paInt16
                    assert call_args['channels'] == 1
                    assert call_args['rate'] == 16000
                    assert call_args['input'] is True
                    assert call_args['frames_per_buffer'] == 512


    def test_detection_timeout(self, config):
        """Test detection with timeout"""
        with patch.dict('os.environ', {'PICOVOICE_API_KEY': 'test_key'}):
            with patch('pvporcupine.create') as mock_create:
                mock_porcupine = Mock()
                mock_porcupine.frame_length = 512
                mock_porcupine.process.return_value = -1  # Never detect
                mock_create.return_value = mock_porcupine
                
                with patch('pyaudio.PyAudio') as mock_pyaudio:
                    mock_pa = Mock()
                    mock_pyaudio.return_value = mock_pa
                    mock_stream = Mock()
                    mock_stream.read.return_value = b'\x00' * 1024
                    mock_pa.open.return_value = mock_stream
                    
                    detector = WakeWordDetector(config)
                    
                    # This should return False after checking many chunks
                    # In a real implementation, there would be a timeout mechanism
                    result = detector.detect()
                    
                    # For now, we just verify it doesn't hang indefinitely
                    assert result is False