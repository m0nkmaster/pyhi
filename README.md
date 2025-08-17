# PyHi Voice Assistant

**A Python voice assistant with pure MCP (Model Context Protocol) architecture for maximum extensibility.**

<p align="center">
  <img src="pyhi.jpg" alt="PyHi Logo" width="200">
</p>

---

## 🎯 Overview

PyHi is a voice-controlled AI assistant that combines:
- **Wake word detection** ("Hey Chat")
- **Speech-to-text** recognition
- **AI conversation** with OpenAI/Anthropic
- **Tool calling** through MCP servers only
- **Text-to-speech** responses

The system is designed for **simplicity and extensibility** - add new capabilities by creating simple MCP servers.

---

## 🚀 Quick Start

### **Installation**
```bash
git clone <repository>
cd pyhi
pip install -r requirements.txt
```

### **Environment Setup**
Create `.env` file:
```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key  # Optional
PICOVOICE_API_KEY=your_picovoice_key
TOMORROW_IO_API_KEY=your_weather_key  # Optional for weather server
WATCHMODE_API_KEY=your_watchmode_key  # Optional for streaming server
```

### **Configuration**
Copy and customize the configuration:
```bash
cp config.yaml my_config.yaml
# Edit my_config.yaml as needed
```

### **Run the Assistant**
```bash
python -m src.app
```

Say **"Hey Chat"** followed by your command!

---

## 🎤 Voice Commands

### **Weather**
- "What's the weather in London?"
- "How's the weather today?"
- "Tell me about the weather in Tokyo"

### **Alarms & Timers**
- "Set a timer for 5 minutes"
- "Set an alarm for 2:30 PM"
- "List my alarms"

### **Train Times** (UK)
- "What trains leave from London Paddington?"
- "Show departures from Manchester"
- "Find trains to Birmingham"

### **Google Calendar**
- "Add meeting tomorrow at 3 PM"
- "What's on my calendar today?"
- "Schedule lunch with John for Friday"

### **Streaming Services**
- "Where can I watch Inception?"
- "Find streaming options for The Office"
- "What's available on Netflix?"

### **General Conversation**
- "What time is it?"
- "Tell me a joke"
- "How are you today?"

---

## 🏗️ Architecture

### **System Flow**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Wake Word     │───▶│   Audio Handler  │───▶│ Speech-to-Text  │
│   Detection     │    │   (Unified)      │    │   Recognition   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Porcupine     │    │   PyAudio +      │    │   Google Speech │
│   Detection     │    │   Speech Rec     │    │   Recognition   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Audio         │◀───│   Text-to-Speech │◀───│   AI Processing │
│   Playback      │    │   Generation     │    │   & MCP Tools   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Unified       │    │   OpenAI TTS     │    │ OpenAI/Anthropic│
│   Audio Handler │    │   API            │    │ + MCP Servers   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **File Structure**

```
src/
├── app.py                    # Main VoiceAssistant class
├── config.py                 # Unified configuration system
├── audio.py                  # Unified audio handler
├── wake_word.py              # Wake word detection
├── mcp_manager.py            # MCP server management
├── conversation/             # AI conversation management
│   ├── ai_client.py          # OpenAI/Anthropic API client
│   └── manager.py            # Conversation state management
├── mcp_servers/              # MCP servers (extensible)
│   ├── weather/              # Weather information
│   ├── alarms/               # Timers and alarms
│   ├── train_times/          # UK train departures
│   ├── calendar/             # Google Calendar integration
│   └── streaming/            # Streaming service search
├── utils/                    # Utility functions
└── assets/                   # Audio files and models
```

### **Core Components**

#### **Configuration System** (`src/config.py`)
- Single Config class with YAML support
- Environment variable expansion
- Platform-specific auto-detection
- Clean, organized settings structure

#### **Audio System** (`src/audio.py` + `src/wake_word.py`)
- **AudioHandler**: Unified recording, playback, and speech recognition
- **WakeWordDetector**: Porcupine integration with async interface
- Async-first design for responsive interaction

#### **MCP Extensions**
All functionality is provided through MCP servers:
- Clean, single-system approach
- 5 complete servers ready to use
- Easy server addition via configuration

