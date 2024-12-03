import pytest
import platform
import subprocess
from unittest.mock import Mock, patch
import numpy as np
from src.audio.player import SystemAudioPlayer, BeepGenerator, AudioPlayerError

@pytest.fixture
def audio_player():
    return SystemAudioPlayer()

@pytest.fixture
def mock_platform():
    with patch('platform.system') as mock_sys:
        mock_sys.return_value = 'Darwin'
        yield mock_sys

@pytest.fixture
def mock_subprocess():
    with patch('subprocess.run') as mock_run:
        yield mock_run

def test_initialization_supported_platform(mock_platform):
    player = SystemAudioPlayer()
    assert player._platform == 'darwin'

def test_initialization_unsupported_platform():
    with patch('platform.system', return_value='Unknown'):
        with pytest.raises(AudioPlayerError, match="Unsupported platform"):
            SystemAudioPlayer()

def test_play_audio_macos(audio_player, mock_subprocess):
    audio_data = b'dummy_audio_data'
    
    with patch('wave.open') as mock_wave:
        mock_wave.return_value.__enter__.return_value = Mock()
        audio_player.play(audio_data)
    
    mock_subprocess.assert_called_once_with(['afplay', 'temp_playback.wav'], check=True)

def test_play_audio_linux(mock_subprocess):
    with patch('platform.system', return_value='Linux'):
        player = SystemAudioPlayer()
        audio_data = b'dummy_audio_data'
        
        with patch('wave.open') as mock_wave:
            mock_wave.return_value.__enter__.return_value = Mock()
            player.play(audio_data)
        
        mock_subprocess.assert_called_once_with(['aplay', 'temp_playback.wav'], check=True)

def test_play_audio_windows(mock_subprocess):
    with patch('platform.system', return_value='Windows'):
        player = SystemAudioPlayer()
        audio_data = b'dummy_audio_data'
        
        with patch('wave.open') as mock_wave:
            mock_wave.return_value.__enter__.return_value = Mock()
            player.play(audio_data)
        
        mock_subprocess.assert_called_once_with(
            ['powershell', '-c', '(New-Object Media.SoundPlayer "temp_playback.wav").PlaySync()'],
            check=True
        )

def test_play_audio_error(audio_player, mock_subprocess):
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'afplay')
    
    with patch('wave.open') as mock_wave:
        mock_wave.return_value.__enter__.return_value = Mock()
        with pytest.raises(AudioPlayerError, match="Failed to play audio"):
            audio_player.play(b'dummy_audio_data')

def test_error_callback():
    mock_callback = Mock()
    player = SystemAudioPlayer(on_error=mock_callback)
    
    with patch('wave.open') as mock_wave:
        mock_wave.side_effect = Exception("Test error")
        with pytest.raises(AudioPlayerError):
            player.play(b'dummy_audio_data')
    
    mock_callback.assert_called_once()

def test_beep_generator():
    beep = BeepGenerator.generate_beep(
        duration=0.1,
        frequency=440,
        sample_rate=44100
    )
    
    # Convert bytes back to numpy array for testing
    samples = np.frombuffer(beep, dtype=np.int16)
    
    # Check basic properties
    assert len(samples) == int(0.1 * 44100)  # Duration * sample_rate
    assert samples.dtype == np.int16
    assert np.abs(samples).max() <= 32767  # Max value for 16-bit audio

def test_beep_generator_fade():
    beep = BeepGenerator.generate_beep(
        duration=0.1,
        frequency=440,
        sample_rate=44100
    )
    samples = np.frombuffer(beep, dtype=np.int16)
    
    # Check fade in/out
    fade_samples = int(0.02 * 44100)  # 20ms fade
    assert abs(samples[0]) < abs(samples[fade_samples])  # Start is quieter
    assert abs(samples[-1]) < abs(samples[-fade_samples])  # End is quieter 