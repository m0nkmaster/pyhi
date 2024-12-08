import pyaudio

def list_audio_devices():
    p = pyaudio.PyAudio()
    
    print("\nAudio Input Devices:")
    print("-" * 50)
    
    default_input = None
    try:
        default_input = p.get_default_input_device_info()
    except IOError:
        pass

    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:
            name = dev_info.get('name')
            is_default = default_input and default_input.get('index') == i
            print("Device {}: {}".format(i, name))
            print("    Channels: {}".format(dev_info.get('maxInputChannels')))
            print("    Sample Rate: {}".format(dev_info.get('defaultSampleRate')))
            print("    Default: {}".format('Yes' if is_default else 'No'))
            print()

    print("\nAudio Output Devices:")
    print("-" * 50)
    
    default_output = None
    try:
        default_output = p.get_default_output_device_info()
    except IOError:
        pass

    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxOutputChannels') > 0:
            name = dev_info.get('name')
            is_default = default_output and default_output.get('index') == i
            print("Device {}: {}".format(i, name))
            print("    Channels: {}".format(dev_info.get('maxOutputChannels')))
            print("    Sample Rate: {}".format(dev_info.get('defaultSampleRate')))
            print("    Default: {}".format('Yes' if is_default else 'No'))
            print()

    p.terminate()

if __name__ == '__main__':
    list_audio_devices() 