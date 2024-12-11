import numpy as np
from ..utils.types import AudioConfig
import speech_recognition as sr
import logging

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
    Detect if audio data contains speech using the SpeechRecognition library.
    """
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_bytes) as source:
        audio = recognizer.record(source)
    try:
        recognizer.recognize_google(audio)
        return True
    except sr.UnknownValueError:
        return False
    except sr.RequestError as e:
        logging.error(f"Could not request results from Google Speech Recognition service; {e}")
        return False