---

## 🛠️ MCP Servers

### **Built-in Servers**

#### **Weather Server** (`src/mcp_servers/weather/`)
- Current weather conditions
- Weather forecasts
- Location-based weather data
- Tomorrow.io API integration

#### **Alarms Server** (`src/mcp_servers/alarms/`)
- Set timers and alarms
- List active alarms
- Cancel alarms
- Audio notifications

#### **Train Times Server** (`src/mcp_servers/train_times/`)
- UK train departure information
- Station code search
- Live departure boards
- LDBWS API integration

#### **Calendar Server** (`src/mcp_servers/calendar/`)
- Google Calendar integration
- Add/delete events
- View upcoming events
- Service account authentication

#### **Streaming Server** (`src/mcp_servers/streaming/`)
- Movie/TV show search
- Streaming availability
- UK-focused results
- Watchmode API integration

### **Adding New MCP Servers**

#### **1. Create Server Structure**
```bash
mkdir src/mcp_servers/my_server
touch src/mcp_servers/my_server/__init__.py
```

#### **2. Implement Server** (`src/mcp_servers/my_server/__main__.py`)
```python
#!/usr/bin/env python3
from mcp.server import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("my-server")

@mcp.tool()
async def my_function(param: str) -> str:
    """My custom function description."""
    return f"Result: {param}"

@mcp.resource("my-data://items")
async def get_items() -> str:
    """Get available items."""
    return json.dumps({"items": ["a", "b", "c"]})

if __name__ == "__main__":
    mcp.run("stdio")
```

#### **3. Update Configuration** (`config.yaml`)
```yaml
mcp:
  servers:
    - name: "my-server"
      command: ["python", "-m", "src.mcp_servers.my_server"]
      enabled: true
```

### **Third-Party MCP Servers**
```yaml
mcp:
  servers:
    - name: "github"
      command: ["npx", "@modelcontextprotocol/server-github"]
    - name: "filesystem"
      command: ["python", "-m", "mcp_server_filesystem"]
```

---

## ⚙️ Configuration

### **config.yaml Structure**
```yaml
# Audio system settings
audio:
  input_device: "default"
  output_device: "default"
  sample_rate: 16000
  channels: 1
  chunk_size: 1024
  speech_threshold: 200.0
  silence_duration: 2.0
  activation_sound: "bing.mp3"
  confirmation_sound: "elevator.mp3"
  ready_sound: "beep.mp3"
  sleep_sound: "bing-bong.mp3"

# AI provider configuration
ai:
  provider: "openai"  # "openai" or "anthropic"
  model: "gpt-4o-mini"
  api_key: "${OPENAI_API_KEY}"
  voice: "nova"
  voice_model: "tts-1"
  max_tokens: 250
  temperature: 0.7

# MCP server configuration
mcp:
  enabled: true
  transport: "stdio"
  timeout: 30
  servers:
    - name: "weather"
      command: ["python", "-m", "src.mcp_servers.weather"]
      enabled: true
    # ... other servers

# Wake word detection
wake_word:
  phrase: "Hey Chat"
  model_path: ""  # Auto-detected

# Application settings
timeout_seconds: 10.0
debug: false
```

### **Environment Variables**
```bash
# Required
OPENAI_API_KEY=your_openai_key
PICOVOICE_API_KEY=your_picovoice_key

# Optional
ANTHROPIC_API_KEY=your_anthropic_key
TOMORROW_IO_API_KEY=your_weather_key
WATCHMODE_API_KEY=your_streaming_key
```

---

## 📊 Architecture Benefits

### **Design Advantages**
- ✅ **Single extension system** (MCP only)
- ✅ **Unified configuration** (YAML with env vars)
- ✅ **Efficient audio system** (streamlined implementation)
- ✅ **Clean file structure** (organized by purpose)
- ✅ **Pure MCP architecture** (standardized protocols)

### **Developer Experience**
- ✅ **Easy to understand** - clear component responsibilities
- ✅ **Simple to extend** - standard MCP server creation
- ✅ **Well documented** - comprehensive examples
- ✅ **Clean APIs** - async-first design
- ✅ **Type safe** - Pydantic models throughout

