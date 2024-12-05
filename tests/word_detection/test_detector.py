import pytest
from unittest.mock import Mock, patch, MagicMock
import wave
import io
from src.word_detection.detector import WhisperWordDetector
from src.config import WordDetectionConfig, AudioConfig
from openai import OpenAI

@pytest.fixture
def mock_client():
    client = Mock(spec=OpenAI)
    # Set up the nested structure
    client.audio = Mock()
    client.audio.transcriptions = Mock()
    client.audio.transcriptions.create = Mock()
    return client

@pytest.fixture
def mock_audio_config():
    return AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_size=1024,
        format=8
    )

@pytest.fixture
def mock_config():
    return WordDetectionConfig(
        model="whisper-1",
        language="en",
        temperature=0.0,
        min_audio_size=1024
    )

@pytest.fixture
def detector(mock_client, mock_config, mock_audio_config):
    return WhisperWordDetector(
        client=mock_client,
        words=["hello", "hi there"],
        config=mock_config,
        audio_config=mock_audio_config
    )

def test_prepare_words():
    detector = WhisperWordDetector(
        client=Mock(),
        words=["Hello,", "Hi there.", "Test"]
    )
    prepared_words = detector.words
    
    # Check that words are cleaned and variations are added
    assert "hello" in prepared_words
    assert "hi there" in prepared_words
    assert "test" in prepared_words
    # Check variations without punctuation
    assert len(prepared_words) >= 3

def test_clean_text():
    detector = WhisperWordDetector(client=Mock(), words=[])
    
    # Test various text cleaning scenarios
    assert detector._clean_text("Hello,   World!") == "hello, world!"
    assert detector._clean_text("  Multiple    Spaces  ") == "multiple spaces"
    assert detector._clean_text("UPPERCASE") == "uppercase"

def test_calculate_similarity():
    detector = WhisperWordDetector(client=Mock(), words=[])
    
    # Test exact match
    assert detector._calculate_similarity("hello", "hello") == 1.0
    # Test similar strings
    assert detector._calculate_similarity("hello", "helo") > 0.8
    # Test different strings
    assert detector._calculate_similarity("hello", "world") < 0.5

def test_detect_with_small_audio():
    detector = WhisperWordDetector(
        client=Mock(),
        words=["hello"],
        config=WordDetectionConfig(min_audio_size=1000)
    )
    
    # Test with audio data smaller than minimum size
    result = detector.detect(b"small audio")
    assert result is False

def test_detect_with_valid_audio(detector, mock_client):
    # Create mock audio data
    audio_data = b"\x00" * 2048  # More than min_audio_size
    
    # Mock the transcription response
    mock_client.audio.transcriptions.create.return_value = "hello world"
    
    # Test detection
    result = detector.detect(audio_data)
    assert result is True
    
    # Verify API call
    mock_client.audio.transcriptions.create.assert_called_once()

def test_detect_with_no_match(detector, mock_client):
    # Create mock audio data
    audio_data = b"\x00" * 2048
    
    # Mock transcription with non-matching text
    mock_client.audio.transcriptions.create.return_value = "something else"
    
    # Test detection
    result = detector.detect(audio_data)
    assert result is False

def test_detect_with_similar_word(detector, mock_client):
    # Create mock audio data
    audio_data = b"\x00" * 2048
    
    # Mock transcription with similar text
    mock_client.audio.transcriptions.create.return_value = "hi their"  # Similar to "hi there"
    
    # Test detection
    result = detector.detect(audio_data)
    assert result is True

def test_detect_with_transcription_error(detector, mock_client):
    # Create mock audio data
    audio_data = b"\x00" * 2048
    
    # Mock transcription error
    mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    # Test detection
    result = detector.detect(audio_data)
    assert result is False

def test_detect_with_word_in_phrase(detector, mock_client):
    # Create mock audio data
    audio_data = b"\x00" * 2048
    
    # Mock transcription with word as part of longer phrase
    mock_client.audio.transcriptions.create.return_value = "I said hello to them"
    
    # Test detection
    result = detector.detect(audio_data)
    assert result is True

def test_transcribe_audio_success(detector, mock_client):
    # Create mock audio data
    audio_buffer = io.BytesIO()
    
    # Mock successful transcription
    mock_client.audio.transcriptions.create.return_value = "test transcript"
    
    # Test transcription
    result = detector._transcribe_audio(audio_buffer)
    assert result == "test transcript"

def test_transcribe_audio_error(detector, mock_client):
    # Create mock audio data
    audio_buffer = io.BytesIO()
    
    # Mock transcription error
    mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
    
    # Test transcription
    result = detector._transcribe_audio(audio_buffer)
    assert result is None

def test_detect_with_wave_error(detector):
    # Create mock audio data
    audio_data = b"\x00" * 2048
    
    # Mock wave.open to raise an error
    with patch('wave.open', side_effect=Exception("Wave error")):
        # Test detection
        result = detector.detect(audio_data)
        assert result is False
