import pytest
import platform
import subprocess
from unittest.mock import patch, MagicMock, call
from src.audio.player import SystemAudioPlayer, AudioPlayerError, DeviceNotFoundError
from src.config import AudioPlayerConfig, AudioDeviceConfig

@pytest.fixture
def audio_config():
    return AudioPlayerConfig(
        temp_file="test_temp.mp3",
        activation_sound_path="test_bing.mp3",
        volume_level=1.0  # Match the default in config
    )

@pytest.fixture
def sample_audio():
    return b"dummy audio data"

@pytest.fixture
def mock_pyaudio(mocker):
    """Fixture for mocking PyAudio."""
    mock = mocker.patch('pyaudio.PyAudio').return_value
    
    # Configure mock device
    mock_info = {
        'name': 'Test Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 0,
        'defaultLowOutputLatency': 0.01
    }
    
    # Create a proper mock device that behaves like a dict
    mock_device = mocker.MagicMock(spec_set=dict)
    mock_device.__getitem__.side_effect = mock_info.__getitem__
    mock_device.get = mock_info.get
    
    # Set up the mock PyAudio instance
    mock.get_device_info_by_index.return_value = mock_device
    mock.get_default_output_device_info.return_value = mock_device
    mock.get_default_input_device_info.return_value = mock_device
    mock.get_device_count.return_value = 1
    
    return mock

@pytest.fixture
def mock_device_config():
    return AudioDeviceConfig(
        list_devices_on_start=False,  # Disable device listing for most tests
        auto_select_device=False,
        debug_audio=False
    )

def test_init_unsupported_platform():
    with patch('platform.system', return_value='InvalidOS'):
        with pytest.raises(AudioPlayerError, match="Unsupported platform"):
            SystemAudioPlayer()

@pytest.mark.parametrize("os_name", ['Darwin', 'Windows', 'Linux'])
def test_init_supported_platforms(os_name, mock_pyaudio):
    """Test initialization on supported platforms."""
    with patch('platform.system', return_value=os_name):
        if os_name == 'Linux':
            # Mock mpg123 check for Linux
            with patch('subprocess.run', return_value=MagicMock()):
                player = SystemAudioPlayer()
                assert player._platform == os_name.lower()
        else:
            player = SystemAudioPlayer()
            assert player._platform == os_name.lower()

def test_init_linux_without_mpg123():
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'which')):
            with pytest.raises(AudioPlayerError, match="mpg123 not found"):
                SystemAudioPlayer()

def test_init_linux_with_mpg123(mock_pyaudio):
    """Test Linux initialization with mpg123 available."""
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run', return_value=MagicMock()):
            player = SystemAudioPlayer()
            assert player._platform == 'linux'

def test_play_darwin(audio_config, sample_audio, mock_pyaudio, mock_device_config):
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=True):  # Ensure cleanup is attempted
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(config=audio_config, device_config=mock_device_config)
                    player.play(sample_audio)
                    
                    # Check if afplay was called with correct arguments
                    mock_run.assert_called_once_with(
                        ['afplay', '-v', '1.0', audio_config.temp_file],
                        check=True
                    )
                    # Check if temp file was cleaned up
                    mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_linux(audio_config, sample_audio, mock_pyaudio, mock_device_config):
    with patch('platform.system', return_value='Linux'):
        with patch('subprocess.run') as mock_run:
            # First call will be the 'which' check
            mock_run.return_value = MagicMock()
            
            with patch('os.path.exists', return_value=True):  # Ensure cleanup is attempted
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(config=audio_config, device_config=mock_device_config)
                    player.play(sample_audio)
                    
                    # Check if mpg123 was called with correct arguments
                    assert mock_run.call_count == 2  # Once for 'which', once for playing
                    assert mock_run.call_args_list[1] == call(
                        ['mpg123', '-q', audio_config.temp_file],
                        check=True
                    )
                    # Check if temp file was cleaned up
                    mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_windows(audio_config, sample_audio, mock_pyaudio, mock_device_config):
    with patch('platform.system', return_value='Windows'):
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=True):  # Ensure cleanup is attempted
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(config=audio_config, device_config=mock_device_config)
                    player.play(sample_audio)
                    
                    # Check if PowerShell was called with correct arguments
                    ps_command = f'(New-Object Media.SoundPlayer "{audio_config.temp_file}").PlaySync()'
                    mock_run.assert_called_once_with(
                        ['powershell', '-c', ps_command],
                        check=True
                    )
                    # Check if temp file was cleaned up
                    mock_remove.assert_called_once_with(audio_config.temp_file)

def test_play_with_error(audio_config, sample_audio, mock_pyaudio, mock_device_config):
    error_callback = MagicMock()
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'afplay')):
            with patch('os.path.exists', return_value=True):  # Ensure cleanup is attempted
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(on_error=error_callback, config=audio_config, device_config=mock_device_config)
                    
                    with pytest.raises(AudioPlayerError, match="Failed to play audio"):
                        player.play(sample_audio)
                    
                    # Check if error callback was called
                    assert error_callback.called
                    # Check if temp file was cleaned up even after error
                    mock_remove.assert_called_once_with(audio_config.temp_file)

