import pytest
from unittest.mock import Mock, patch
from src.conversation.ai_client import AIWrapper
from src.conversation.manager import ChatConversationManager, Message
from src.config import AIConfig


@pytest.fixture
def ai_config():
    config = AIConfig()
    config.api_key = "test-key"
    return config


class TestAIWrapper:
    def test_initialization(self, ai_config):
        """Test AIWrapper initialization"""
        wrapper = AIWrapper(ai_config)
        assert wrapper.config == ai_config
        assert wrapper.provider == ai_config.provider
        assert wrapper.model == ai_config.model


    def test_invalid_provider(self, ai_config):
        """Test invalid AI provider"""
        ai_config.provider = "invalid_provider"
        wrapper = AIWrapper(ai_config)
        
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            wrapper.get_completion([{"role": "user", "content": "test"}])


    @patch('openai.OpenAI')
    def test_text_to_speech_empty_text(self, mock_openai_class, ai_config):
        """Test text-to-speech with empty text"""
        wrapper = AIWrapper(ai_config)
        
        assert wrapper.text_to_speech("") is None
        assert wrapper.text_to_speech("   ") is None
        assert wrapper.text_to_speech(None) is None


class TestChatConversationManager:
    def test_initialization(self):
        """Test conversation manager initialization"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: {"ip": "1.2.3.4"}),
                Mock(status_code=200, json=lambda: {"city": "Test City", "region": "Test Region", "country_name": "Test Country"})
            ]
            
            manager = ChatConversationManager()
            assert len(manager.conversation.messages) == 1
            assert manager.conversation.messages[0].role == "system"


    def test_add_messages(self):
        """Test adding user and assistant messages"""
        with patch('requests.get', side_effect=Exception("Network error")):
            manager = ChatConversationManager()
            
            manager.add_user_message("Hello assistant")
            assert len(manager.conversation.messages) == 2
            assert manager.conversation.messages[-1].role == "user"
            assert manager.conversation.messages[-1].content == "Hello assistant"


    def test_clear_history(self):
        """Test clearing conversation history"""
        with patch('requests.get', side_effect=Exception("Network error")):
            manager = ChatConversationManager()
            manager.add_user_message("Test")
            
            assert len(manager.conversation.messages) == 2
            manager.clear_history()
            assert len(manager.conversation.messages) == 1
            assert manager.conversation.messages[0].role == "system"


    def test_process_assistant_response_simple(self):
        """Test processing simple assistant response without tools"""
        with patch('requests.get', side_effect=Exception("Network error")):
            manager = ChatConversationManager()
            
            response = {"content": "Simple response"}
            result = manager.process_assistant_response(response)
            
            assert result == "Simple response"
            assert len(manager.conversation.messages) == 2


class TestMessage:
    def test_message_creation(self):
        """Test Message dataclass creation"""
        message = Message(role="user", content="Hello")
        
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.tool_call_id is None
        assert message.tool_calls is None
        assert message.name is None


    def test_message_validation(self):
        """Test Message validation"""
        Message(role="system", content="System prompt")
        Message(role="user", content="User message")
        Message(role="assistant", content="Assistant response")
        Message(role="tool", content="Tool response", name="tool_name", tool_call_id="call_123")
        
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid", content="Test")


    def test_message_content_handling(self):
        """Test message content handling"""
        message = Message(role="user", content=None)
        assert message.content == ""