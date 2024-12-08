# PyHi - Voice Assistant

<p align="center">
  <img src="pyhi.jpg" alt="PyHi Logo" width="200">
</p>

A Python-based voice assistant that enables natural conversations with ChatGPT using voice input and output. The assistant listens for wake words, processes voice commands, and responds with synthesized speech using OpenAI's APIs.

## Features

- Wake word detection using OpenAI's Whisper API
- Natural voice conversations powered by GPT-4-Turbo
- Text-to-speech responses using OpenAI's TTS API
- Automatic session management with configurable timeouts
- Cross-platform audio playback support
- Configurable wake words and audio settings
- Intelligent speech detection with silence analysis
- System audio integration for reliable playback
- Speech detection and analysis
- System audio integration

## Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Microphone for voice input
- Audio output device (speakers/headphones)
- Operating system: Windows, macOS, or Linux
- Required system packages for PyAudio (platform-specific)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/m0nkmaster/pyhi.git
cd pyhi
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. For development/testing, install additional dependencies:
```bash
pip install -r requirements-test.txt
```

4. Create a `.env` file in the project root:
```bash
OPENAI_API_KEY=your_api_key_here
```

### Platform-Specific Setup

#### macOS
```bash
brew install portaudio
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
```

#### Windows
PyAudio should install directly through pip. If issues occur, use the appropriate wheel from [PyAudio Wheels](https://pypi.org/project/pyaudio-wheels/) (untested).

## Project Structure

```
pyhi/
├── src/
│   ├── app.py             # Main application entry point
│   ├── config.py          # Configuration classes
│   ├── _config-mac.py     # macOS-specific config sample
│   ├── _config-raspberry-pi.py  # Raspberry Pi config sample
│   ├── audio/             # Audio recording and playback
│   │   ├── analyzer.py    # Speech analysis
│   │   ├── player.py      # Audio playback
│   │   └── recorder.py    # Audio recording
│   ├── conversation/      # Chat functionality
│   │   ├── manager.py     # Conversation management
│   │   └── openai_client.py # OpenAI API integration
│   ├── word_detection/    # Wake word detection
│   │   └── detector.py    # Wake word processing
│   ├── utils/            # Utility functions
│   │   ├── audio_setup.py  # Audio device configuration
│   │   ├── list_devices.py # Device enumeration utilities
│   │   └── types.py      # Type definitions and protocols
│   └── assets/           # Sound files and resources
│       └── bing.mp3      # Activation sound
├── tests/               # Test suite
├── scripts/             # Utility scripts
├── pyproject.toml      # Project configuration
├── setup.py           # Package setup
├── requirements.txt    # Python dependencies
├── requirements-test.txt # Test dependencies
└── .env               # Environment configuration
```

## Configuration

The application is highly configurable through several configuration classes in `src/config.py`. Primary configurations include:

### AppConfig
- `timeout_seconds`: Conversation timeout duration
- `wake_words`: List of wake word phrases

### AudioConfig
- Sample rate
- Chunk size
- Audio format settings

### ChatConfig
- GPT model settings
- Temperature
- System prompts

### TTSConfig
- Voice selection
- Speech parameters

### WordDetectionConfig
- Detection sensitivity
- Processing parameters

## Usage

1. Start the assistant:
```bash
python -m src.app
```
[Here](CONFIG.md) is a full configuration breakdown.

2. Activate with wake words:
   - Say any configured wake word (default: "Hey Chat", "Hi Chat")
   - Wait for the activation sound
   - Speak your command or question

3. Interaction:
   - The assistant will process your speech using Whisper
   - Generate a response using ChatGPT
   - Convert the response to speech using OpenAI's TTS
   - Play the response through your system audio

4. Session Management:
   - After each response, the assistant waits for the configured timeout period
   - If no new input is detected, it returns to wake word detection mode
   - You can start a new conversation at any time with a wake word

## Development

### Adding New Features
1. Create new modules in the appropriate directory
2. Update configuration in `config.py`
3. Integrate with `VoiceAssistant` class in `app.py`
4. Add tests in the `tests/` directory

### Testing
Install test dependencies:
```bash
pip install -r requirements-test.txt
```

Run the test suite:
```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src

# Run specific test file
pytest tests/unit/test_audio_analyzer.py -v
```

### Common Issues
- Audio device not found: Check system audio settings and permissions
- OpenAI API errors: Verify API key and network connection
- PyAudio installation: Follow platform-specific setup instructions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

See our [Development Roadmap](./ROADMAP.md) for planned features and improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details

### macOS Audio Setup

1. Check microphone permissions:
   - Go to System Preferences > Security & Privacy > Privacy > Microphone
   - Ensure your terminal or IDE has microphone access

2. Verify audio input:
```bash
# Run the audio device test
pytest tests/unit/test_audio_recorder.py -v -s
```

3. If no input is detected, try these solutions:
   - Quit and restart Terminal/IDE after granting permissions
   - Use headphones with built-in mic instead of built-in microphone
   - Check System Preferences > Sound > Input for correct input device
   - Try different sample rates (44100 or 48000) in config

### Troubleshooting

#### macOS Audio Issues

1. Check System Settings
   - Go to System Settings > Privacy & Security > Microphone
   - Ensure Terminal/IDE has microphone access
   - Restart Terminal/IDE after granting permissions

2. Check Audio Input Settings
   - Go to System Settings > Sound > Input
   - Select "MacBook Pro Microphone" or your preferred input device
   - Ensure input volume is not muted/too low

3. Common Issues:
   - **Incorrect Audio Device**: If a virtual audio device is selected instead of your microphone:
     ```bash
     # Check available audio devices
     python -m src.utils.list_devices
     
     # Force microphone selection by setting AUDIO_DEVICE environment variable, e.g.:
     export AUDIO_DEVICE="MacBook Pro Microphone"
     python -m src.app
     ```
   
   - **No Sound Detected**: 
     - Try increasing input volume in System Settings
     - Check if microphone is being used by another application
     - Try unplugging and replugging any external audio devices

4. Virtual Audio Devices:
   - BlackHole, Microsoft Teams Audio, and other virtual devices should be avoided
   - The app will try to use physical microphones first
   - If using virtual audio routing, ensure proper configuration in Audio MIDI Setup