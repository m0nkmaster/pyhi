import pyaudio
from typing import Optional
import os

def find_input_device() -> Optional[int]:
    """Find the best available input device for Mac."""
    p = pyaudio.PyAudio()
    
    print("\nSearching for input devices...")
    print("-" * 50)
    
    # First, try to find MacBook Pro Microphone
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:
            name = dev_info.get('name', '').lower()
            print("Found device {}: {}".format(i, name))
            print("    Input channels:", dev_info.get('maxInputChannels'))
            print("    Sample rate:", dev_info.get('defaultSampleRate'))
            print("    Is default input:", p.get_default_input_device_info().get('index') == i)
            
            # Skip virtual audio devices
            if any(x in name for x in ['blackhole', 'virtual', 'loopback', 'microsoft teams']):
                print("    SKIPPED: Virtual device detected")
                continue
            
            # Look specifically for MacBook Pro Microphone
            if 'macbook pro microphone' in name:
                print("    SELECTED: MacBook Pro Microphone found")
                p.terminate()
                return i
    
    print("\nNo MacBook Pro Microphone found, trying built-in mics...")
    
    # Try built-in mics
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        name = dev_info.get('name', '').lower()
        if dev_info.get('maxInputChannels') > 0:
            print("Checking device {}: {}".format(i, name))
            
            # Skip virtual devices
            if any(x in name for x in ['blackhole', 'virtual', 'loopback', 'microsoft teams']):
                print("    SKIPPED: Virtual device")
                continue
                
            # Look for built-in keywords
            if any(x in name for x in ['built-in', 'macbook', 'internal']):
                print("    SELECTED: Built-in microphone found")
                p.terminate()
                return i
    
    print("\nNo built-in mics found, checking default device...")
    
    # Try default input device
    try:
        default_device = p.get_default_input_device_info()
        if default_device:
            name = default_device.get('name', '').lower()
            print("Default device:", name)
            if not any(x in name for x in ['blackhole', 'virtual', 'loopback', 'microsoft teams']):
                print("    SELECTED: Using default input device")
                p.terminate()
                return default_device.get('index')
            else:
                print("    SKIPPED: Default device is virtual")
    except IOError:
        print("No default input device found")

    print("No suitable input device found!")
    p.terminate()
    return None

def setup_audio_stream(config, callback=None):
    """Setup audio stream with proper error handling."""
    p = pyaudio.PyAudio()
    
    # Always try to find the MacBook Pro Microphone first
    macbook_mic_index = None
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        name = dev_info.get('name', '').lower()
        if 'macbook pro microphone' in name:
            macbook_mic_index = i
            break
    
    if macbook_mic_index is not None:
        print("Found MacBook Pro Microphone, forcing selection...")
        config.input_device_index = macbook_mic_index
    
    # If no input device specified, try to find one
    if config.input_device_index is None:
        print("\nNo input device specified, searching for suitable device...")
        config.input_device_index = find_input_device()
        
    if config.input_device_index is None:
        raise RuntimeError("No suitable audio input device found")
    
    # Double-check the selected device
    dev_info = p.get_device_info_by_index(config.input_device_index)
    name = dev_info.get('name', '').lower()
    print("\nSelected device:", name)
    print("Index:", config.input_device_index)
    
    # Force reselection if a virtual device was somehow selected
    if any(x in name for x in ['blackhole', 'virtual', 'loopback', 'microsoft teams']):
        print("WARNING: Virtual device was selected. Forcing reselection...")
        config.input_device_index = find_input_device()
        if config.input_device_index is None:
            raise RuntimeError("No suitable physical microphone found")
        
        # Verify the new selection
        dev_info = p.get_device_info_by_index(config.input_device_index)
        print("Reselected device:", dev_info.get('name'))
    
    try:
        stream = p.open(
            format=config.format,
            channels=config.channels,
            rate=config.sample_rate,
            input=True,
            input_device_index=config.input_device_index,
            frames_per_buffer=config.chunk_size,
            stream_callback=callback if callback else None
        )
        return p, stream
    except Exception as e:
        print("Error opening stream:", str(e))
        p.terminate()
        raise