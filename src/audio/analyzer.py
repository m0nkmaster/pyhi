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

def is_speech(audio_bytes: bytes, config: AudioConfig) -> bool:
    """
    Determine if the audio frame contains speech-like characteristics.
    
    Args:
        audio_bytes: Raw audio data in bytes
        config: Audio configuration parameters containing speech detection settings
    
    Returns:
        bool: True if speech is detected, False otherwise
    """
    # Convert bytes to numpy array
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
    
    # Get speech detection config for cleaner code
    speech_config = config.speech_config
    threshold = speech_config.base_threshold
    
    # Calculate audio characteristics
    rms = calculate_rms(audio_data)
    avg_magnitude, peak_freq, freq_variation = analyze_frequency_components(
        audio_data, 
        config.sample_rate
    )
    
    # Define speech characteristics with configured thresholds
    is_loud_enough = rms > threshold * speech_config.loudness_multiplier
    has_speech_frequencies = (speech_config.min_speech_freq < peak_freq < 
                            speech_config.max_speech_freq)
    has_sufficient_variation = freq_variation > threshold/speech_config.variation_divisor
    
    # Magnitude check using configured values
    background_noise_level = threshold * speech_config.background_noise_multiplier
    signal_to_noise = avg_magnitude / background_noise_level if background_noise_level > 0 else 0
    has_sufficient_magnitude = signal_to_noise > speech_config.signal_to_noise_threshold
    
    # Energy distribution check using configured values
    has_valid_energy_distribution = (
        avg_magnitude > threshold * speech_config.magnitude_multiplier and
        freq_variation > threshold * speech_config.variation_multiplier and
        rms > threshold * speech_config.rms_multiplier
    )
    
    if config.device_config.debug_audio and (is_loud_enough and has_speech_frequencies and 
            has_sufficient_variation and has_sufficient_magnitude and has_valid_energy_distribution):
        print(f"\rSpeech detected - RMS: {rms:.1f}, Freq: {peak_freq:.1f}Hz, "
              f"Var: {freq_variation:.1f}, Mag: {avg_magnitude:.1f}, S/N: {signal_to_noise:.1f}", 
              end="", flush=True)
    
    return (is_loud_enough and has_speech_frequencies and has_sufficient_variation and 
            has_sufficient_magnitude and has_valid_energy_distribution)