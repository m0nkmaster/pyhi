# PyHi - Voice Assistant

A Python-based voice assistant that enables natural conversations with ChatGPT using voice input and output. The assistant listens for wake words, processes voice commands, and responds with synthesized speech using OpenAI's APIs.

## Features

- Wake word detection using OpenAI's Whisper API
- Natural voice conversations with ChatGPT
- Text-to-speech responses using OpenAI's TTS API
- Automatic session management with configurable timeouts
- Cross-platform audio playback support
- Configurable wake words and audio settings
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

3. Create a `.env` file in the project root:
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
│   ├── app.py              # Main application entry point
│   ├── config.py           # Configuration classes
│   ├── _config-mac.py      # macOS-specific config
│   ├── _config-raspberry-pi.py  # Raspberry Pi config
│   ├── audio/              # Audio recording and playback
│   │   ├── analyzer.py     # Speech analysis
│   │   ├── player.py       # Audio playback
│   │   └── recorder.py     # Audio recording
│   ├── conversation/       # Chat functionality
│   │   ├── manager.py      # Conversation management
│   │   └── openai_client.py # OpenAI API integration
│   ├── word_detection/     # Wake word detection
│   │   └── detector.py     # Wake word processing
│   ├── utils/             # Utility functions
│   │   └── types.py       # Type definitions and protocols
│   └── assets/            # Sound files and resources
│       └── bing.mp3       # Activation sound
├── requirements.txt       # Python dependencies
└── .env                # Environment configuration
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
Run the test suite:
```bash
pytest tests/
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