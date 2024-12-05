import pytest
from src.conversation.manager import ChatConversationManager, Message, Conversation

@pytest.fixture
def manager():
    return ChatConversationManager()

@pytest.fixture
def custom_manager():
    return ChatConversationManager(system_prompt="Custom system prompt")

def test_init_default_prompt(manager):
    history = manager.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"
    assert history[0]["content"] == Conversation.system_prompt

def test_init_custom_prompt(custom_manager):
    history = custom_manager.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"
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

def test_get_conversation_history_empty(manager):
    history = manager.get_conversation_history()
    assert len(history) == 1  # Just system prompt
    assert all(isinstance(msg, dict) for msg in history)
    assert all("role" in msg and "content" in msg for msg in history)

def test_get_conversation_history_with_messages(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi!")
    manager.add_user_message("How are you?")
    
    history = manager.get_conversation_history()
    assert len(history) == 4  # System + 3 messages
    assert [msg["role"] for msg in history[1:]] == ["user", "assistant", "user"]
    assert [msg["content"] for msg in history[1:]] == ["Hello", "Hi!", "How are you?"]

def test_clear_history(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi!")
    manager.clear_history()
    
    history = manager.get_conversation_history()
    assert len(history) == 1
    assert history[0]["role"] == "system"

def test_get_last_user_message_none(manager):
    assert manager.get_last_user_message() is None

def test_get_last_user_message(manager):
    manager.add_user_message("First")
    manager.add_assistant_message("Response")
    manager.add_user_message("Second")
    
    assert manager.get_last_user_message() == "Second"

def test_get_last_assistant_message_none(manager):
    assert manager.get_last_assistant_message() is None

def test_get_last_assistant_message(manager):
    manager.add_user_message("Hello")
    manager.add_assistant_message("First response")
    manager.add_user_message("Question")
    manager.add_assistant_message("Second response")
    
    assert manager.get_last_assistant_message() == "Second response"

def test_conversation_flow(manager):
    # Test a typical conversation flow
    manager.add_user_message("Hello")
    manager.add_assistant_message("Hi! How can I help?")
    manager.add_user_message("What's the weather?")
    manager.add_assistant_message("I'm not able to check the weather.")
    
    history = manager.get_conversation_history()
    assert len(history) == 5  # System + 4 messages
    assert manager.get_last_user_message() == "What's the weather?"
    assert manager.get_last_assistant_message() == "I'm not able to check the weather."