### **Maintainability**
- ✅ **Reduced complexity** - single system to maintain
- ✅ **Clear error handling** - structured exceptions
- ✅ **Easy testing** - modular components
- ✅ **Standard protocols** - MCP for all extensions

---

## 🔍 Technical Details

### **Dependencies**
```txt
# Core functionality
openai>=1.5.0
mcp>=1.0.0
pydantic>=2.0.0
pyyaml>=6.0.0

# AI providers
anthropic>=0.25.0

# Audio processing
pyaudio>=0.2.14
SpeechRecognition>=3.10.0
pydub>=0.25.0
pvporcupine>=3.0.0

# HTTP client
httpx>=0.25.0

# Utilities
python-dotenv>=1.0.0
numpy>=1.21.0
```

### **Platform Support**
- **macOS**: Full support (development platform)
- **Linux**: General support
- **Raspberry Pi**: Optimized for edge deployment
- **Windows**: Basic support

### **Hardware Requirements**
- **Microphone**: Any USB/built-in microphone
- **Speakers**: Audio output device
- **CPU**: Modern processor for speech processing
- **RAM**: 1GB+ for AI model processing
- **Network**: Internet connection for AI APIs

---

## 🧪 Development

### **Setup**
```bash
git clone <repository>
cd pyhi
pip install -r requirements.txt
pip install -r requirements-test.txt  # For development
```

### **Running Tests**
```bash
pytest                    # All tests
pytest --cov=src         # With coverage
pytest tests/test_mcp.py  # Specific tests
```

### **Code Quality**
```bash
ruff check src/          # Linting
ruff format src/         # Formatting
mypy src/               # Type checking
```

### **Development Commands**
```bash
# Run the assistant
python -m src.app

# Test individual MCP servers
python -m src.mcp_servers.weather
python -m src.mcp_servers.alarms

# Load custom config
python -m src.app --config my_config.yaml
```

---

## 🚀 Usage Examples

### **Basic Interaction**
1. Start PyHi: `python -m src.app`
2. Say "Hey Chat" (wait for confirmation sound)
3. Ask: "What's the weather like today?"
4. Listen to response
5. Continue conversation or wait for timeout

### **Configuration Customization**
```bash
# Copy default config
cp config.yaml my_setup.yaml

# Edit settings
vim my_setup.yaml

# Run with custom config
python -m src.app --config my_setup.yaml
```

### **Server Development**
```bash
# Create new server
mkdir src/mcp_servers/my_service
cd src/mcp_servers/my_service

# Implement server (see examples above)
vim __main__.py

# Test server independently
python __main__.py

# Add to config and restart PyHi
```

---

## 📚 Documentation

### **Available Documentation**
- `CLAUDE.md`: Development instructions and architecture notes
- `ARCHITECTURE.md`: Detailed architecture analysis
- `config.yaml`: Complete configuration reference with comments

### **API Documentation**
Each MCP server includes:
- **Tool definitions** with parameter validation
- **Resource endpoints** for data access
- **Prompt templates** for AI interaction
- **Error handling** with structured responses

---

## 🤝 Contributing

### **Areas for Contribution**
1. **New MCP Servers** - Add functionality through standard MCP protocol
2. **Platform Support** - Improve Windows/Linux compatibility
3. **Audio Enhancements** - Better speech recognition, noise cancellation
4. **Documentation** - Usage examples, tutorials, troubleshooting
5. **Testing** - Expand test coverage, integration tests

### **Contribution Process**
1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Ensure code quality (ruff, mypy)
5. Submit pull request with description

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙋 Support

- **Issues**: [GitHub Issues](link)
- **Discussions**: [GitHub Discussions](link)
- **Documentation**: This README and inline documentation

---

## 🎉 Acknowledgments

- **OpenAI** for ChatGPT and TTS APIs
- **Anthropic** for Claude chat completions
- **Picovoice** for Porcupine wake word engine
- **MCP Community** for the Model Context Protocol standard
- **PyAudio contributors** and all other open-source dependencies

---

**PyHi** - A voice assistant that's simple to understand, easy to extend, and powerful through standardized MCP servers.

*Built with ❤️ for developers who value simplicity and extensibility.*