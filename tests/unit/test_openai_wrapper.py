import pytest
from unittest.mock import Mock, patch, mock_open
from src.conversation.openai_client import OpenAIWrapper, ChatConfig, TTSConfig

@pytest.fixture
def mock_openai_client():
    client = Mock()
    
    # Mock chat completion response
    completion_response = Mock()
    completion_response.choices = [Mock(message=Mock(content="Test response"))]
    client.chat.completions.create.return_value = completion_response
    
    # Mock TTS response
    tts_response = Mock()
    tts_response.stream_to_file = Mock()
    client.audio.speech.with_streaming_response.create.return_value = tts_response
    
    # Mock transcription response
    client.audio.transcriptions.create.return_value = "Transcribed text"
    
    return client

@pytest.fixture
def wrapper(mock_openai_client):
    return OpenAIWrapper(
        client=mock_openai_client,
        chat_config=ChatConfig(model="test-model", max_tokens=100, temperature=0.5),
        tts_config=TTSConfig(model="test-tts", voice="test-voice")
    )

def test_initialization(wrapper):
    assert wrapper.chat_config.model == "test-model"
    assert wrapper.chat_config.max_tokens == 100
    assert wrapper.chat_config.temperature == 0.5
    assert wrapper.tts_config.model == "test-tts"
    assert wrapper.tts_config.voice == "test-voice"

def test_initialization_defaults():
    wrapper = OpenAIWrapper(Mock())
    assert wrapper.chat_config.model == "gpt-3.5-turbo"
    assert wrapper.tts_config.voice == "nova"

def test_get_chat_completion(wrapper, mock_openai_client):
    messages = [{"role": "user", "content": "Hello"}]
    response = wrapper.get_chat_completion(messages)
    
    assert response == "Test response"
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=messages,
        max_tokens=100,
        temperature=0.5
    )

def test_get_chat_completion_error(wrapper, mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    
    messages = [{"role": "user", "content": "Hello"}]
    response = wrapper.get_chat_completion(messages)
    
    assert response is None

def test_text_to_speech(wrapper, mock_openai_client):
    result = wrapper.text_to_speech("Hello", "test.mp3")
    
    assert result is True
    mock_openai_client.audio.speech.with_streaming_response.create.assert_called_once_with(
        model="test-tts",
        voice="test-voice",
        input="Hello"
    )

def test_text_to_speech_empty_text(wrapper, mock_openai_client):
    result = wrapper.text_to_speech("")
    
    assert result is False
    mock_openai_client.audio.speech.with_streaming_response.create.assert_not_called()

def test_text_to_speech_error(wrapper, mock_openai_client):
    mock_openai_client.audio.speech.with_streaming_response.create.side_effect = Exception("API Error")
    
    result = wrapper.text_to_speech("Hello")
    
    assert result is False

@patch("builtins.open", new_callable=mock_open, read_data=b"test audio data")
def test_transcribe_audio(mock_file, wrapper, mock_openai_client):
    transcript = wrapper.transcribe_audio("test.wav")
    
    assert transcript == "Transcribed text"
    mock_openai_client.audio.transcriptions.create.assert_called_once_with(
        model="whisper-1",
        file=mock_file.return_value,
        language="en",
        response_format="text",
        temperature=0.2
    )

@patch("builtins.open", new_callable=mock_open, read_data=b"test audio data")
def test_transcribe_audio_error(mock_file, wrapper, mock_openai_client):
    mock_openai_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    transcript = wrapper.transcribe_audio("test.wav")
    
    assert transcript is None 