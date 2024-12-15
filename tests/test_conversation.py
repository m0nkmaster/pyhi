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

@pytest.fixture
def mock_ai_client(ai_config):
    mock_client = Mock(spec=AIWrapper)
    mock_client.config = ai_config
    mock_client.get_completion.return_value = {"content": "Test response"}
    return mock_client

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
    def test_initialization(self, mock_ai_client):
        manager = ChatConversationManager(ai_client=mock_ai_client)
        assert len(manager.conversation.messages) == 1  # System prompt
        assert manager.conversation.messages[0].role == "system"
        assert manager.ai_client == mock_ai_client

    def test_add_messages(self, mock_ai_client):
        manager = ChatConversationManager(ai_client=mock_ai_client)
        
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

    def test_get_conversation_history(self, mock_ai_client):
        manager = ChatConversationManager(ai_client=mock_ai_client)
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

    def test_process_assistant_response_with_function_calls(self, mock_ai_client):
        # Create a mock function manager
        mock_function_manager = Mock()
        mock_function_manager.call_function.return_value = "Function response"

        # Create the conversation manager with both mocks
        manager = ChatConversationManager(
            function_manager=mock_function_manager,
            ai_client=mock_ai_client
        )

        # Create a response with a function call
        response = {
            "content": "Let me help you with that.",
            "tool_calls": [
                Mock(
                    type="function",
                    id="call_1",
                    function=Mock(
                        name="test_function",
                        arguments='{"param": "value"}'
                    )
                )
            ]
        }

        # Set up the mock AI client to return a response for the second API call
        mock_ai_client.get_completion.return_value = {
            "content": "Here's what I found: Function response"
        }

        # Process the response
        result = manager.process_assistant_response(response)

        # Verify the function was called
        mock_function_manager.call_function.assert_called_once_with(
            "test_function",
            param="value"
        )

        # Verify the second API call was made
        mock_ai_client.get_completion.assert_called_once()

        # Verify the final response
        assert result == "Here's what I found: Function response"

    def test_process_assistant_response_without_ai_client(self):
        manager = ChatConversationManager()  # No AI client provided
        response = {
            "content": "Let me help you with that.",
            "tool_calls": [
                Mock(
                    type="function",
                    id="call_1",
                    function=Mock(
                        name="test_function",
                        arguments='{"param": "value"}'
                    )
                )
            ]
        }
        
        result = manager.process_assistant_response(response)
        assert "I apologize, but I encountered an issue processing the data" in result
