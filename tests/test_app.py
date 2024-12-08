import os
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

from src.app import VoiceAssistant, main
from src.audio.player import AudioPlayerError
from src.config import (
    AppConfig,
    AudioConfig,
    AudioPlayerConfig,
    ChatConfig,
    TTSConfig,
    WordDetectionConfig,
    AudioRecorderConfig
)

@pytest.fixture
def mock_openai():
    with patch('openai.OpenAI') as mock:
        yield mock

@pytest.fixture
def mock_audio_player():
    with patch('src.app.SystemAudioPlayer') as mock:
        yield mock

@pytest.fixture
def mock_audio_recorder():
    with patch('src.app.PyAudioRecorder') as mock:
        yield mock

@pytest.fixture
def mock_word_detector():
    with patch('src.app.WhisperWordDetector') as mock:
        yield mock

@pytest.fixture
def mock_conversation_manager():
    with patch('src.app.ChatConversationManager') as mock:
        yield mock

@pytest.fixture
def mock_openai_wrapper():
    with patch('src.app.OpenAIWrapper') as mock:
        yield mock

@pytest.fixture
def mock_sleep():
    """Mock time.sleep to speed up tests."""
    with patch('time.sleep') as mock:
        yield mock

@pytest.fixture
def mock_is_speech():
    with patch('src.app.is_speech') as mock:
        yield mock

@pytest.fixture
def assistant(
    mock_openai,
    mock_audio_player,
    mock_audio_recorder,
    mock_word_detector,
    mock_conversation_manager,
    mock_openai_wrapper
):
    with patch('builtins.open', mock_open(read_data=b'test_sound')):
        assistant = VoiceAssistant(words=['hey', 'hi'], timeout_seconds=5.0)
    return assistant

@pytest.fixture
def mock_cleanup_assistant(assistant):
    """Assistant with mocked cleanup for conversation flow testing."""
    assistant._cleanup = Mock()
    return assistant

def test_init_with_default_config(mock_openai):
    """Test initialization with default configuration."""
    with patch('builtins.open', mock_open()):
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device info
            mock_device = {
                'maxInputChannels': 2,
                'maxOutputChannels': 2,
                'defaultSampleRate': 44100,
                'name': 'Test Device'
            }
            mock_pyaudio.return_value.get_device_count.return_value = 1
            mock_pyaudio.return_value.get_device_info_by_index.return_value = mock_device
            
            assistant = VoiceAssistant(words=['hey'])
            
            assert assistant.app_config.words == ['hey']
            assert assistant.app_config.timeout_seconds == AppConfig().timeout_seconds
            assert assistant.app_config.temp_recording_path == 'recording.wav'
            assert assistant.app_config.temp_response_path == 'response.mp3'
            assert isinstance(assistant.audio_config, AudioConfig)
            assert isinstance(assistant.audio_player_config, AudioPlayerConfig)

def test_init_with_custom_config(mock_openai):
    """Test initialization with custom configuration."""
    with patch('builtins.open', mock_open()):
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device info
            mock_device = {
                'maxInputChannels': 2,
                'maxOutputChannels': 2,
                'defaultSampleRate': 44100,
                'name': 'Test Device'
            }
            mock_pyaudio.return_value.get_device_count.return_value = 1
            mock_pyaudio.return_value.get_device_info_by_index.return_value = mock_device
            
            assistant = VoiceAssistant(words=['hey', 'hi'], timeout_seconds=10.0)
            
            assert assistant.app_config.words == ['hey', 'hi']
            assert assistant.app_config.timeout_seconds == 10.0

def test_is_speech(assistant, mock_is_speech):
    """Test speech detection."""
    mock_config = AudioConfig()
    mock_audio = b'audio_data'
    
    # Test when speech is detected
    mock_is_speech.return_value = True
    assert assistant.is_speech(mock_audio, mock_config)
    mock_is_speech.assert_called_once_with(mock_audio, mock_config)

def test_is_speech_error(assistant, mock_is_speech):
    """Test speech detection error handling."""
    mock_config = AudioConfig()
    mock_audio = b'audio_data'
    
    mock_is_speech.side_effect = Exception("Speech detection error")
    result = assistant.is_speech(mock_audio, mock_config)
    assert not result  # Should return False on error
    mock_is_speech.assert_called_once_with(mock_audio, mock_config)

def test_init_no_activation_sound(mock_openai):
    """Test initialization when activation sound file is not found."""
    with patch('builtins.open', mock_open()) as mock_file:
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device info
            mock_device = {
                'maxInputChannels': 2,
                'maxOutputChannels': 2,
                'defaultSampleRate': 44100,
                'name': 'Test Device'
            }
            mock_pyaudio.return_value.get_device_count.return_value = 1
            mock_pyaudio.return_value.get_device_info_by_index.return_value = mock_device
            
            mock_file.side_effect = FileNotFoundError()
            assistant = VoiceAssistant(words=['hey'])
            assert assistant.activation_sound is None

