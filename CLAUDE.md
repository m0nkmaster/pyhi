# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
python -m src.app
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_audio.py
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt

# Install in development mode
pip install -e .
```

### Environment Setup
Create a `.env` file with required API keys:
```
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
PICOVOICE_API_KEY=your_picovoice_key_here
```

## Architecture Overview

PyHi is a Python voice assistant that provides natural conversations with AI models using voice input/output. The system integrates multiple AI providers (OpenAI, Anthropic) with wake word detection and function calling capabilities.

### Core Components

- **VoiceAssistant** (`src/app.py`): Main application orchestrating all components
- **AIWrapper** (`src/conversation/ai_client.py`): Unified interface for OpenAI and Anthropic APIs
- **MCPManager** (`src/mcp_manager.py`): MCP server management and tool execution system
- **Audio System**: Separate recording (`src/audio/recorder.py`) and playback (`src/audio/player.py`) modules
- **Wake Word Detection**: Porcupine-based detection system (`src/word_detection/detector.py`)

### MCP System Architecture

Tools are provided through MCP (Model Context Protocol) servers in `src/mcp_servers/` with each server providing specific functionality:

Available MCP servers:
- `train_times/`: Rail departure information via LDBWS API
- `weather/`: Weather data integration
- `calendar/`: Google Calendar integration
- `alarms/`: Audio alarm functionality
- `streaming/`: File system monitoring and streaming capabilities

### Configuration System

All configuration is centralized in `src/config.py` with dataclass-based configs:
- `AppConfig`: Application-level settings and timeouts
- `AudioConfig`: Audio processing parameters (16kHz, mono, 1024 chunk size for Porcupine)
- `AIConfig`: AI provider selection and model settings
- `WordDetectionConfig`: Wake word detection settings

### AI Provider Support

The system supports multiple AI providers through `AIWrapper`:
- **OpenAI**: GPT models for chat, TTS for voice synthesis
- **Anthropic**: Claude models for chat completions
- Provider selection via `chat_provider` config parameter

### Audio Pipeline

1. **Wake Word Detection**: Continuous monitoring using Porcupine
2. **Speech Recording**: PyAudio-based recording with silence detection
3. **Speech Recognition**: Google Speech Recognition API
4. **AI Processing**: Context-aware responses with function calling
5. **Text-to-Speech**: OpenAI TTS for response synthesis
6. **Audio Playback**: Cross-platform audio output

### Session Management

- Conversation context maintained in `ChatConversationManager`
- Configurable timeout system for automatic sleep mode
- Audio feedback for different states (activation, processing, ready, sleep)

## Development Notes

- Audio configuration requires 16kHz sample rate and mono channel for Porcupine compatibility
- Function implementations must have an `execute(args: dict) -> dict` method
- Platform-specific wake word models (.ppn files) are required for different operating systems
- All temporary audio files are automatically cleaned up on exit
- Use Conventional Commits for version control