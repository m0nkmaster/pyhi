import pytest
from src.conversation.manager import ChatConversationManager, Message, Conversation

@pytest.fixture
def manager():
    return ChatConversationManager()

@pytest.fixture
def custom_manager():
    return ChatConversationManager(system_prompt="Custom system prompt")

def test_initialization(manager):
    history = manager.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"
    assert "helpful assistant" in history[0]["content"]

def test_custom_system_prompt(custom_manager):
    history = custom_manager.get_conversation_history()
    assert history[0]["content"] == "Custom system prompt"

def test_add_user_message(manager):
    manager.add_user_message("Hello")
    history = manager.get_conversation_history()
    assert len(history) == 2
    assert history[1]["role"] == "user"
    assert history[1]["content"] == "Hello"

def test_add_assistant_message(manager):
    manager.add_assistant_message("Hi there!")
    history = manager.get_conversation_history()
    assert len(history) == 2
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"

def test_clear_history(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi!")
    manager.clear_history()
    
    history = manager.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"

def test_get_last_user_message(manager):
    manager.add_user_message("First")
    manager.add_assistant_message("Response")
    manager.add_user_message("Second")
    
    assert manager.get_last_user_message() == "Second"

def test_get_last_assistant_message(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("First response")
    manager.add_user_message("Hi again")
    manager.add_assistant_message("Second response")
    
    assert manager.get_last_assistant_message() == "Second response"

def test_get_last_messages_empty(manager):
    assert manager.get_last_user_message() is None
    assert manager.get_last_assistant_message() is None

def test_conversation_format(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi!")
    
    history = manager.get_conversation_history()
    assert all(isinstance(msg, dict) for msg in history)
    assert all("role" in msg and "content" in msg for msg in history) 