def test_check_timeout_not_timed_out(assistant):
    """Test timeout check when not timed out."""
    assistant.is_awake = True
    assistant.last_interaction = datetime.now()
    assert not assistant._check_timeout()

def test_check_timeout_timed_out(assistant):
    """Test timeout check when timed out."""
    assistant.is_awake = True
    assistant.last_interaction = datetime.now() - timedelta(seconds=10)
    assistant.app_config.timeout_seconds = 5
    assert assistant._check_timeout()

def test_cleanup(assistant):
    """Test cleanup of temporary files."""
    test_files = ['recording.wav', 'response.mp3']
    
    # Create mock files
    mock_files = {file: True for file in test_files}
    
    with patch('os.path.exists', lambda x: mock_files.get(x, False)), \
         patch('os.remove') as mock_remove:
        assistant._cleanup()
        assert mock_remove.call_count == len(test_files)

def test_cleanup_error(assistant):
    """Test cleanup when file removal fails."""
    test_files = ['recording.wav', 'response.mp3']
    mock_files = {file: True for file in test_files}
    
    with patch('os.path.exists', lambda x: mock_files.get(x, False)), \
         patch('os.remove', side_effect=Exception("Remove error")):
        assistant._cleanup()  # Should not raise exception

def test_listen_for_trigger_word_detected(assistant):
    """Test successful trigger word detection."""
    mock_audio_data = b'test_audio'
    assistant.audio_recorder.stop_recording.return_value = mock_audio_data
    assistant.word_detector.detect.return_value = True
    
    with patch('builtins.open', mock_open()) as mock_file:
        assert assistant._listen_for_trigger_word()
    
    mock_file().write.assert_called_once_with(mock_audio_data)
    assistant.audio_player.play.assert_called_once_with(assistant.activation_sound)

def test_listen_for_trigger_word_not_detected(assistant):
    """Test when trigger word is not detected."""
    mock_audio_data = b'test_audio'
    assistant.audio_recorder.stop_recording.return_value = mock_audio_data
    assistant.word_detector.detect.return_value = False
    
    with patch('builtins.open', mock_open()):
        assert not assistant._listen_for_trigger_word()

def test_record_user_input_success(assistant):
    """Test successful user input recording."""
    mock_audio_data = b'test_audio'
    assistant.audio_recorder.stop_recording.return_value = mock_audio_data
    
    with patch('builtins.open', mock_open()) as mock_file:
        result = assistant._record_user_input()
    
    assert result == mock_audio_data
    assistant.audio_recorder.start_recording.assert_called_once()
    assistant.audio_recorder.stop_recording.assert_called_once_with(is_wake_word_mode=False)

def test_record_user_input_no_speech(assistant):
    """Test when no speech is detected during recording."""
    assistant.audio_recorder.stop_recording.return_value = None
    assert assistant._record_user_input() is None

@patch('time.sleep')  # Mock sleep to speed up tests
def test_run_conversation_flow(mock_sleep, mock_cleanup_assistant):
    """Test the main conversation flow."""
    # Mock a single conversation cycle
    def run_once(*args, **kwargs):
        mock_cleanup_assistant.is_awake = True
        raise KeyboardInterrupt()
    
    mock_cleanup_assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    mock_cleanup_assistant.openai_wrapper.transcribe_audio.return_value = "Hello"
    mock_cleanup_assistant.openai_wrapper.get_chat_completion.return_value = "Hi there!"
    mock_cleanup_assistant.openai_wrapper.text_to_speech.return_value = b"audio_response"
    mock_cleanup_assistant._record_user_input = Mock(return_value=b"test_audio")
    
    # Run the assistant
    mock_cleanup_assistant.run()
    
    # Verify the conversation flow
    mock_cleanup_assistant._listen_for_trigger_word.assert_called_once()
    mock_cleanup_assistant.conversation_manager.add_user_message.assert_not_called()  # Interrupted before this
    mock_cleanup_assistant._cleanup.assert_called_once()

def test_run_transcription_error(mock_sleep, mock_cleanup_assistant):
    """Test conversation flow when transcription fails."""
    def run_once(*args, **kwargs):
        mock_cleanup_assistant.is_awake = True
        raise KeyboardInterrupt()
    
    mock_cleanup_assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    mock_cleanup_assistant.openai_wrapper.transcribe_audio.return_value = None
    mock_cleanup_assistant._record_user_input = Mock(return_value=b"test_audio")
    
    mock_cleanup_assistant.run()
    mock_cleanup_assistant._cleanup.assert_called_once()

def test_run_chat_completion_error(mock_sleep, mock_cleanup_assistant):
    """Test conversation flow when chat completion fails."""
    def run_once(*args, **kwargs):
        mock_cleanup_assistant.is_awake = True
        raise KeyboardInterrupt()
    
    mock_cleanup_assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    mock_cleanup_assistant.openai_wrapper.transcribe_audio.return_value = "Hello"
    mock_cleanup_assistant.openai_wrapper.get_chat_completion.return_value = None
    mock_cleanup_assistant._record_user_input = Mock(return_value=b"test_audio")
    
    mock_cleanup_assistant.run()
    mock_cleanup_assistant._cleanup.assert_called_once()

