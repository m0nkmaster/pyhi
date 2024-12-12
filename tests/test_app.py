import pytest
import os
import pyaudio
import wave
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import speech_recognition as sr
from src.app import VoiceAssistant
from src.config import AppConfig, AudioConfig, AIConfig
from src.conversation.manager import ChatConversationManager
from src.audio.player import PyAudioPlayer
from src.audio.recorder import PyAudioRecorder
from src.word_detection.detector import PorcupineWakeWordDetector

@pytest.fixture
def mock_audio_config():
    return AudioConfig()

@pytest.fixture
def mock_ai_config():
    return AIConfig()

@pytest.fixture
def mock_app_config():
    return AppConfig(words=["test_wake_word"])

@pytest.fixture
def mock_recognizer():
    recognizer = Mock(spec=sr.Recognizer)
    recognizer.recognize_google.return_value = "test command"
    return recognizer

@pytest.fixture
def mock_audio_player():
    return Mock(spec=PyAudioPlayer)

@pytest.fixture
def mock_audio_recorder():
    recorder = Mock(spec=PyAudioRecorder)
    recorder.record_speech.return_value = b"test audio data"
    recorder.record_chunk.return_value = b"test chunk data"
    recorder.stream = Mock()
    return recorder

@pytest.fixture
def mock_word_detector():
    detector = Mock(spec=PorcupineWakeWordDetector)
    detector.detect.return_value = False
    return detector

@pytest.fixture
def voice_assistant(mock_app_config, mock_audio_player, mock_audio_recorder, mock_word_detector, mock_recognizer):
    with patch('src.app.sr.Recognizer', return_value=mock_recognizer):
        assistant = VoiceAssistant(mock_app_config.words)
        assistant.audio_player = mock_audio_player
        assistant.audio_recorder = mock_audio_recorder
        assistant.word_detector = mock_word_detector
        assistant.recognizer = mock_recognizer
        return assistant

class TestVoiceAssistant:
    def test_initialization(self, voice_assistant):
        """Test proper initialization of VoiceAssistant"""
        assert voice_assistant.running == True
        assert voice_assistant.words == ["test_wake_word"]
        assert voice_assistant.timeout_seconds == 10.0
        assert voice_assistant.is_awake == False
        assert voice_assistant.last_interaction is None

    def test_listen_for_command_success(self, voice_assistant, mock_recognizer):
        """Test successful command recognition"""
        with patch('src.app.sr.Microphone') as mock_mic:
            result = voice_assistant.listen_for_command()
            assert result == "test command"
            mock_recognizer.recognize_google.assert_called_once()

    def test_listen_for_command_no_speech(self, voice_assistant, mock_recognizer):
        """Test command recognition when no speech is detected"""
        mock_recognizer.recognize_google.side_effect = sr.UnknownValueError()
        with patch('src.app.sr.Microphone'):
            result = voice_assistant.listen_for_command()
            assert result is None

    def test_listen_for_trigger_word_detected(self, voice_assistant):
        """Test trigger word detection"""
        voice_assistant.word_detector.detect.return_value = True
        assert voice_assistant._listen_for_trigger_word() == True
        voice_assistant.audio_player.play.assert_called_once()

    def test_listen_for_trigger_word_not_detected(self, voice_assistant):
        """Test when trigger word is not detected"""
        voice_assistant.word_detector.detect.return_value = False
        assert voice_assistant._listen_for_trigger_word() == False
        voice_assistant.audio_player.play.assert_not_called()

    def test_check_timeout_no_interaction(self, voice_assistant):
        """Test timeout check with no previous interaction"""
        assert voice_assistant._check_timeout() == False

    def test_check_timeout_within_limit(self, voice_assistant):
        """Test timeout check within the time limit"""
        voice_assistant.last_interaction = datetime.now()
        assert voice_assistant._check_timeout() == False

    def test_check_timeout_exceeded(self, voice_assistant):
        """Test timeout check when time limit is exceeded"""
        voice_assistant.last_interaction = datetime.now() - timedelta(seconds=15)
        assert voice_assistant._check_timeout() == True

    def test_run_with_trigger_word(self, voice_assistant):
        """Test run method when trigger word is detected"""
        def stop_after_detection(*args):
            voice_assistant.running = False
            return True
            
        voice_assistant.word_detector.detect = Mock(side_effect=stop_after_detection)
        
        # Run the assistant
        voice_assistant.run()
        
        # Verify the sequence of events
        assert voice_assistant.is_awake == True
        voice_assistant.audio_player.play.assert_called_once()
        assert voice_assistant.last_interaction is not None

    def test_signal_handler(self, voice_assistant):
        """Test signal handler cleanup"""
        with pytest.raises(SystemExit):
            voice_assistant._signal_handler(None, None)
        assert voice_assistant.running == False

class TestAIIntegration:
    def test_conversation_manager_initialization(self):
        """Test conversation manager initialization"""
        manager = ChatConversationManager()
        assert len(manager.conversation.messages) == 1  # System prompt
        assert manager.conversation.messages[0].role == "system"

    def test_add_user_message(self):
        """Test adding user message to conversation"""
        manager = ChatConversationManager()
        test_message = "Hello, assistant!"
        manager.add_user_message(test_message)
        assert len(manager.conversation.messages) == 2
        assert manager.conversation.messages[1].role == "user"
        assert manager.conversation.messages[1].content == test_message

    def test_add_assistant_message(self):
        """Test adding assistant message to conversation"""
        manager = ChatConversationManager()
        test_message = "Hello, user!"
        manager.add_assistant_message(test_message)
        assert len(manager.conversation.messages) == 2
        assert manager.conversation.messages[1].role == "assistant"
        assert manager.conversation.messages[1].content == test_message

    def test_get_conversation_history(self):
        """Test retrieving conversation history"""
        manager = ChatConversationManager()
        user_message = "Hello, assistant!"
        assistant_message = "Hello, user!"
        manager.add_user_message(user_message)
        manager.add_assistant_message(assistant_message)
        history = manager.get_conversation_history()
        assert len(history) == 3  # System prompt + user message + assistant message

if __name__ == "__main__":
    pytest.main([__file__])
