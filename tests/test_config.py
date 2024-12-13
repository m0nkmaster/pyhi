import pytest
from src.config import AudioDeviceConfig

def test_audio_device_config_default_values():
    """Test that AudioDeviceConfig initializes with correct default values"""
    config = AudioDeviceConfig()
    
    assert config.auto_select_device is True
    assert config.preferred_input_device_name is None
    assert config.preferred_output_device_name is None
    assert config.excluded_device_names == ["BlackHole", "ZoomAudioDevice"]
    assert config.fallback_to_default is True
    assert config.buffer_size_ms == 50
    assert config.retry_on_error is True
    assert config.max_retries == 3
    assert config.list_devices_on_start is True
    assert config.debug_audio is False

def test_audio_device_config_custom_values():
    """Test that AudioDeviceConfig accepts and sets custom values"""
    config = AudioDeviceConfig(
        auto_select_device=False,
        preferred_input_device_name="Test Input",
        preferred_output_device_name="Test Output",
        excluded_device_names=["TestDevice"],
        fallback_to_default=False,
        buffer_size_ms=100,
        retry_on_error=False,
        max_retries=5,
        list_devices_on_start=False,
        debug_audio=True
    )
    
    assert config.auto_select_device is False
    assert config.preferred_input_device_name == "Test Input"
    assert config.preferred_output_device_name == "Test Output"
    assert config.excluded_device_names == ["TestDevice"]
    assert config.fallback_to_default is False
    assert config.buffer_size_ms == 100
    assert config.retry_on_error is False
    assert config.max_retries == 5
    assert config.list_devices_on_start is False
    assert config.debug_audio is True
