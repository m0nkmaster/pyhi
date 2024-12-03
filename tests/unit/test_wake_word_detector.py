import pytest
from unittest.mock import Mock, patch, mock_open
from src.wake_word.detector import WhisperWakeWordDetector

@pytest.fixture
def mock_openai_client():
    client = Mock()
    # Mock the nested structure of OpenAI client
    client.audio.transcriptions.create.return_value = "hey chat"
    return client

@pytest.fixture
def wake_words():
    return ["hey chat", "hi chat", "hello chat"]

@pytest.fixture
def detector(mock_openai_client, wake_words):
    return WhisperWakeWordDetector(
        client=mock_openai_client,
        wake_words=wake_words
    )

def test_initialization(detector, wake_words):
    assert all(word in detector.wake_words for word in wake_words)
    assert detector.temperature == 0.2
    assert detector.language == "en"

@patch("wave.open")
def test_detect_wake_word_success(mock_wave, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    # Test with matching wake word
    result = detector.detect(b"dummy_audio_data")
    
    assert result is True
    mock_openai_client.audio.transcriptions.create.assert_called_once()

@patch("wave.open")
def test_detect_wake_word_failure(mock_wave, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    # Mock transcription without wake word
    mock_openai_client.audio.transcriptions.create.return_value = "random speech"
    
    result = detector.detect(b"dummy_audio_data")
    
    assert result is False

@patch("wave.open")
def test_detect_wake_word_transcription_error(mock_wave, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    # Mock transcription error
    mock_openai_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    result = detector.detect(b"dummy_audio_data")
    
    assert result is False

@patch("wave.open")
def test_detect_wake_word_case_insensitive(mock_wave, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    # Test with different case
    mock_openai_client.audio.transcriptions.create.return_value = "HEY CHAT"
    
    result = detector.detect(b"dummy_audio_data")
    
    assert result is True

@patch("builtins.open", new_callable=mock_open, read_data=b"dummy_audio_data")
@patch("wave.open")
def test_transcribe_audio_success(mock_wave, mock_file, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    transcript = detector._transcribe_audio("dummy.wav")
    
    assert transcript == "hey chat"
    mock_openai_client.audio.transcriptions.create.assert_called_once_with(
        model="whisper-1",
        file=mock_file.return_value.__enter__.return_value,
        language="en",
        response_format="text",
        temperature=0.2
    )

@patch("builtins.open", new_callable=mock_open, read_data=b"dummy_audio_data")
@patch("wave.open")
def test_transcribe_audio_failure(mock_wave, mock_file, detector, mock_openai_client):
    # Mock wave file operations
    mock_wave.return_value.__enter__.return_value = Mock()
    
    # Mock API error
    mock_openai_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    transcript = detector._transcribe_audio("dummy.wav")
    
    assert transcript is None 