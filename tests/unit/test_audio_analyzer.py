import numpy as np
import pytest
from src.audio.analyzer import calculate_rms, analyze_frequency_components, is_speech
from src.utils.types import AudioConfig

@pytest.fixture
def audio_config():
    return AudioConfig(
        sample_rate=44100,
        channels=1,
        chunk_size=1024,
        format=8  # pyaudio.paInt16
    )

def test_calculate_rms():
    # Test with known values
    audio_data = np.array([1, -1, 2, -2], dtype=np.int16)
    rms = calculate_rms(audio_data)
    assert rms == pytest.approx(1.5811388300841898)  # sqrt(mean([1, 1, 4, 4]))

def test_analyze_frequency_components():
    # Create a simple sine wave at 1000Hz
    duration = 0.1  # seconds
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 1000
    audio_data = np.sin(2 * np.pi * frequency * t)
    audio_data = (audio_data * 32767).astype(np.int16)
    
    avg_magnitude, peak_freq, freq_variation = analyze_frequency_components(audio_data, sample_rate)
    
    # The peak frequency should be close to 1000Hz
    assert 900 < peak_freq < 1100
    assert avg_magnitude > 0
    assert freq_variation > 0

def test_is_speech(audio_config):
    # Create a test signal that should be detected as speech
    duration = 0.1
    sample_rate = audio_config.sample_rate
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Combine multiple frequencies typical in speech (e.g., 200Hz and 1000Hz)
    audio_data = np.sin(2 * np.pi * 200 * t) + 0.5 * np.sin(2 * np.pi * 1000 * t)
    audio_data = (audio_data * 32767).astype(np.int16)  # Convert to 16-bit PCM
    
    # Test with a strong signal
    result = is_speech(audio_data.tobytes(), audio_config, threshold=100)
    assert result is True
    
    # Test with a very weak signal
    weak_signal = (audio_data * 0.1).astype(np.int16)
    result = is_speech(weak_signal.tobytes(), audio_config, threshold=500)
    assert result is False

def test_is_speech_with_noise(audio_config):
    # Create random noise
    duration = 0.1
    sample_rate = audio_config.sample_rate
    noise = np.random.normal(0, 100, int(sample_rate * duration)).astype(np.int16)
    
    # Test with pure noise
    result = is_speech(noise.tobytes(), audio_config, threshold=500)
    assert result is False 