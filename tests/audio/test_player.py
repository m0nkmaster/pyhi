import pytest
import platform
import subprocess
from unittest.mock import patch, MagicMock
from src.audio.player import SystemAudioPlayer, AudioPlayerError
from src.config import AudioPlayerConfig

@pytest.fixture
def audio_config():
    return AudioPlayerConfig(
        temp_file="test_temp.mp3",
        activation_sound_path="test_bing.mp3",
        output_device="default"
    )

@pytest.fixture
def sample_audio():
    return b"dummy audio data"

def test_init_unsupported_platform():
    with patch('platform.system', return_value='InvalidOS'):
        with pytest.raises(AudioPlayerError, match="Unsupported platform"):
            SystemAudioPlayer()

@pytest.mark.parametrize("os_name", ['Darwin', 'Windows'])
def test_init_supported_platforms(os_name):
    with patch('platform.system', return_value=os_name):
        player = SystemAudioPlayer()
        assert player._platform == os_name.lower()

def test_init_linux_without_mpg123():
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'which')):
            with pytest.raises(AudioPlayerError, match="mpg123 not found"):
                SystemAudioPlayer()

def test_init_linux_with_mpg123():
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run', return_value=MagicMock()):
            player = SystemAudioPlayer()
            assert player._platform == 'linux'

def test_play_darwin(audio_config, sample_audio):
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run') as mock_run:
            with patch('os.remove') as mock_remove:
                player = SystemAudioPlayer(config=audio_config)
                player.play(sample_audio)
                
                # Check if afplay was called with correct arguments
                mock_run.assert_called_once_with(
                    ['afplay', '-v', '0.5', audio_config.temp_file],
                    check=True
                )
                # Check if temp file was cleaned up
                mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_linux(audio_config, sample_audio):
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run') as mock_run:
            with patch('os.remove') as mock_remove:
                player = SystemAudioPlayer(config=audio_config)
                player.play(sample_audio)
                
                # Check if mpg123 was called with correct arguments
                mock_run.assert_called_with(
                    ['mpg123', '-q', '-a', audio_config.output_device, audio_config.temp_file],
                    check=True
                )
                # Check if temp file was cleaned up
                mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_windows(audio_config, sample_audio):
    with patch('platform.system', return_value='Windows'):
        with patch('subprocess.run') as mock_run:
            with patch('os.remove') as mock_remove:
                player = SystemAudioPlayer(config=audio_config)
                player.play(sample_audio)
                
                # Check if PowerShell was called with correct arguments
                ps_command = f'(New-Object Media.SoundPlayer "{audio_config.temp_file}").PlaySync()'
                mock_run.assert_called_with(
                    ['powershell', '-c', ps_command],
                    check=True
                )
                # Check if temp file was cleaned up
                mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_with_error(audio_config, sample_audio):
    error_callback = MagicMock()
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'afplay')):
            with patch('os.remove') as mock_remove:
                player = SystemAudioPlayer(on_error=error_callback, config=audio_config)
                
                with pytest.raises(AudioPlayerError, match="Failed to play audio"):
                    player.play(sample_audio)
                
                # Check if error callback was called
                assert error_callback.called
                # Check if temp file was cleaned up even after error
                mock_remove.assert_called_once_with(audio_config.temp_file)

def test_cleanup_on_file_write_error(audio_config, sample_audio):
    with patch('platform.system', return_value='Darwin'):
        with patch('builtins.open', side_effect=IOError("Failed to write file")):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(config=audio_config)
                    
                    with pytest.raises(AudioPlayerError, match="Failed to play audio"):
                        player.play(sample_audio)
                    
                    # Check if temp file was cleaned up after write error
                    mock_remove.assert_called_once_with(audio_config.temp_file)
