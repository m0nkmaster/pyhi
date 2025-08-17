import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.conversation.ai_client import AIWrapper
from src.conversation.manager import ChatConversationManager, Message
from src.config import Config


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager for testing"""
    manager = Mock()
    manager.call_tool = AsyncMock(return_value="MCP tool response")
    return manager


@pytest.fixture
def mock_ai_client(config):
    """Mock AI client"""
    client = Mock(spec=AIWrapper)
    client.config = config.ai
    client.get_completion.return_value = {"content": "Test AI response"}
    return client


class TestAIWrapper:
    def test_initialization(self, config):
        """Test AIWrapper initialization"""
        wrapper = AIWrapper(config.ai)
        assert wrapper.config == config.ai
        assert wrapper.provider == config.ai.provider
        assert wrapper.model == config.ai.model


    @patch('openai.OpenAI')
    def test_get_completion_openai(self, mock_openai_class, config):
        """Test OpenAI completion"""
        # Configure mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_message = Mock()
        mock_message.content = "OpenAI response"
        mock_message.tool_calls = None  # Add hasattr check support
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = mock_message
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test
        config.ai.provider = "openai"
        config.ai.api_key = "test-key"  # Set test API key
        wrapper = AIWrapper(config.ai)
        
        messages = [{"role": "user", "content": "Hello"}]
        response = wrapper.get_completion(messages)
        
        # Verify
        assert response["content"] == "OpenAI response"
        assert response["tool_calls"] is None
        mock_client.chat.completions.create.assert_called_once()


    @patch('openai.OpenAI')
    def test_get_completion_openai_with_tools(self, mock_openai_class, config, mock_mcp_manager):
        """Test OpenAI completion with MCP tools"""
        # Configure mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock MCP manager to provide tools
        mock_mcp_manager.get_tools.return_value = [
            {"type": "function", "function": {"name": "get_weather", "description": "Get weather", "parameters": {}}}
        ]
        
        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "test_function"
        mock_tool_call.function.arguments = '{"param": "value"}'
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_message = Mock()
        mock_message.content = "I'll help you with that"
        mock_message.tool_calls = [mock_tool_call]
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = mock_message
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test with MCP manager
        config.ai.provider = "openai"
        config.ai.api_key = "test-key"
        wrapper = AIWrapper(config.ai, mcp_manager=mock_mcp_manager)
        
        messages = [{"role": "user", "content": "What's the weather?"}]
        response = wrapper.get_completion(messages)
        
        # Verify
        assert response["content"] == "I'll help you with that"
        assert response["tool_calls"] == [mock_tool_call]
        mock_mcp_manager.get_tools.assert_called_once()


    @patch('anthropic.Anthropic')
    def test_get_completion_anthropic(self, mock_anthropic_class, config):
        """Test Anthropic completion"""
        # Configure mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_content_block = Mock()
        mock_content_block.type = "text"
        mock_content_block.text = "Anthropic response"
        
        mock_response = Mock()
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response
        
        # Test
        config.ai.provider = "anthropic"
        config.ai.api_key = "test-key"  # Set a test API key
        wrapper = AIWrapper(config.ai)
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        response = wrapper.get_completion(messages)
        
        # Verify
        assert response["content"] == "Anthropic response"
        assert response["tool_calls"] is None
        mock_client.messages.create.assert_called_once()


    @patch('anthropic.Anthropic')
    def test_get_completion_anthropic_with_tools(self, mock_anthropic_class, config, mock_mcp_manager):
        """Test Anthropic completion with MCP tools"""
        # Configure mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock MCP manager to provide tools
        mock_mcp_manager.get_tools.return_value = [
            {"type": "function", "function": {"name": "get_weather", "description": "Get weather", "parameters": {}}}
        ]
        
        # Mock tool use response
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "I'll check the weather for you."
        
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "toolu_123"
        mock_tool_block.name = "get_weather"
        mock_tool_block.input = {"location": "NYC"}
        
        mock_response = Mock()
        mock_response.content = [mock_text_block, mock_tool_block]
        mock_client.messages.create.return_value = mock_response
        
        # Test
        config.ai.provider = "anthropic"
        config.ai.api_key = "test-key"
        wrapper = AIWrapper(config.ai, mcp_manager=mock_mcp_manager)
        
        messages = [{"role": "user", "content": "What's the weather in NYC?"}]
        response = wrapper.get_completion(messages)
        
        # Verify
        assert response["content"] == "I'll check the weather for you."
        assert response["tool_calls"] is not None
        assert len(response["tool_calls"]) == 1
        assert response["tool_calls"][0].function.name == "get_weather"
        mock_mcp_manager.get_tools.assert_called_once()


    @patch('openai.OpenAI')
    def test_text_to_speech(self, mock_openai_class, config):
        """Test text-to-speech functionality"""
        # Configure mock
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = b"audio_data"
        mock_client.audio.speech.create.return_value = mock_response
        
        # Test
        config.ai.api_key = "test-key"
        wrapper = AIWrapper(config.ai)
        audio_data = wrapper.text_to_speech("Hello world")
        
        # Verify
        assert audio_data == b"audio_data"
        mock_client.audio.speech.create.assert_called_once_with(
            model=config.ai.voice_model,
            voice=config.ai.voice,
            input="Hello world"
        )


    def test_invalid_provider(self, config):
        """Test invalid AI provider"""
        config.ai.provider = "invalid_provider"
        wrapper = AIWrapper(config.ai)
        
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            wrapper.get_completion([{"role": "user", "content": "test"}])


class TestChatConversationManager:
    def test_initialization(self, mock_ai_client):
        """Test conversation manager initialization"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        
        # Should have system message
        assert len(manager.conversation.messages) == 1
        assert manager.conversation.messages[0].role == "system"
        assert manager.ai_client == mock_ai_client


    def test_add_messages(self, mock_ai_client):
        """Test adding user and assistant messages"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        
        # Add user message
        manager.add_user_message("Hello assistant")
        assert len(manager.conversation.messages) == 2
        assert manager.conversation.messages[-1].role == "user"
        assert manager.conversation.messages[-1].content == "Hello assistant"
        
        # Add assistant message
        manager.add_assistant_message("Hello user")
        assert len(manager.conversation.messages) == 3
        assert manager.conversation.messages[-1].role == "assistant"
        assert manager.conversation.messages[-1].content == "Hello user"


    def test_get_conversation_history(self, mock_ai_client):
        """Test getting conversation history"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        manager.add_user_message("Test message")
        
        history = manager.get_conversation_history()
        
        assert len(history) == 2  # System + user
        assert isinstance(history, list)
        assert all(isinstance(msg, dict) for msg in history)
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[1]["content"] == "Test message"


    def test_clear_history(self, mock_ai_client):
        """Test clearing conversation history"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        manager.add_user_message("Test")
        manager.add_assistant_message("Response")
        
        assert len(manager.conversation.messages) == 3
        
        manager.clear_history()
        
        # Should only have system prompt
        assert len(manager.conversation.messages) == 1
        assert manager.conversation.messages[0].role == "system"


    def test_get_last_messages(self, mock_ai_client):
        """Test getting last user/assistant messages"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        manager.add_user_message("User message 1")
        manager.add_assistant_message("Assistant response 1")
        manager.add_user_message("User message 2")
        
        last_user = manager.get_last_user_message()
        last_assistant = manager.get_last_assistant_message()
        
        assert last_user == "User message 2"
        assert last_assistant == "Assistant response 1"


    def test_process_assistant_response_simple(self, mock_ai_client):
        """Test processing simple assistant response without tools"""
        manager = ChatConversationManager(ai_client=mock_ai_client)
        
        response = {"content": "Simple response"}
        result = manager.process_assistant_response(response)
        
        assert result == "Simple response"
        assert len(manager.conversation.messages) == 2  # System + assistant


    def test_process_assistant_response_with_mcp_tools(self, mock_ai_client, mock_mcp_manager):
        """Test processing assistant response with MCP tool calls"""
        manager = ChatConversationManager(
            ai_client=mock_ai_client,
            mcp_manager=mock_mcp_manager
        )
        
        # Mock tool call
        mock_tool_call = Mock()
        mock_tool_call.type = "function"
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "get_weather"
        mock_tool_call.function.arguments = '{"location": "London"}'
        
        # Mock MCP response with content attribute
        mock_mcp_response = Mock()
        mock_mcp_response.content = [Mock(text="Weather: Sunny, 22°C")]
        mock_mcp_manager.call_tool.return_value = mock_mcp_response
        
        # Mock second AI call
        mock_ai_client.get_completion.return_value = {
            "content": "The weather in London is sunny with 22°C"
        }
        
        response = {
            "content": "I'll check the weather for you",
            "tool_calls": [mock_tool_call]
        }
        
        result = manager.process_assistant_response(response)
        
        # Verify MCP tool was called
        mock_mcp_manager.call_tool.assert_called_once_with(
            "get_weather", {"location": "London"}
        )
        
        # Verify second AI call was made
        mock_ai_client.get_completion.assert_called_once()
        
        # Verify result
        assert result == "The weather in London is sunny with 22°C"


    def test_process_assistant_response_tool_error(self, mock_ai_client, mock_mcp_manager):
        """Test handling tool call errors"""
        manager = ChatConversationManager(
            ai_client=mock_ai_client,
            mcp_manager=mock_mcp_manager
        )
        
        # Mock tool call
        mock_tool_call = Mock()
        mock_tool_call.type = "function"
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "broken_tool"
        mock_tool_call.function.arguments = '{"param": "value"}'
        
        # Mock MCP error
        mock_mcp_manager.call_tool.side_effect = Exception("Tool error")
        
        response = {
            "content": "I'll use a tool",
            "tool_calls": [mock_tool_call]
        }
        
        result = manager.process_assistant_response(response)
        
        # Should continue without the tool call
        assert "I'll use a tool" in result


    def test_process_assistant_response_no_ai_client(self):
        """Test processing response without AI client"""
        manager = ChatConversationManager()  # No AI client
        
        mock_tool_call = Mock()
        mock_tool_call.type = "function"
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "test_tool"
        mock_tool_call.function.arguments = '{"param": "value"}'
        
        response = {
            "content": "Using tools",
            "tool_calls": [mock_tool_call]
        }
        
        result = manager.process_assistant_response(response)
        
        # Should return error message
        assert "I apologize, but I encountered an issue" in result


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
        # Valid roles should work
        Message(role="system", content="System prompt")
        Message(role="user", content="User message")
        Message(role="assistant", content="Assistant response")
        Message(role="tool", content="Tool response", name="tool_name", tool_call_id="call_123")
        
        # Invalid role should raise error
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid", content="Test")


    def test_tool_message_validation(self):
        """Test tool message specific validation"""
        # Tool message without name should raise error
        with pytest.raises(ValueError, match="Tool messages must have a name"):
            Message(role="tool", content="Response")
        
        # Tool message without tool_call_id should raise error
        with pytest.raises(ValueError, match="Tool messages must have a tool_call_id"):
            Message(role="tool", content="Response", name="tool_name")


    def test_message_content_handling(self):
        """Test message content handling"""
        # None content should become empty string
        message = Message(role="user", content=None)
        assert message.content == ""