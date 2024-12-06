import numpy as np
from ..utils.types import AudioConfig

def calculate_rms(audio_data: np.ndarray) -> float:
    """Calculate the Root Mean Square (RMS) amplitude of the audio data."""
    return np.sqrt(np.mean(np.square(np.abs(audio_data).astype(np.float64))))

def analyze_frequency_components(audio_data: np.ndarray, sample_rate: int) -> tuple[float, float, float]:
    """
    Analyze frequency components of the audio data.
    
    Returns:
        tuple: (average_magnitude, peak_frequency, frequency_variation)
    """
    fft = np.fft.fft(audio_data)
    frequencies = np.abs(fft)
    
    freq_bins = len(frequencies)
    speech_range_start = int(100 * freq_bins / sample_rate)
    speech_range_end = int(3000 * freq_bins / sample_rate)
    speech_frequencies = frequencies[speech_range_start:speech_range_end]
    
    avg_magnitude = np.mean(speech_frequencies)
    peak_idx = np.argmax(speech_frequencies) + speech_range_start
    peak_freq = peak_idx * sample_rate / freq_bins
    freq_variation = np.std(speech_frequencies)
    
    return avg_magnitude, peak_freq, freq_variation

def is_speech(audio_bytes: bytes, config: AudioConfig, threshold: int = 500) -> bool:
    """
    Determine if the audio frame contains speech-like characteristics.
    
    Args:
        audio_bytes: Raw audio data in bytes
        config: Audio configuration parameters
        threshold: Base amplitude threshold for speech detection
    
    Returns:
        bool: True if speech is detected, False otherwise
    """
    # Convert bytes to numpy array
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # Calculate audio characteristics
    rms = calculate_rms(audio_data)
    avg_magnitude, peak_freq, freq_variation = analyze_frequency_components(
        audio_data, 
        config.sample_rate
    )
    
    # Calculate adaptive threshold based on recent audio levels
    adaptive_threshold = max(threshold, rms * 0.75)  # Use at least 75% of current RMS
    
    # Define speech characteristics with adaptive thresholds
    is_loud_enough = rms > adaptive_threshold
    has_speech_frequencies = 100 < peak_freq < 3000
    has_sufficient_variation = freq_variation > adaptive_threshold/4
    
    if is_loud_enough and has_speech_frequencies and has_sufficient_variation:
        print(f"\rSpeech detected - RMS: {rms:.1f}, Peak Freq: {peak_freq:.1f}Hz, Variation: {freq_variation:.1f}", end="", flush=True)
    
    return is_loud_enough and has_speech_frequencies and has_sufficient_variation