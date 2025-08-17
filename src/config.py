"""
Simplified configuration system for PyHi voice assistant.
Single unified configuration with YAML support and environment variable integration.
"""

import os
import platform
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def expand_env_vars(value: str) -> str:
    """Expand environment variables in configuration values."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, "")
    return value


@dataclass
class AudioConfig:
    """Audio system configuration."""
    input_device: str = "default"
    output_device: str = "default"
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    
    # Speech detection settings
    speech_threshold: float = 200.0
    silence_duration: float = 2.0
    
    # Audio files
    activation_sound: str = "bing.mp3"
    confirmation_sound: str = "elevator.mp3"
    ready_sound: str = "beep.mp3"
    sleep_sound: str = "bing-bong.mp3"


@dataclass
class AIConfig:
    """AI provider configuration."""
    provider: str = "openai"  # "openai" or "anthropic"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    voice: str = "nova"
    voice_model: str = "tts-1"
    max_tokens: int = 250
    temperature: float = 0.7
    
    def __post_init__(self):
        """Expand environment variables in API key."""
        if self.api_key:
            self.api_key = expand_env_vars(self.api_key)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    command: List[str]
    enabled: bool = True
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class MCPConfig:
    """MCP system configuration."""
    enabled: bool = True
    transport: str = "stdio"
    timeout: int = 30
    servers: List[MCPServerConfig] = field(default_factory=list)


@dataclass
class WakeWordConfig:
    """Wake word detection configuration."""
    phrase: str = "Hey Chat"
    model_path: str = ""
    
    def __post_init__(self):
        """Set platform-specific model path if not provided."""
        if not self.model_path:
            assets_dir = Path(__file__).parent / "assets"
            if platform.system().lower() == 'darwin':
                self.model_path = str(assets_dir / "Hey-Chat_en_mac_v3_0_0.ppn")
            else:
                self.model_path = str(assets_dir / "Hey-Chat_en_raspberry-pi_v3_0_0.ppn")


@dataclass
class Config:
    """Main PyHi configuration."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    
    # App settings
    timeout_seconds: float = 10.0
    debug: bool = False
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """
        Load configuration from YAML file with environment variable support.
        
        Args:
            config_path: Path to YAML config file, defaults to 'config.yaml'
            
        Returns:
            Config instance
        """
        if config_path is None:
            config_path = "config.yaml"
        
        # Start with default configuration
        config_data = {}
        
        # Load from YAML file if it exists
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data:
                    config_data = yaml_data
        
        # Create config with defaults, then update with loaded data
        config = cls()
        
        # Update audio config
        if 'audio' in config_data:
            audio_data = config_data['audio']
            for key, value in audio_data.items():
                if hasattr(config.audio, key):
                    setattr(config.audio, key, value)
        
        # Update AI config
        if 'ai' in config_data:
            ai_data = config_data['ai']
            for key, value in ai_data.items():
                if hasattr(config.ai, key):
                    if isinstance(value, str):
                        value = expand_env_vars(value)
                    setattr(config.ai, key, value)
        
        # Update MCP config
        if 'mcp' in config_data:
            mcp_data = config_data['mcp']
            
            # Basic MCP settings
            for key in ['enabled', 'transport', 'timeout']:
                if key in mcp_data:
                    setattr(config.mcp, key, mcp_data[key])
            
            # MCP servers
            if 'servers' in mcp_data:
                config.mcp.servers = []
                for server_data in mcp_data['servers']:
                    server = MCPServerConfig(
                        name=server_data['name'],
                        command=server_data['command'],
                        enabled=server_data.get('enabled', True),
                        env=server_data.get('env', {})
                    )
                    config.mcp.servers.append(server)
        
        # Update wake word config
        if 'wake_word' in config_data:
            wake_word_data = config_data['wake_word']
            for key, value in wake_word_data.items():
                if hasattr(config.wake_word, key):
                    setattr(config.wake_word, key, value)
        
        # Update app settings
        app_settings = ['timeout_seconds', 'debug']
        for setting in app_settings:
            if setting in config_data:
                setattr(config, setting, config_data[setting])
        
        # Validate required settings
        config._validate()
        
        return config
    
    def _validate(self) -> None:
        """Validate configuration settings."""
        # Check for required API keys
        if not self.ai.api_key:
            if self.ai.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            elif self.ai.provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        
        # Check wake word model file (skip check if path is empty, will auto-detect)
        if self.wake_word.model_path and not os.path.exists(self.wake_word.model_path):
            raise ValueError(f"Wake word model not found at {self.wake_word.model_path}")
        
        # Validate audio settings
        if self.audio.sample_rate != 16000:
            print("Warning: Sample rate should be 16000 for optimal wake word detection")
    
    def save(self, config_path: str = "config.yaml") -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save YAML config file
        """
        config_dict = {
            'audio': {
                'input_device': self.audio.input_device,
                'output_device': self.audio.output_device,
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'chunk_size': self.audio.chunk_size,
                'speech_threshold': self.audio.speech_threshold,
                'silence_duration': self.audio.silence_duration,
                'activation_sound': self.audio.activation_sound,
                'confirmation_sound': self.audio.confirmation_sound,
                'ready_sound': self.audio.ready_sound,
                'sleep_sound': self.audio.sleep_sound,
            },
            'ai': {
                'provider': self.ai.provider,
                'model': self.ai.model,
                'api_key': '${OPENAI_API_KEY}' if self.ai.provider == 'openai' else '${ANTHROPIC_API_KEY}',
                'voice': self.ai.voice,
                'voice_model': self.ai.voice_model,
                'max_tokens': self.ai.max_tokens,
                'temperature': self.ai.temperature,
            },
            'mcp': {
                'enabled': self.mcp.enabled,
                'transport': self.mcp.transport,
                'timeout': self.mcp.timeout,
                'servers': [
                    {
                        'name': server.name,
                        'command': server.command,
                        'enabled': server.enabled,
                        'env': server.env
                    }
                    for server in self.mcp.servers
                ]
            },
            'wake_word': {
                'phrase': self.wake_word.phrase,
                'model_path': self.wake_word.model_path,
            },
            'timeout_seconds': self.timeout_seconds,
            'debug': self.debug,
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    @classmethod
    def create_default_config(cls, config_path: str = "config.yaml") -> 'Config':
        """
        Create a default configuration file with all MCP servers.
        
        Args:
            config_path: Path to create the config file
            
        Returns:
            Config instance with defaults
        """
        config = cls()
        
        # Set default AI configuration
        config.ai.api_key = "${OPENAI_API_KEY}"
        
        # Set default MCP servers
        config.mcp.servers = [
            MCPServerConfig(
                name="weather",
                command=["python", "-m", "src.mcp_servers.weather"]
            ),
            MCPServerConfig(
                name="alarms",
                command=["python", "-m", "src.mcp_servers.alarms"]
            ),
            MCPServerConfig(
                name="train_times",
                command=["python", "-m", "src.mcp_servers.train_times"]
            ),
        ]
        
        config.save(config_path)
        return config


# Convenience function for loading config
def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or create default."""
    return Config.load(config_path)