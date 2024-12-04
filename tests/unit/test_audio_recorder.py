import pytest
from unittest.mock import Mock, patch
import pyaudio
from src.audio.recorder import PyAudioRecorder
from src.utils.types import AudioConfig, AudioFrame

@pytest.fixture
def audio_config():
    return AudioConfig(
        sample_rate=44100,
        channels=1,
        chunk_size=1024,
        format=pyaudio.paInt16
    )

@pytest.fixture
def mock_analyzer():
    analyzer = Mock()
    analyzer.is_speech.return_value = True
    return analyzer

@pytest.fixture
def mock_stream():
    stream = Mock()
    stream.read.return_value = b'test_audio_data'
    return stream

@pytest.fixture
def mock_pyaudio(mock_stream):
    with patch('pyaudio.PyAudio') as mock_pa:
        mock_pa_instance = Mock()
        mock_pa_instance.open.return_value = mock_stream
        mock_pa.return_value = mock_pa_instance
        yield mock_pa

def test_recorder_initialization(audio_config, mock_analyzer, mock_pyaudio):
    recorder = PyAudioRecorder(audio_config, mock_analyzer)
    assert recorder.config == audio_config
    assert recorder.analyzer == mock_analyzer
    assert recorder.stream is None
    assert recorder.frames == []

def test_start_recording(audio_config, mock_analyzer, mock_pyaudio):
    recorder = PyAudioRecorder(audio_config, mock_analyzer)
    recorder.start_recording()
    
    # Verify PyAudio.open was called with correct parameters
    mock_pyaudio.return_value.open.assert_called_once_with(
        format=audio_config.format,
        channels=audio_config.channels,
        rate=audio_config.sample_rate,
        input=True,
        frames_per_buffer=audio_config.chunk_size
    )

def test_stop_recording(audio_config, mock_analyzer, mock_pyaudio, mock_stream):
    recorder = PyAudioRecorder(audio_config, mock_analyzer)
    recorder.start_recording()
    recorder.frames = [b'frame1', b'frame2']
    
    result = recorder.stop_recording()
    
    assert result == b'frame1frame2'
    assert recorder.frames == []
    mock_stream.stop_stream.assert_called_once()
    mock_stream.close.assert_called_once()

def test_read_frame(audio_config, mock_analyzer, mock_pyaudio, mock_stream):
    recorder = PyAudioRecorder(audio_config, mock_analyzer)
    recorder.start_recording()
    
    frame = recorder.read_frame()
    
    assert isinstance(frame, AudioFrame)
    assert frame.data == b'test_audio_data'
    assert frame.is_speech is True
    mock_stream.read.assert_called_once_with(audio_config.chunk_size, exception_on_overflow=False)
    mock_analyzer.is_speech.assert_called_once()

def test_read_frame_without_starting(audio_config, mock_analyzer, mock_pyaudio):
    recorder = PyAudioRecorder(audio_config, mock_analyzer)
    
    with pytest.raises(RuntimeError, match="Recording not started"):
        recorder.read_frame()

def test_error_callback(audio_config, mock_analyzer, mock_pyaudio):
    error_callback = Mock()
    recorder = PyAudioRecorder(audio_config, mock_analyzer, error_callback)
    
    # Simulate an error in PyAudio.open
    mock_pyaudio.return_value.open.side_effect = Exception("Test error")
    
    with pytest.raises(Exception):
        recorder.start_recording()
    
    error_callback.assert_called_once() 