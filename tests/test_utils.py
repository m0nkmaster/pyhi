import pytest
from unittest.mock import Mock, patch
import pyaudio
from src.utils.audio_setup import find_input_device, setup_audio_stream
from src.config import AudioConfig

@pytest.fixture
def mock_pyaudio():
    with patch('pyaudio.PyAudio') as mock:
        yield mock

@pytest.fixture
def audio_config():
    return AudioConfig()

def create_mock_device_info(name, channels, is_default=False):
    return {
        'name': name,
        'maxInputChannels': channels,
        'defaultSampleRate': 44100,
        'index': 0
    }

class TestAudioSetup:
    def test_find_input_device_macbook_pro(self, mock_pyaudio):
        mock_instance = mock_pyaudio.return_value
        mock_instance.get_device_count.return_value = 2
        
        # Mock device info for MacBook Pro Microphone
        macbook_device = create_mock_device_info('MacBook Pro Microphone', 1)
        mock_instance.get_device_info_by_index.return_value = macbook_device
        
        device_index = find_input_device()
        assert device_index == 0
        mock_instance.terminate.assert_called_once()

    def test_find_input_device_builtin(self, mock_pyaudio):
        mock_instance = mock_pyaudio.return_value
        mock_instance.get_device_count.return_value = 2
        
        # First device is virtual, second is built-in
        devices = [
            create_mock_device_info('Blackhole Audio', 1),
            create_mock_device_info('Built-in Microphone', 1)
        ]
        mock_instance.get_device_info_by_index.side_effect = lambda x: devices[x]
        
        device_index = find_input_device()
        assert device_index == 1
        mock_instance.terminate.assert_called_once()

    def test_find_input_device_default(self, mock_pyaudio):
        mock_instance = mock_pyaudio.return_value
        mock_instance.get_device_count.return_value = 1
        
        # No MacBook Pro or built-in mic, use default
        default_device = create_mock_device_info('Default Microphone', 1, True)
        mock_instance.get_default_input_device_info.return_value = default_device
        mock_instance.get_device_info_by_index.return_value = default_device
        
        device_index = find_input_device()
        assert device_index == 0
        mock_instance.terminate.assert_called_once()

    def test_find_input_device_no_devices(self, mock_pyaudio):
        mock_instance = mock_pyaudio.return_value
        mock_instance.get_device_count.return_value = 0
        mock_instance.get_default_input_device_info.side_effect = IOError()
        
        device_index = find_input_device()
        assert device_index is None
        mock_instance.terminate.assert_called_once()

    def test_setup_audio_stream_success(self, mock_pyaudio, audio_config):
        mock_instance = mock_pyaudio.return_value
        mock_stream = Mock()
        mock_instance.open.return_value = mock_stream
        
        # Mock device info
        device_info = create_mock_device_info('MacBook Pro Microphone', 1)
        mock_instance.get_device_info_by_index.return_value = device_info
        mock_instance.get_device_count.return_value = 1
        
        audio_config.input_device_index = 0
        p, stream = setup_audio_stream(audio_config)
        
        assert p == mock_instance
        assert stream == mock_stream
        mock_instance.open.assert_called_once()

    def test_setup_audio_stream_error(self, mock_pyaudio, audio_config):
        mock_instance = mock_pyaudio.return_value
        mock_instance.open.side_effect = Exception("Stream error")
        
        # Mock device info
        device_info = create_mock_device_info('MacBook Pro Microphone', 1)
        mock_instance.get_device_info_by_index.return_value = device_info
        mock_instance.get_device_count.return_value = 1
        
        audio_config.input_device_index = 0
        
        with pytest.raises(Exception) as exc_info:
            setup_audio_stream(audio_config)
        
        assert str(exc_info.value) == "Stream error"
        mock_instance.terminate.assert_called_once()
