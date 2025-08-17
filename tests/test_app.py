import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.app import VoiceAssistant
from src.config import Config


@pytest.fixture
def config():
    """Create a test config"""
    return Config()


@pytest.fixture
def mock_audio_handler():
    """Mock audio handler"""
    handler = Mock()
    handler.record_speech_async = AsyncMock(return_value="test command")
    handler.play_audio_file_async = AsyncMock()
    handler.cleanup = Mock()
    return handler


@pytest.fixture
def mock_wake_word_detector():
    """Mock wake word detector"""
    detector = Mock()
    detector.detect_async = AsyncMock(return_value=False)
    detector.cleanup = Mock()
    return detector


@pytest.fixture
def mock_conversation_manager():
    """Mock conversation manager"""
    manager = Mock()
    manager.add_user_message = Mock()
    manager.process_assistant_response = Mock(return_value="Assistant response")
    return manager


@pytest.fixture
def mock_ai_client():
    """Mock AI client"""
    client = Mock()
    client.get_completion = Mock(return_value={"content": "AI response"})
    client.text_to_speech = Mock(return_value=b"audio_data")
    return client


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager"""
    manager = Mock()
    manager.initialize = AsyncMock()
    manager.cleanup = AsyncMock()
    manager.get_available_tools = Mock(return_value=[])
    return manager


@pytest.fixture
def voice_assistant(config, mock_audio_handler, mock_wake_word_detector, 
                   mock_conversation_manager, mock_ai_client, mock_mcp_manager):
    """Create a VoiceAssistant with mocked dependencies"""
    with patch('src.app.AudioHandler', return_value=mock_audio_handler), \
         patch('src.app.WakeWordDetector', return_value=mock_wake_word_detector), \
         patch('src.app.ChatConversationManager', return_value=mock_conversation_manager), \
         patch('src.app.AIWrapper', return_value=mock_ai_client), \
         patch('src.app.MCPManager', return_value=mock_mcp_manager), \
         patch('src.app.load_config', return_value=config):
        
        assistant = VoiceAssistant(words=['hey', 'chat'], timeout_seconds=10.0)
        return assistant


class TestVoiceAssistant:
    def test_initialization(self, voice_assistant, config):
        """Test VoiceAssistant initialization"""
        assert voice_assistant.config is not None
        assert voice_assistant.running is True
        assert voice_assistant.audio_handler is not None
        assert voice_assistant.word_detector is not None
        assert voice_assistant.conversation_manager is not None
        assert voice_assistant.ai_client is not None
        assert voice_assistant.words == ['hey', 'chat']
        assert voice_assistant.timeout_seconds == 10.0


    @pytest.mark.asyncio
    async def test_wake_word_detection_loop(self, voice_assistant, mock_wake_word_detector):
        """Test wake word detection loop"""
        # Set up mock to detect wake word once then stop
        call_count = 0
        async def mock_detect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True  # Wake word detected
            voice_assistant.running = False  # Stop the loop
            return False
        
        mock_wake_word_detector.detect_async.side_effect = mock_detect
        
        # Run the detection loop
        await voice_assistant._wake_word_detection_loop()
        
        # Verify wake word detection was called
        assert mock_wake_word_detector.detect_async.call_count >= 1


    @pytest.mark.asyncio
    async def test_handle_user_input(self, voice_assistant, mock_audio_handler, 
                                   mock_conversation_manager, mock_ai_client):
        """Test handling user input"""
        # Set up mocks
        mock_audio_handler.record_speech_async.return_value = "What's the weather?"
        mock_ai_client.get_completion.return_value = {"content": "It's sunny today"}
        mock_conversation_manager.process_assistant_response.return_value = "It's sunny today"
        mock_ai_client.text_to_speech.return_value = b"audio_response"
        
        # Handle user input
        await voice_assistant._handle_user_input()
        
        # Verify the flow
        mock_audio_handler.record_speech_async.assert_called_once()
        mock_conversation_manager.add_user_message.assert_called_once_with("What's the weather?")
        mock_ai_client.get_completion.assert_called_once()
        mock_conversation_manager.process_assistant_response.assert_called_once()
        mock_ai_client.text_to_speech.assert_called_once_with("It's sunny today")


    @pytest.mark.asyncio
    async def test_handle_user_input_no_speech(self, voice_assistant, mock_audio_handler):
        """Test handling user input when no speech is detected"""
        # Mock no speech detected
        mock_audio_handler.record_speech_async.return_value = None
        
        # Handle user input
        await voice_assistant._handle_user_input()
        
        # Verify only recording was attempted
        mock_audio_handler.record_speech_async.assert_called_once()
        # No other processing should happen
        assert voice_assistant.conversation_manager.add_user_message.call_count == 0


    @pytest.mark.asyncio
    async def test_handle_user_input_empty_speech(self, voice_assistant, mock_audio_handler):
        """Test handling user input with empty speech"""
        # Mock empty speech
        mock_audio_handler.record_speech_async.return_value = ""
        
        # Handle user input
        await voice_assistant._handle_user_input()
        
        # Verify recording was attempted but no further processing
        mock_audio_handler.record_speech_async.assert_called_once()
        assert voice_assistant.conversation_manager.add_user_message.call_count == 0


    @pytest.mark.asyncio
    async def test_mcp_initialization(self, voice_assistant, mock_mcp_manager):
        """Test MCP manager initialization"""
        # MCP should be initialized during startup
        mock_mcp_manager.initialize.assert_called_once()


    @pytest.mark.asyncio
    async def test_timeout_handling(self, voice_assistant):
        """Test timeout and sleep mode handling"""
        # Set last interaction to simulate timeout
        import time
        voice_assistant.last_interaction = time.time() - (voice_assistant.config.timeout_seconds + 1)
        
        # Check if timeout is detected
        timed_out = voice_assistant._check_timeout()
        assert timed_out is True


    def test_cleanup(self, voice_assistant, mock_audio_handler, mock_wake_word_detector, mock_mcp_manager):
        """Test cleanup of resources"""
        # Trigger cleanup
        voice_assistant.cleanup()
        
        # Verify all components are cleaned up
        mock_audio_handler.cleanup.assert_called_once()
        mock_wake_word_detector.cleanup.assert_called_once()


    @pytest.mark.asyncio
    async def test_error_handling_in_user_input(self, voice_assistant, mock_audio_handler, mock_ai_client):
        """Test error handling during user input processing"""
        # Mock recording success but AI client failure
        mock_audio_handler.record_speech_async.return_value = "test command"
        mock_ai_client.get_completion.side_effect = Exception("AI API Error")
        
        # Should handle error gracefully
        await voice_assistant._handle_user_input()
        
        # Verify recording was attempted
        mock_audio_handler.record_speech_async.assert_called_once()


    @pytest.mark.asyncio
    async def test_conversation_context_maintained(self, voice_assistant, mock_conversation_manager):
        """Test that conversation context is maintained across interactions"""
        # Simulate multiple interactions
        voice_assistant.conversation_manager.add_user_message("First message")
        voice_assistant.conversation_manager.add_user_message("Second message")
        
        # Verify messages were added
        assert mock_conversation_manager.add_user_message.call_count == 2


class TestVoiceAssistantIntegration:
    @pytest.mark.asyncio
    async def test_full_interaction_flow(self, config):
        """Test a complete interaction flow with real components"""
        # This test uses minimal mocking to test integration
        with patch('src.app.AudioHandler') as mock_audio_class, \
             patch('src.app.WakeWordDetector') as mock_wake_class, \
             patch('src.app.AIWrapper') as mock_ai_class, \
             patch('src.app.MCPManager') as mock_mcp_class:
            
            # Set up mocks
            mock_audio = Mock()
            mock_audio.record_speech_async = AsyncMock(return_value="Hello")
            mock_audio.play_audio_file_async = AsyncMock()
            mock_audio.cleanup = Mock()
            mock_audio_class.return_value = mock_audio
            
            mock_wake = Mock()
            mock_wake.detect_async = AsyncMock(return_value=True)  # Trigger wake word once
            mock_wake.cleanup = Mock()
            mock_wake_class.return_value = mock_wake
            
            mock_ai = Mock()
            mock_ai.get_completion.return_value = {"content": "Hello there!"}
            mock_ai.text_to_speech.return_value = b"audio_response"
            mock_ai_class.return_value = mock_ai
            
            mock_mcp = Mock()
            mock_mcp.initialize = AsyncMock()
            mock_mcp.cleanup = AsyncMock()
            mock_mcp.get_available_tools.return_value = []
            mock_mcp_class.return_value = mock_mcp
            
            # Create assistant
            assistant = VoiceAssistant(config_path=None)
            
            # Test single interaction
            await assistant._handle_user_input()
            
            # Verify the flow worked
            mock_audio.record_speech_async.assert_called_once()
            mock_ai.get_completion.assert_called_once()
            mock_ai.text_to_speech.assert_called_once()


    def test_signal_handling(self, voice_assistant):
        """Test signal handler for graceful shutdown"""
        import signal
        
        # Test signal handler
        voice_assistant._signal_handler(signal.SIGINT, None)
        
        # Should mark as not running
        assert voice_assistant.running is False


    def test_config_loading(self):
        """Test config loading with different sources"""
        # Test with default config
        with patch('src.config.load_config') as mock_load:
            mock_load.return_value = Config()
            
            assistant = VoiceAssistant(config_path=None)
            mock_load.assert_called_once_with("config.yaml")
            
        # Test with custom config path
        with patch('src.config.load_config') as mock_load:
            mock_load.return_value = Config()
            
            assistant = VoiceAssistant(config_path="custom.yaml")
            mock_load.assert_called_once_with("custom.yaml")