def test_run_tts_error(mock_sleep, mock_cleanup_assistant):
    """Test conversation flow when text-to-speech fails."""
    def run_once(*args, **kwargs):
        mock_cleanup_assistant.is_awake = True
        raise KeyboardInterrupt()
    
    mock_cleanup_assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    mock_cleanup_assistant.openai_wrapper.transcribe_audio.return_value = "Hello"
    mock_cleanup_assistant.openai_wrapper.get_chat_completion.return_value = "Hi"
    mock_cleanup_assistant.openai_wrapper.text_to_speech.return_value = None
    mock_cleanup_assistant._record_user_input = Mock(return_value=b"test_audio")
    
    mock_cleanup_assistant.run()
    mock_cleanup_assistant._cleanup.assert_called_once()

def test_run_audio_playback_error(mock_sleep, mock_cleanup_assistant):
    """Test conversation flow when audio playback fails."""
    def run_once(*args, **kwargs):
        mock_cleanup_assistant.is_awake = True
        raise KeyboardInterrupt()
    
    mock_cleanup_assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    mock_cleanup_assistant.openai_wrapper.transcribe_audio.return_value = "Hello"
    mock_cleanup_assistant.openai_wrapper.get_chat_completion.return_value = "Hi"
    mock_cleanup_assistant.openai_wrapper.text_to_speech.return_value = b"audio"
    mock_cleanup_assistant.audio_player.play.side_effect = AudioPlayerError("Playback error")
    mock_cleanup_assistant._record_user_input = Mock(return_value=b"test_audio")
    
    mock_cleanup_assistant.run()
    mock_cleanup_assistant._cleanup.assert_called_once()

def test_run_no_speech_no_whisper(mock_sleep, mock_cleanup_assistant, mock_is_speech):
    """Test that Whisper is not called when no speech is detected."""
    # Setup
    assistant = mock_cleanup_assistant
    
    # Configure mocks
    def run_once(*args, **kwargs):
        assistant.is_awake = True
        raise KeyboardInterrupt()
    
    assistant._listen_for_trigger_word = Mock(side_effect=run_once)
    assistant._record_user_input = Mock(return_value=None)  # No speech detected
    
    # Run the assistant
    assistant.run()
    
    # Verify
    assistant._listen_for_trigger_word.assert_called_once()
    assistant.openai_wrapper.transcribe_audio.assert_not_called()  # Verify Whisper was not called
    assistant.conversation_manager.add_user_message.assert_not_called()
    assistant.openai_wrapper.get_chat_completion.assert_not_called()
    assistant._cleanup.assert_called_once()

def test_run_with_speech_calls_whisper(mock_sleep, mock_cleanup_assistant, mock_is_speech):
    """Test that Whisper is called when speech is detected."""
    # Setup
    assistant = mock_cleanup_assistant
    
    # Track state for mocks
    trigger_word_called = False
    check_timeout_called = False
    
    # Configure mocks
    def trigger_word_mock(*args, **kwargs):
        nonlocal trigger_word_called
        if not trigger_word_called:
            trigger_word_called = True
            return True
        raise KeyboardInterrupt()
    
    def check_timeout_mock(*args, **kwargs):
        nonlocal check_timeout_called
        if not check_timeout_called:
            check_timeout_called = True
            return False
        return True
    
    assistant._listen_for_trigger_word = Mock(side_effect=trigger_word_mock)
    assistant._record_user_input = Mock(return_value=b"test_audio")  # Speech detected
    assistant._check_timeout = Mock(side_effect=check_timeout_mock)  # Control flow
    assistant.openai_wrapper.transcribe_audio.return_value = "Hello"
    assistant.openai_wrapper.get_chat_completion.return_value = "Hi there!"
    assistant.openai_wrapper.text_to_speech.return_value = b"audio_response"
    assistant.audio_player.play = Mock()  # Mock audio playback
    
    # Run the assistant
    assistant.run()
    
    # Verify
    assistant._listen_for_trigger_word.assert_called()
    assistant._record_user_input.assert_called_once()
    assistant.openai_wrapper.transcribe_audio.assert_called_once()  # Verify Whisper was called
    assistant.conversation_manager.add_user_message.assert_called_once_with("Hello")
    assistant._cleanup.assert_called_once()

def test_main_no_api_key():
    """Test main function without API key."""
    with patch.dict(os.environ, clear=True):
        assert main() == 1

def test_main_with_api_key():
    """Test main function with API key."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}), \
         patch('src.app.VoiceAssistant') as mock_assistant:
        assert main() == 0
        mock_assistant.assert_called_once()
        mock_assistant.return_value.run.assert_called_once()

def test_main_error(mock_openai):
    """Test main function when assistant initialization fails."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
        with patch('src.app.VoiceAssistant') as mock_assistant_class:
            mock_assistant_class.return_value = Mock()
            mock_assistant_class.return_value.run.side_effect = Exception("Init error")
            assert main() == 1
