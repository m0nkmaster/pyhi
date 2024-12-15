# PyHi - Voice Assistant

<p align="center">
  <img src="pyhi.jpg" alt="PyHi Logo" width="200">
</p>

A Python-based voice assistant that enables natural conversations with ChatGPT using voice input and output. The assistant uses Porcupine for wake word detection and provides a seamless voice interaction experience.

## Features

- Wake word detection using Picovoice's Porcupine engine
- Natural voice conversations powered by GPT-3.5-turbo
- Text-to-speech responses using OpenAI's TTS API
- Automatic session management with configurable timeouts
- Cross-platform audio playback support
- Configurable wake words through Porcupine
- Intelligent silence detection for speech processing
- System audio integration for reliable playback
- Audio feedback sounds for clear interaction states
- Unified AI interactions using the `AIWrapper` class for both OpenAI and Claude APIs
- Configurable AI provider and model settings

## Prerequisites

- OpenAI API key (for ChatGPT and TTS)
- Anthropic API key (for Claude chat completions)
- Python 3.9 or higher
- Picovoice API key (for Porcupine wake word detection)
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
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
PICOVOICE_API_KEY=your_picovoice_key_here
```

Ensure you have both OpenAI and Anthropic API keys set in your environment before running the application.

### Platform-Specific Setup

#### macOS
```bash
brew install portaudio
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install python3-pyaudio portaudio19-dev
source venv/bin/activate
```

#### Windows
PyAudio should install directly through pip. If issues occur, use the appropriate wheel from [PyAudio Wheels](https://pypi.org/project/pyaudio-wheels/).

## Project Structure

```
pyhi/
├── src/
│   ├── app.py             # Main application entry point
│   ├── config.py          # Configuration classes
│   ├── audio/             # Audio recording and playback
│   │   ├── player.py      # Audio playback
│   │   └── recorder.py    # Audio recording
│   ├── conversation/      # Chat functionality
│   │   ├── __init__.py
│   │   ├── ai_client.py     # AI service integration (OpenAI, Anthropic)
│   │   └── manager.py       # Conversation state management
│   ├── utils/            # Utility functions
│   │   ├── audio_setup.py  # Audio device configuration
│   │   ├── list_devices.py # Device enumeration utilities
│   │   └── types.py      # Type definitions and protocols
│   └── assets/           # Sound files and resources
│       ├── bing.mp3      # Wake word sound
│       ├── yes.mp3       # Speech recognition sound
│       ├── beep.mp3      # Ready for next question sound
│       └── bing-bong.mp3 # Sleep mode sound
├── tests/               # Test suite
├── scripts/             # Utility scripts
├── CONFIG.md           # Detailed configuration guide
├── pyproject.toml      # Project configuration
├── setup.py           # Package setup
├── requirements.txt    # Python dependencies
├── requirements-test.txt # Test dependencies
└── .env               # Environment configuration
```

## Usage

1. Run the assistant:
```bash
python -m src.app
```

2. Say a wake word (default: "Computer") to start a conversation
3. Wait for the activation sound
4. Ask your question
5. Wait for the response
6. Continue the conversation or let it timeout to sleep mode

## Interaction Flow

1. **Wake Word Detection**
   - Say "Computer" (or your configured wake word)
   - Hear "bing.mp3" to confirm wake word detection

2. **Speech Input**
   - Speak your question/command
   - Silence is automatically detected
   - Hear "yes.mp3" when speech is recognized

3. **AI Response**
   - ChatGPT processes your input
   - Response is converted to speech
   - Hear "beep.mp3" when ready for next question

4. **Sleep Mode**
   - After timeout period with no interaction
   - Hear "bing-bong.mp3" when going to sleep
   - Say wake word to start new conversation

## Configuration

See [CONFIG.md](CONFIG.md) for detailed configuration options, including:
- Audio device selection
- Wake word customization
- Silence detection thresholds
- ChatGPT and TTS settings
- Timeout values
- AI provider and model settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for ChatGPT and TTS APIs
- Anthropic for Claude chat completions
- Picovoice for Porcupine wake word engine
- PyAudio contributors
- All other open-source dependencies