import pytest
from unittest.mock import Mock, patch, MagicMock, call
import pyaudio
from itertools import cycle, chain, repeat
from src.audio.recorder import (
    PyAudioRecorder,
    AudioRecorderError,
    DeviceNotFoundError,
    AudioConfig,
    AudioRecorderConfig
)
from src.config import AudioConfig, AudioRecorderConfig

@pytest.fixture
def mock_analyzer():
    analyzer = Mock()
    analyzer.is_speech = Mock(return_value=False)
    return analyzer

@pytest.fixture
def mock_device_config():
    return Mock(
        debug_audio=False,
        list_devices_on_start=False,
        excluded_device_names=[],
        preferred_input_device_name=None,
        fallback_to_default=True
    )

@pytest.fixture
def mock_audio_config(mock_device_config):
    return AudioConfig(
        sample_rate=44100,
        channels=1,
        chunk_size=1024,
        format=pyaudio.paInt16,
        input_device_index=0,
        device_config=mock_device_config
    )

@pytest.fixture
def mock_recorder_config():
    return AudioRecorderConfig(
        wake_word_silence_threshold=0.7,
        response_silence_threshold=0.02,  # Just slightly less than one chunk duration
        buffer_duration=0.0
    )

@pytest.fixture
def mock_stream():
    stream = MagicMock()
    stream.read = MagicMock()
    stream.stop_stream = MagicMock()
    stream.close = MagicMock()
    return stream

@pytest.fixture
def mock_pyaudio(mock_stream):
    with patch('pyaudio.PyAudio') as mock:
        # Mock device info
        device_info = MagicMock()
        device_info.__getitem__.side_effect = {
            'index': 0,
            'name': 'Test Device',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'is_builtin': False
        }.__getitem__
        
        mock.return_value.get_device_info_by_index.return_value = device_info
        mock.return_value.get_device_count.return_value = 1
        
        # Set up the mock stream
        mock.return_value.open.return_value = mock_stream
        mock.return_value.terminate = MagicMock()
        
        yield mock

def test_init_with_valid_device(mock_pyaudio, mock_analyzer, mock_audio_config, mock_recorder_config):
    # Mock device info to have 2 channels
    device_info = MagicMock()
    device_info.__getitem__.side_effect = {
        'index': 0,
        'name': 'Test Device',
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'is_builtin': False
    }.__getitem__
    mock_pyaudio.return_value.get_device_info_by_index.return_value = device_info
    
    recorder = PyAudioRecorder(
        config=mock_audio_config,
        analyzer=mock_analyzer,
        recorder_config=mock_recorder_config
    )
    
    assert recorder.config.channels == 2
    assert recorder.config.sample_rate == 44100
    assert recorder.wake_word_silence_threshold == mock_recorder_config.wake_word_silence_threshold
    assert recorder.response_silence_threshold == mock_recorder_config.response_silence_threshold

def test_init_with_no_input_channels(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Mock device with no input channels
    device_info = MagicMock()
    device_info.__getitem__.side_effect = {
        'index': 0,
        'name': 'Invalid Device',
        'maxInputChannels': 0,
        'defaultSampleRate': 44100,
        'is_builtin': False
    }.__getitem__
    mock_pyaudio.return_value.get_device_info_by_index.return_value = device_info
    
    with pytest.raises(ValueError, match="has no input channels"):
        PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)

def test_init_error_callback(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Test error callback
    error_callback = Mock()
    mock_error = Exception("Device error")
    
    # Mock get_device_info_by_index to raise an error
    mock_pyaudio.return_value.get_device_info_by_index.side_effect = mock_error
    
    # Should raise the original error
    with pytest.raises(Exception) as exc_info:
        PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer, on_error=error_callback)
    
    assert exc_info.value == mock_error
    error_callback.assert_called_once_with(mock_error)

