import pytest
from unittest.mock import Mock, patch, mock_open
from src.conversation.openai_client import OpenAIWrapper, ChatConfig, TTSConfig

@pytest.fixture
def mock_openai_client():
    return Mock()

@pytest.fixture
def openai_wrapper(mock_openai_client):
    return OpenAIWrapper(mock_openai_client)

def test_init_with_default_configs():
    client = Mock()
    wrapper = OpenAIWrapper(client)
    assert wrapper.chat_config.model == "gpt-4-turbo"
    assert wrapper.chat_config.max_completion_tokens == 150
    assert wrapper.chat_config.temperature == 0.7
    assert wrapper.tts_config.model == "tts-1"
    assert wrapper.tts_config.voice == "nova"

def test_init_with_custom_configs():
    client = Mock()
    chat_config = ChatConfig(model="gpt-3.5-turbo", max_completion_tokens=100, temperature=0.5)
    tts_config = TTSConfig(model="tts-2", voice="alloy")
    wrapper = OpenAIWrapper(client, chat_config, tts_config)
    assert wrapper.chat_config == chat_config
    assert wrapper.tts_config == tts_config

def test_get_chat_completion_success(openai_wrapper, mock_openai_client):
    # Setup mock response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_openai_client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "Hello"}]
    response = openai_wrapper.get_chat_completion(messages)

    assert response == "Test response"
    mock_openai_client.chat.completions.create.assert_called_once_with(
        model=openai_wrapper.chat_config.model,
        messages=messages,
        max_completion_tokens=openai_wrapper.chat_config.max_completion_tokens,
        temperature=openai_wrapper.chat_config.temperature
    )

def test_get_chat_completion_failure(openai_wrapper, mock_openai_client):
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
    messages = [{"role": "user", "content": "Hello"}]
    response = openai_wrapper.get_chat_completion(messages)
    assert response is None

def test_text_to_speech_success(openai_wrapper, mock_openai_client):
    # Setup mock response
    mock_response = Mock()
    mock_audio_data = b"mock audio data"
    mock_response.read.return_value = mock_audio_data
    mock_openai_client.audio.speech.create.return_value = mock_response

    with patch("builtins.open", mock_open()) as mock_file:
        audio_data = openai_wrapper.text_to_speech("Hello", "test.mp3")

    assert audio_data == mock_audio_data
    mock_openai_client.audio.speech.create.assert_called_once_with(
        model=openai_wrapper.tts_config.model,
        voice=openai_wrapper.tts_config.voice,
        input="Hello",
        speed=1.2,
        response_format="mp3"
    )
    mock_file.assert_called_once_with("test.mp3", "wb")
    mock_file().write.assert_called_once_with(mock_audio_data)

def test_text_to_speech_empty_text(openai_wrapper):
    audio_data = openai_wrapper.text_to_speech("")
    assert audio_data is None

def test_text_to_speech_failure(openai_wrapper, mock_openai_client):
    mock_openai_client.audio.speech.create.side_effect = Exception("API Error")
    audio_data = openai_wrapper.text_to_speech("Hello")
    assert audio_data is None

def test_transcribe_audio_success(openai_wrapper, mock_openai_client):
    mock_openai_client.audio.transcriptions.create.return_value = "Transcribed text"
    
    with patch("builtins.open", mock_open(read_data=b"audio data")):
        transcript = openai_wrapper.transcribe_audio("test.mp3")

    assert transcript == "Transcribed text"
    mock_openai_client.audio.transcriptions.create.assert_called_once_with(
        model="whisper-1",
        file=mock_openai_client.audio.transcriptions.create.call_args[1]['file'],
        language="en",
        response_format="text",
        temperature=0.2
    )

def test_transcribe_audio_failure(openai_wrapper, mock_openai_client):
    mock_openai_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    with patch("builtins.open", mock_open(read_data=b"audio data")):
        transcript = openai_wrapper.transcribe_audio("test.mp3")
    
    assert transcript is None
