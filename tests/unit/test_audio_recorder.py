import pytest
import numpy as np
import pyaudio
from src.utils.types import AudioConfig

def test_list_audio_devices():
    """
    This is a debug test to list all available audio devices.
    Run this with: pytest tests/unit/test_audio_recorder.py -v -s
    """
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("\nAudio Devices Found:")
    print("-" * 50)
    
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_index(i)
        if device_info.get('maxInputChannels') > 0:  # Only input devices
            print(f"Input Device id {i} - {device_info.get('name')}")
            print(f"    Input channels: {device_info.get('maxInputChannels')}")
            print(f"    Default sample rate: {device_info.get('defaultSampleRate')}")
            print()
    
    p.terminate()
    assert True  # This test is for debugging only 