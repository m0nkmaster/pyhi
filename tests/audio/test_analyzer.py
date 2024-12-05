import pytest
import numpy as np
import pyaudio
from src.audio.analyzer import calculate_rms, analyze_frequency_components, is_speech
from src.config import AudioConfig

@pytest.fixture
def sample_audio_data():
    # Create a simple sine wave at 440Hz (A4 note) for testing
    duration = 0.1  # seconds
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)

@pytest.fixture
def audio_config():
    return AudioConfig(
        sample_rate=44100,
        channels=1,
        chunk_size=1024,
        format=pyaudio.paInt16
    )

def test_calculate_rms():
    # Test with known values
    test_data = np.array([1, -1, 2, -2, 3, -3])
    expected_rms = np.sqrt(28/6)  # sqrt(mean([1, 1, 4, 4, 9, 9]))
    assert np.isclose(calculate_rms(test_data), expected_rms)
    
    # Test with zeros
    assert calculate_rms(np.zeros(10)) == 0.0
    
    # Test with ones
    assert calculate_rms(np.ones(10)) == 1.0

def test_analyze_frequency_components(sample_audio_data):
    sample_rate = 44100
    avg_magnitude, peak_freq, freq_variation = analyze_frequency_components(
        sample_audio_data, sample_rate
    )
    
    # Check if peak frequency is close to 440Hz (allowing some deviation due to FFT resolution)
    assert 400 < peak_freq < 480
    
    # Basic sanity checks
    assert avg_magnitude > 0
    assert freq_variation >= 0

def test_is_speech():
    # Create a synthetic speech-like signal
    duration = 0.1
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Combine multiple frequencies typical in speech (e.g., 200Hz and 1000Hz)
    signal = 5000 * (np.sin(2 * np.pi * 200 * t) + 0.5 * np.sin(2 * np.pi * 1000 * t))
    
    # Convert to int16 and then to bytes
    audio_bytes = signal.astype(np.int16).tobytes()
    
    config = AudioConfig(
        sample_rate=sample_rate,
        channels=1,
        chunk_size=len(signal),
        format=pyaudio.paInt16
    )
    
    # Test with default threshold
    assert is_speech(audio_bytes, config)
    
    # Test with very high threshold (should not detect speech)
    assert not is_speech(audio_bytes, config, threshold=10000)
    
    # Test with silence (zeros)
    silence = np.zeros(int(sample_rate * duration), dtype=np.int16).tobytes()
    assert not is_speech(silence, config)