def test_init_with_no_device_index(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Test device index fallback
    mock_audio_config.input_device_index = None
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    assert recorder.config.input_device_index == 0

def test_cleanup_error_handling(mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    # Test cleanup with errors
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Make stream operations raise errors
    mock_stream.stop_stream.side_effect = Exception("Stop error")
    mock_stream.close.side_effect = Exception("Close error")
    mock_pyaudio.return_value.terminate.side_effect = Exception("Terminate error")
    
    # Should not raise any exceptions
    recorder.__del__()

def test_start_recording(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Mock device info
    device_info = MagicMock()
    device_info.__getitem__.side_effect = {
        'index': 0,
        'name': 'Test Device',
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'is_builtin': False
    }.__getitem__
    mock_pyaudio.return_value.get_device_info_by_index.return_value = device_info
    
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    mock_pyaudio.return_value.open.assert_called_once_with(
        format=mock_audio_config.format,
        channels=2,  # Should use device's channels
        rate=44100,
        input=True,
        input_device_index=mock_audio_config.input_device_index,
        frames_per_buffer=mock_audio_config.chunk_size
    )
    assert recorder.is_recording is True

def test_start_recording_error(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Mock stream opening to raise an error
    mock_pyaudio.return_value.open.side_effect = Exception("Failed to open stream")
    
    error_callback = Mock()
    recorder = PyAudioRecorder(
        config=mock_audio_config,
        analyzer=mock_analyzer,
        on_error=error_callback
    )
    
    with pytest.raises(Exception, match="Failed to open stream"):
        recorder.start_recording()
    
    error_callback.assert_called_once()

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_no_speech(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Create a counter to control how many chunks to return
    chunk_counter = 0
    stream_active = True
    def read_side_effect(*args, **kwargs):
        nonlocal chunk_counter, stream_active
        if not stream_active:  # Stop returning data after stream is stopped
            return b''
        chunk_counter += 1
        if chunk_counter <= 3:  # Return 3 chunks before "stopping"
            return f'chunk{chunk_counter}'.encode()
        return b''  # Return empty data after 3 chunks
    
    # Mock the stream's methods
    def stop_stream():
        nonlocal stream_active
        stream_active = False
    
    mock_stream.read.side_effect = read_side_effect
    mock_stream.stop_stream.side_effect = stop_stream
    mock_stream._is_input_stream = True  # Add this property
    
    # Create a list to track speech detection results
    speech_results = [False, True, True, False]  # Only chunks 2 and 3 contain speech
    speech_counter = 0
    def is_speech_side_effect(data, config):
        nonlocal speech_counter
        if not stream_active:  # Don't process speech after stream is stopped
            return False
        result = speech_results[speech_counter] if speech_counter < len(speech_results) else False
        speech_counter += 1
        return result
    
    mock_analyzer.is_speech.side_effect = is_speech_side_effect
    
    audio_data = recorder.stop_recording()
    assert isinstance(audio_data, bytes)
    # chunk1 should be included as it's in the pre-speech buffer when speech is detected in chunk2
    assert b'chunk1' in audio_data  # Pre-speech buffer
    assert b'chunk2' in audio_data  # First chunk with speech
    assert b'chunk3' in audio_data  # Second chunk with speech
    # Verify that we immediately stop after speech ends and don't include any more chunks
    assert audio_data.endswith(b'chunk3')  # Should end with the last speech chunk
    assert b'chunk4' not in audio_data  # Should not include any chunks after speech ends

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_with_speech(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Create a counter to control speech detection sequence
    chunk_counter = 0
    def read_side_effect(*args, **kwargs):
        nonlocal chunk_counter
        chunk_counter += 1
        if chunk_counter <= 4:  # Return 4 chunks before "stopping"
            return f'chunk{chunk_counter}'.encode()
        return b''
    
    mock_stream.read.side_effect = read_side_effect
    
    # Create a sequence that matches our chunks
    speech_values = [True, True, False, False]  # One value per chunk
    def speech_side_effect(*args, **kwargs):
        nonlocal chunk_counter
        if chunk_counter <= len(speech_values):
            return speech_values[chunk_counter - 1]
        return False
    
    mock_analyzer.is_speech.side_effect = speech_side_effect
    
    audio_data = recorder.stop_recording()
    assert isinstance(audio_data, bytes)
    assert b'chunk1' in audio_data
    assert b'chunk2' in audio_data

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_wake_word_mode(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Create a counter to control speech detection sequence
    chunk_counter = 0
    def read_side_effect(*args, **kwargs):
        nonlocal chunk_counter
        chunk_counter += 1
        if chunk_counter <= 4:  # Return 4 chunks before "stopping"
            return f'chunk{chunk_counter}'.encode()
        return b''
    
    mock_stream.read.side_effect = read_side_effect
    
    # Create a sequence that matches our chunks
    speech_values = [True, True, False, False]  # One value per chunk
    def speech_side_effect(*args, **kwargs):
        nonlocal chunk_counter
        if chunk_counter <= len(speech_values):
            return speech_values[chunk_counter - 1]
        return False
    
    mock_analyzer.is_speech.side_effect = speech_side_effect
    
    audio_data = recorder.stop_recording(is_wake_word_mode=True)
    assert isinstance(audio_data, bytes)
    assert b'chunk1' in audio_data
    assert b'chunk2' in audio_data
    
    # Verify the audio buffer was used
    assert len(recorder.audio_buffer) <= recorder.buffer_size

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_error_handling(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    error_callback = Mock()
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer, on_error=error_callback)
    recorder.start_recording()
    
    # Make stream operations raise errors
    mock_stream.read.side_effect = Exception("Read error")
    
    with pytest.raises(Exception, match="Read error"):
        recorder.stop_recording()
    
    error_callback.assert_called_once()

def test_stop_recording_without_start(mock_pyaudio, mock_analyzer, mock_audio_config):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    audio_data = recorder.stop_recording()
    assert audio_data == b''

def test_cleanup_on_deletion(mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Trigger cleanup
    recorder.__del__()
    
    # Verify cleanup was called
    mock_stream.stop_stream.assert_called_once()
    mock_stream.close.assert_called_once()
    mock_pyaudio.return_value.terminate.assert_called_once()

def test_init_with_no_input_devices(mock_pyaudio, mock_analyzer, mock_audio_config):
    # Mock device with no input channels for all devices
    device_info = MagicMock()
    device_info.__getitem__.side_effect = {
        'index': 0,
        'name': 'Output Only Device',
        'maxInputChannels': 0,
        'defaultSampleRate': 44100,
        'is_builtin': False
    }.__getitem__
    
    # Mock get_device_count to return 1 device
    mock_pyaudio.return_value.get_device_count.return_value = 1
    mock_pyaudio.return_value.get_device_info_by_index.return_value = device_info
    
    # Set input_device_index to None to force device search
    mock_audio_config.input_device_index = None
    
    # Should raise DeviceNotFoundError since there are no input devices
    with pytest.raises(DeviceNotFoundError, match="No input devices found"):
        PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_io_error(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    recorder.start_recording()
    
    # Create a counter to control the sequence
    chunk_counter = 0
    def read_side_effect(*args, **kwargs):
        nonlocal chunk_counter
        chunk_counter += 1
        if chunk_counter == 1:
            raise IOError("Stream read error")  # This should be caught and continue
        if chunk_counter <= 3:
            return f'chunk{chunk_counter}'.encode()
        return b''
    
    mock_stream.read.side_effect = read_side_effect
    # Simulate speech detection for chunks 2 and 3
    def is_speech_side_effect(data, config):
        chunk_num = int(data.decode().replace('chunk', ''))
        return chunk_num in [2, 3]
    
    mock_analyzer.is_speech.side_effect = is_speech_side_effect
    
    audio_data = recorder.stop_recording()
    assert isinstance(audio_data, bytes)
    assert b'chunk2' in audio_data  # First chunk with speech
    assert b'chunk3' in audio_data  # Second chunk with speech

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_stop_recording_error_with_callback(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    error_callback = Mock()
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer, on_error=error_callback)
    recorder.start_recording()
    
    # Simulate an error during recording
    mock_stream.read.side_effect = Exception("Recording error")
    
    with pytest.raises(Exception, match="Recording error"):
        recorder.stop_recording()
    
    error_callback.assert_called_once()

def test_stop_recording_stream_close_error(mock_pyaudio, mock_analyzer, mock_audio_config, mock_stream):
    # Set up mock error callback
    error_callback = Mock()
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer, on_error=error_callback)
    recorder.stream = mock_stream
    
    # Mock stream.read to return some bytes data
    mock_stream.read.return_value = b'\x00' * 1024
    
    # Mock stream.close to raise an error
    mock_stream.close.side_effect = Exception("Stream close error")
    
    # Mock analyzer to detect speech and then silence to trigger stop
    # First call returns True, all subsequent calls return False
    mock_analyzer.is_speech.side_effect = chain([True], repeat(False))
    
    # Stop recording should still complete despite the error
    audio_data = recorder.stop_recording()
    
    # Error callback should have been called
    error_callback.assert_called_once()
    assert "Stream close error" in str(error_callback.call_args[0][0])
    
    # Audio data should still be returned
    assert isinstance(audio_data, bytes)
    assert len(audio_data) > 0

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_list_audio_devices_with_debug(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config):
    # Create a proper device config
    class DeviceConfig:
        def __init__(self):
            self.debug_audio = True
            self.preferred_input_device_name = None
            self.excluded_device_names = []
            self.fallback_to_default = True
            self.list_devices_on_start = False
    mock_audio_config.device_config = DeviceConfig()
    
    # Mock device info that should be skipped (virtual device)
    virtual_device = {
        'name': 'BlackHole 16ch',
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 0,
        'defaultLowInputLatency': 0.1,
        'defaultHighInputLatency': 0.2
    }
    
    # Mock device info for a regular device that should be included
    regular_device = {
        'name': 'Built-in Microphone (Core Audio)',
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 1,
        'defaultLowInputLatency': 0.1,
        'defaultHighInputLatency': 0.2
    }
    
    def get_device_info_side_effect(index):
        if index == 0:
            return virtual_device
        elif index == 1:
            return regular_device
        raise Exception("Test error getting device info")
    
    # Override the default mock behavior
    mock_pyaudio.return_value.get_device_count.return_value = 2
    mock_pyaudio.return_value.get_device_info_by_index.side_effect = get_device_info_side_effect
    mock_pyaudio.return_value.get_default_input_device_info.return_value = regular_device
    
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    devices = recorder._list_audio_devices()
    
    # Verify that only the regular device is in the list and virtual device is skipped
    assert len(devices) == 1
    device = devices[0]
    assert device['name'] == regular_device['name']
    assert device['channels'] == regular_device['maxInputChannels']
    assert device['sample_rate'] == regular_device['defaultSampleRate']
    assert device['latency'] == regular_device['defaultLowInputLatency']
    assert device['is_builtin'] == True  # Should be True because name contains 'built-in'
    assert device['is_default'] == True  # Should be True because it matches default device
    assert device['index'] == regular_device['index']

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_find_device_with_preferred_name(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config):
    # Create a new device config with preferred device name
    class DeviceConfig:
        def __init__(self):
            self.preferred_input_device_name = "Built-in"
            self.debug_audio = False
            self.excluded_device_names = []
            self.fallback_to_default = True
            self.list_devices_on_start = False
    mock_audio_config.device_config = DeviceConfig()
    
    # Create test devices with all required fields
    devices = [
        {
            'index': 0,
            'name': 'Built-in Microphone (Core Audio)',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'defaultLowInputLatency': 0.1,
            'defaultHighInputLatency': 0.2,
            'channels': 2,
            'sample_rate': 44100,
            'latency': 0.1,
            'is_builtin': True,
            'is_default': False
        },
        {
            'index': 1,
            'name': 'Built-in Input (Core Audio)',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'defaultLowInputLatency': 0.05,
            'defaultHighInputLatency': 0.2,
            'channels': 2,
            'sample_rate': 44100,
            'latency': 0.05,
            'is_builtin': True,
            'is_default': True
        },
        {
            'index': 2,
            'name': 'External Mic',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'defaultLowInputLatency': 0.01,
            'defaultHighInputLatency': 0.2,
            'channels': 2,
            'sample_rate': 44100,
            'latency': 0.01,
            'is_builtin': False,
            'is_default': False
        }
    ]
    
    def get_device_info_side_effect(index):
        return next((d for d in devices if d['index'] == index), None)
    
    mock_pyaudio.get_device_count.return_value = len(devices)
    mock_pyaudio.get_device_info_by_index.side_effect = get_device_info_side_effect
    mock_pyaudio.get_default_input_device_info.return_value = next(d for d in devices if d['is_default'])
    
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    selected_device = recorder._find_compatible_device(devices)
    
    # Should select the Built-in Input due to matching name and lower latency
    assert selected_device['index'] == 1
    assert selected_device['name'] == 'Built-in Input (Core Audio)'
    assert selected_device['is_builtin'] == True
    assert selected_device['is_default'] == True
    assert selected_device['latency'] == 0.05

@patch('time.sleep', return_value=None)  # Prevent actual sleeping
def test_find_device_preferred_not_found(mock_sleep, mock_pyaudio, mock_analyzer, mock_audio_config):
    # Create a new device config with non-existent preferred device name
    class DeviceConfig:
        def __init__(self):
            self.preferred_input_device_name = "NonExistent"
            self.debug_audio = False
            self.excluded_device_names = []
            self.fallback_to_default = True
            self.list_devices_on_start = False
    mock_audio_config.device_config = DeviceConfig()
    
    # Create test devices with all required fields
    devices = [
        {
            'index': 0,
            'name': 'Built-in Microphone (Core Audio)',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'defaultLowInputLatency': 0.1,
            'defaultHighInputLatency': 0.2,
            'channels': 2,
            'sample_rate': 44100,
            'latency': 0.1,
            'is_builtin': True,
            'is_default': True
        },
        {
            'index': 1,
            'name': 'External Mic',
            'maxInputChannels': 2,
            'defaultSampleRate': 44100,
            'defaultLowInputLatency': 0.01,
            'defaultHighInputLatency': 0.2,
            'channels': 2,
            'sample_rate': 44100,
            'latency': 0.01,
            'is_builtin': False,
            'is_default': False
        }
    ]
    
    def get_device_info_side_effect(index):
        return next((d for d in devices if d['index'] == index), None)
    
    mock_pyaudio.get_device_count.return_value = len(devices)
    mock_pyaudio.get_device_info_by_index.side_effect = get_device_info_side_effect
    mock_pyaudio.get_default_input_device_info.return_value = next(d for d in devices if d['is_default'])
    
    recorder = PyAudioRecorder(config=mock_audio_config, analyzer=mock_analyzer)
    selected_device = recorder._find_compatible_device(devices)
    
    # Should fall back to built-in device since it's also the default
    assert selected_device['index'] == 0
    assert selected_device['name'] == 'Built-in Microphone (Core Audio)'
    assert selected_device['is_builtin'] == True
    assert selected_device['is_default'] == True
    assert selected_device['latency'] == 0.1
