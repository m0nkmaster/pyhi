import pytest
import numpy as np
import pyaudio
from src.audio.analyzer import calculate_rms, analyze_frequency_components, is_speech
from src.config import AudioConfig, SpeechDetectionConfig

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
        format=pyaudio.paInt16,
        speech_config=SpeechDetectionConfig(
            base_threshold=500,  # Lower threshold for test
            loudness_multiplier=1.0,
            background_noise_multiplier=1.5,
            signal_to_noise_threshold=2.0,
            magnitude_multiplier=1.5,
            variation_multiplier=1.0,
            rms_multiplier=1.0
        )
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

def test_is_speech(audio_config):
    # Create a synthetic speech-like signal
    duration = 0.1
    sample_rate = audio_config.sample_rate
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a more complex signal with multiple frequencies typical of speech
    speech_like_signal = (
        np.sin(2 * np.pi * 150 * t) +  # Fundamental frequency
        0.5 * np.sin(2 * np.pi * 300 * t) +  # First harmonic
        0.25 * np.sin(2 * np.pi * 450 * t)   # Second harmonic
    )
    
    # Add some amplitude modulation to simulate speech patterns
    modulation = 1 + 0.5 * np.sin(2 * np.pi * 5 * t)
    speech_like_signal *= modulation
    
    # Scale to a significant amplitude (above base_threshold)
    speech_like_signal = speech_like_signal * 1000
    
    # Convert to bytes
    audio_bytes = speech_like_signal.astype(np.int16).tobytes()
    
    # Test with speech-like signal
    assert is_speech(audio_bytes, audio_config)
    
    # Test with silence (should return False)
    silence = np.zeros(int(sample_rate * duration), dtype=np.int16).tobytes()
    assert not is_speech(silence, audio_config)
    
    # Test with pure noise (should return False)
    noise = (np.random.random(int(sample_rate * duration)) * 100).astype(np.int16).tobytes()
    assert not is_speech(noise, audio_config)
