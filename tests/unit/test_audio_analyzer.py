import numpy as np
import pytest
from dataclasses import dataclass
from src.audio.analyzer import calculate_rms, analyze_frequency_components, is_speech

@dataclass
class TestAudioConfig:
    format: int | None
    channels: int
    sample_rate: int
    chunk_size: int
    input_device_index: int

@pytest.fixture
def audio_config():
    return TestAudioConfig(
        format=None,  # Not needed for these tests
        channels=1,
        sample_rate=16000,
        chunk_size=1024,
        input_device_index=0
    )

def test_calculate_rms():
    # Test with silence (zeros)
    silent_data = np.zeros(1000, dtype=np.int16)
    assert calculate_rms(silent_data) == 0.0
    
    # Test with constant amplitude
    constant_data = np.full(1000, 1000, dtype=np.int16)
    expected_rms = 1000.0
    assert abs(calculate_rms(constant_data) - expected_rms) < 0.1
    
    # Test with sine wave
    t = np.linspace(0, 1, 1000)
    amplitude = 1000
    sine_data = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
    # RMS of a sine wave should be amplitude/√2
    expected_rms = amplitude / np.sqrt(2)
    assert abs(calculate_rms(sine_data) - expected_rms) < 1.0

def test_analyze_frequency_components():
    # Create a test signal with known frequency components
    sample_rate = 16000
    duration = 0.1  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Generate a 440 Hz sine wave
    test_freq = 440
    test_data = np.sin(2 * np.pi * test_freq * t).astype(np.float64)
    
    avg_magnitude, peak_freq, freq_variation = analyze_frequency_components(test_data, sample_rate)
    
    # Test if peak frequency is close to our input frequency
    assert abs(peak_freq - test_freq) < 10  # Allow 10 Hz tolerance
    
    # Test if we have some magnitude
    assert avg_magnitude > 0
    
    # Test if frequency variation is reasonable
    assert freq_variation >= 0

def test_is_speech(audio_config):
    # Test silence (should not be detected as speech)
    silent_data = np.zeros(1024, dtype=np.int16).tobytes()
    assert not is_speech(silent_data, audio_config)
    
    # Test pure tone (should not be detected as speech)
    t = np.linspace(0, 1, 1024)
    pure_tone = (32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16).tobytes()
    assert not is_speech(pure_tone, audio_config)
    
    # Test speech-like signal
    # Create a complex signal with frequencies in speech range (100-3000 Hz)
    t = np.linspace(0, 1, 1024)
    speech_freqs = [300, 1000, 2000]
    speech_like = np.zeros_like(t)
    for freq in speech_freqs:
        speech_like += np.sin(2 * np.pi * freq * t)
    speech_like = (32767 * speech_like / np.max(np.abs(speech_like))).astype(np.int16).tobytes()
    
    assert is_speech(speech_like, audio_config)

def test_is_speech_threshold(audio_config):
    # Test with different amplitude thresholds
    t = np.linspace(0, 1, 1024)
    speech_freqs = [300, 1000, 2000]
    speech_like = np.zeros_like(t)
    for freq in speech_freqs:
        speech_like += np.sin(2 * np.pi * freq * t)
    
    # Test with very low amplitude (should not be speech)
    quiet_speech = (100 * speech_like).astype(np.int16).tobytes()
    assert not is_speech(quiet_speech, audio_config, threshold=500)
    
    # Test with high amplitude (should be speech)
    loud_speech = (10000 * speech_like).astype(np.int16).tobytes()
    assert is_speech(loud_speech, audio_config, threshold=500) 