def test_cleanup_on_file_write_error(audio_config, sample_audio, mock_pyaudio, mock_device_config):
    with patch('platform.system', return_value='Darwin'):
        with patch('builtins.open', side_effect=IOError("Failed to write file")):
            with patch('os.path.exists', return_value=False):  # File was never created
                with patch('os.remove') as mock_remove:
                    player = SystemAudioPlayer(config=audio_config, device_config=mock_device_config)
                    
                    with pytest.raises(AudioPlayerError, match="Failed to play audio"):
                        player.play(sample_audio)
                    
                    # File was never created, so remove should not be called
                    mock_remove.assert_not_called()

def test_play_audio_with_device(mock_pyaudio, tmp_path, mock_device_config):
    # Create a temporary audio file
    temp_file = tmp_path / "test_temp.mp3"
    temp_file.touch()
    
    # Configure mock device
    device_info = {
        'name': 'Test Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 1,
        'defaultLowOutputLatency': 0.01
    }
    mock_device = mock_pyaudio.MagicMock(spec_set=dict)
    mock_device.__getitem__.side_effect = device_info.__getitem__
    mock_device.get = device_info.get
    mock_pyaudio.get_device_info_by_index.return_value = mock_device
    mock_pyaudio.get_default_output_device_info.return_value = mock_device
    mock_pyaudio.get_device_count.return_value = 2
    
    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    player = SystemAudioPlayer(device_config=mock_device_config)
                    player.play(temp_file.read_bytes(), device='Test Device')
                    
                    mock_run.assert_called_once()

def test_play_audio_with_volume(mock_pyaudio, tmp_path, mock_device_config):
    # Create a temporary audio file
    temp_file = tmp_path / "test_temp.mp3"
    temp_file.touch()
    
    config = AudioPlayerConfig(
        temp_file=str(temp_file),
        volume_level=1.0
    )

    with patch('platform.system', return_value='Darwin'):
        with patch('subprocess.run') as mock_run:
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    player = SystemAudioPlayer(config=config, device_config=mock_device_config)
                    player.play(temp_file.read_bytes(), volume=0.5)

                    mock_run.assert_called_once_with(
                        ['afplay', '-v', '0.5', str(temp_file)],
                        check=True
                    )

def test_device_selection_preferred_device(mock_pyaudio, mocker):
    # Configure mock devices
    device_info_0 = {
        'name': 'Default Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 0,
        'defaultLowOutputLatency': 0.01
    }
    
    device_info_1 = {
        'name': 'Preferred Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 1,
        'defaultLowOutputLatency': 0.01
    }
    
    mock_device_0 = mocker.MagicMock(spec_set=dict)
    mock_device_0.__getitem__.side_effect = device_info_0.__getitem__
    mock_device_0.get = device_info_0.get
    mock_device_1 = mocker.MagicMock(spec_set=dict)
    mock_device_1.__getitem__.side_effect = device_info_1.__getitem__
    mock_device_1.get = device_info_1.get
    
    mock_pyaudio.get_device_count.return_value = 2
    mock_pyaudio.get_device_info_by_index.side_effect = lambda x: [mock_device_0, mock_device_1][x]
    mock_pyaudio.get_default_output_device_info.return_value = mock_device_0
    
    device_config = AudioDeviceConfig(
        preferred_output_device_name='Preferred Device',
        auto_select_device=True,
        list_devices_on_start=False  # Disable device listing for this test
    )
    
    player = SystemAudioPlayer(device_config=device_config)
    assert player.config.output_device_index == 1

def test_device_selection_fallback(mock_pyaudio):
    # Configure mock device
    device_info = {
        'name': 'Default Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 0,
        'defaultLowOutputLatency': 0.01
    }
    
    mock_device = mock_pyaudio.MagicMock(spec_set=dict)
    mock_device.__getitem__.side_effect = device_info.__getitem__
    mock_device.get = device_info.get
    mock_pyaudio.get_device_info_by_index.return_value = mock_device
    mock_pyaudio.get_default_output_device_info.return_value = mock_device
    mock_pyaudio.get_device_count.return_value = 1
    
    device_config = AudioDeviceConfig(
        preferred_output_device_name='NonExistent',
        fallback_to_default=True,
        auto_select_device=True,
        list_devices_on_start=False  # Disable device listing for this test
    )
    
    player = SystemAudioPlayer(device_config=device_config)
    assert player.config.output_device_index == 0

def test_device_selection_no_fallback(mock_pyaudio):
    # Configure mock device
    device_info = {
        'name': 'Default Device',
        'maxOutputChannels': 2,
        'maxInputChannels': 2,
        'defaultSampleRate': 44100,
        'index': 0,
        'defaultLowOutputLatency': 0.01
    }
    
    mock_device = mock_pyaudio.MagicMock(spec_set=dict)
    mock_device.__getitem__.side_effect = device_info.__getitem__
    mock_device.get = device_info.get
    mock_pyaudio.get_device_info_by_index.return_value = mock_device
    mock_pyaudio.get_device_count.return_value = 1
    
    device_config = AudioDeviceConfig(
        preferred_output_device_name='NonExistent',
        fallback_to_default=False,
        auto_select_device=True,
        list_devices_on_start=False  # Disable device listing for this test
    )
    
    with pytest.raises(DeviceNotFoundError, match="No suitable output device found"):
        SystemAudioPlayer(device_config=device_config)

def test_device_selection_invalid_device(mock_device_config):
    config = AudioPlayerConfig(output_device_index=999)
    device_config = AudioDeviceConfig(
        fallback_to_default=False,
        auto_select_device=True,
        list_devices_on_start=False  # Disable device listing for this test
    )
    
    with pytest.raises(DeviceNotFoundError):
        SystemAudioPlayer(config=config, device_config=device_config)
