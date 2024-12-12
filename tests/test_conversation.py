import pytest
from unittest.mock import Mock, patch, PropertyMock
from src.conversation.ai_client import AIWrapper, OpenAI, Anthropic
from src.conversation.manager import ChatConversationManager, Message
from src.config import AIConfig

@pytest.fixture
def ai_config():
    config = AIConfig()
    config.chat_provider = "openai"
    config.chat_model = "gpt-3.5-turbo"
    return config

class TestAIWrapper:
    def test_initialization(self, ai_config):
        wrapper = AIWrapper(ai_config)
        assert wrapper.config == ai_config
        assert wrapper.chat_provider == ai_config.chat_provider
        assert wrapper.chat_model == ai_config.chat_model

    @patch('src.conversation.ai_client.OpenAI')
    def test_get_completion_openai(self, mock_openai_cls, ai_config):
        mock_client = Mock()
        mock_openai_cls.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        
        ai_config.chat_provider = "openai"
        wrapper = AIWrapper(ai_config)
        
        messages = [{"role": "user", "content": "Hello"}]
        response = wrapper.get_completion(messages)
        assert response == "Test response"
        mock_client.chat.completions.create.assert_called_once_with(
            model=ai_config.chat_model,
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )

    @patch('src.conversation.ai_client.Anthropic')
    def test_get_completion_claude(self, mock_anthropic_cls, ai_config):
        mock_client = Mock()
        mock_anthropic_cls.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_client.messages.create.return_value = mock_response
        
        ai_config.chat_provider = "claude"
        wrapper = AIWrapper(ai_config)
        
        messages = [{"role": "user", "content": "Hello"}]
        response = wrapper.get_completion(messages)
        assert response == "Test response"
        mock_client.messages.create.assert_called_once_with(
            model=ai_config.chat_model,
            system=None,  # No system message in test
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=150
        )

    def test_invalid_provider(self, ai_config):
        ai_config.chat_provider = "invalid"
        wrapper = AIWrapper(ai_config)
        messages = [{"role": "user", "content": "Hello"}]
        with pytest.raises(ValueError, match="Unsupported AI chat_provider: invalid"):
            wrapper.get_completion(messages)

class TestChatConversationManager:
    def test_initialization(self):
        manager = ChatConversationManager()
        assert len(manager.conversation.messages) == 1  # System prompt
        assert manager.conversation.messages[0].role == "system"

    def test_add_messages(self):
        manager = ChatConversationManager()
        
        # Test adding user message
        manager.add_user_message("Hello")
        assert len(manager.conversation.messages) == 2
        assert manager.conversation.messages[-1].role == "user"
        assert manager.conversation.messages[-1].content == "Hello"
        
        # Test adding assistant message
        manager.add_assistant_message("Hi there")
        assert len(manager.conversation.messages) == 3
        assert manager.conversation.messages[-1].role == "assistant"
        assert manager.conversation.messages[-1].content == "Hi there"

    def test_get_conversation_history(self):
        manager = ChatConversationManager()
        manager.add_user_message("Hello")
        manager.add_assistant_message("Hi")
        
        history = manager.get_conversation_history()
        assert len(history) == 3  # System + user + assistant
        assert isinstance(history, list)
        assert all(isinstance(msg, dict) for msg in history)
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[2]["role"] == "assistant"
        assert history[1]["content"] == "Hello"
        assert history[2]["content"] == "Hi"
