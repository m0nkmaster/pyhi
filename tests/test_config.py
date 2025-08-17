import pytest
import tempfile
import os
from src.config import Config, load_config, AudioConfig, AIConfig, MCPConfig, WakeWordConfig, MCPServerConfig


class TestConfig:
    def test_config_defaults(self):
        """Test that Config initializes with correct default values"""
        config = Config()
        
        # Audio defaults
        assert config.audio.input_device == "default"
        assert config.audio.output_device == "default"
        assert config.audio.sample_rate == 16000
        assert config.audio.channels == 1
        assert config.audio.chunk_size == 1024
        assert config.audio.speech_threshold == 200.0
        assert config.audio.silence_duration == 2.0
        assert config.audio.activation_sound == "bing.mp3"
        assert config.audio.confirmation_sound == "elevator.mp3"
        assert config.audio.ready_sound == "beep.mp3"
        assert config.audio.sleep_sound == "bing-bong.mp3"
        
        # AI defaults
        assert config.ai.provider == "openai"
        assert config.ai.model == "gpt-4o-mini"
        assert config.ai.voice == "nova"
        assert config.ai.voice_model == "tts-1"
        assert config.ai.max_tokens == 250
        assert config.ai.temperature == 0.7
        
        # MCP defaults
        assert config.mcp.enabled is True
        assert config.mcp.transport == "stdio"
        assert config.mcp.timeout == 30
        assert isinstance(config.mcp.servers, list)
        
        # Wake word defaults
        assert config.wake_word.phrase == "Hey Chat"
        assert config.wake_word.model_path != ""  # Auto-detected path
        
        # App defaults
        assert config.timeout_seconds == 10.0
        assert config.debug is False


    def test_load_config_from_yaml(self, mock_env_vars):
        """Test loading config from YAML file"""
        yaml_content = """
audio:
  sample_rate: 22050
  channels: 2
  speech_threshold: 300.0

ai:
  provider: "anthropic"
  model: "claude-3-haiku-20240307"
  temperature: 0.5

mcp:
  enabled: false
  timeout: 60
  servers:
    - name: "test-server"
      command: ["python", "-m", "test"]
      enabled: true

wake_word:
  phrase: "Hello Assistant"
  model_path: ""

timeout_seconds: 15.0
debug: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = Config.load(f.name)
                
                # Verify overridden values
                assert config.audio.sample_rate == 22050
                assert config.audio.channels == 2
                assert config.audio.speech_threshold == 300.0
                assert config.ai.provider == "anthropic"
                assert config.ai.model == "claude-3-haiku-20240307"
                assert config.ai.temperature == 0.5
                assert config.mcp.enabled is False
                assert config.mcp.timeout == 60
                assert len(config.mcp.servers) == 1
                assert config.mcp.servers[0].name == "test-server"
                assert config.wake_word.phrase == "Hello Assistant"
                # Model path should be empty since we set it to empty in YAML
                # Auto-detection happens in __post_init__ only if empty
                assert config.wake_word.model_path == ""
                assert config.timeout_seconds == 15.0
                assert config.debug is True
                
                # Verify defaults remain for non-overridden values
                assert config.audio.input_device == "default"
                assert config.ai.voice == "nova"
                
            finally:
                os.unlink(f.name)


    def test_environment_variable_expansion(self, mock_env_vars):
        """Test environment variable expansion in config"""
        yaml_content = """
ai:
  api_key: "${OPENAI_API_KEY}"
  model: "${TEST_MODEL}"
"""
        
        # Set test environment variable
        os.environ["TEST_MODEL"] = "gpt-4"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = Config.load(f.name)
                
                assert config.ai.api_key == "test-openai-key"
                assert config.ai.model == "gpt-4"
                
            finally:
                os.unlink(f.name)
                del os.environ["TEST_MODEL"]


    def test_load_config_file_not_found(self):
        """Test loading config with non-existent file returns defaults"""
        config = Config.load("/nonexistent/config.yaml")
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.ai.provider == "openai"  # Default value


    def test_mcp_server_config_structure(self, mock_env_vars):
        """Test MCP server configuration structure"""
        yaml_content = """
mcp:
  servers:
    - name: "weather"
      command: ["python", "-m", "src.mcp_servers.weather"]
      enabled: true
      env:
        API_KEY: "test-key"
    - name: "alarms"
      command: ["python", "-m", "src.mcp_servers.alarms"]
      enabled: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = Config.load(f.name)
                
                assert len(config.mcp.servers) == 2
                
                weather_server = config.mcp.servers[0]
                assert weather_server.name == "weather"
                assert weather_server.command == ["python", "-m", "src.mcp_servers.weather"]
                assert weather_server.enabled is True
                assert weather_server.env == {"API_KEY": "test-key"}
                
                alarms_server = config.mcp.servers[1]
                assert alarms_server.name == "alarms"
                assert alarms_server.enabled is False
                
            finally:
                os.unlink(f.name)


    def test_config_validation(self, mock_env_vars):
        """Test configuration validation"""
        config = Config()
        config.ai.api_key = "test-key"
        
        # Should not raise with valid config
        config._validate()


    def test_config_validation_missing_api_key(self):
        """Test validation with missing API key"""
        from unittest.mock import patch
        with patch.dict('os.environ', {}, clear=True):  # Clear all env vars
            config = Config()
            config.ai.api_key = ""
            config.ai.provider = "openai"
            
            # Should raise error for missing API key
            with pytest.raises(ValueError, match="OpenAI API key not found"):
                config._validate()


    def test_config_save(self, mock_env_vars):
        """Test saving configuration to YAML file"""
        config = Config()
        config.ai.provider = "anthropic"
        config.timeout_seconds = 20.0
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                config.save(f.name)
                
                # Load and verify saved config
                loaded_config = Config.load(f.name)
                assert loaded_config.ai.provider == "anthropic"
                assert loaded_config.timeout_seconds == 20.0
                
            finally:
                os.unlink(f.name)


    def test_create_default_config(self, mock_env_vars):
        """Test creating default configuration file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                config = Config.create_default_config(f.name)
                
                # Verify file was created and has expected content
                assert os.path.exists(f.name)
                
                # Load and verify default config (without env expansion)
                with open(f.name, 'r') as yaml_file:
                    import yaml
                    yaml_content = yaml.safe_load(yaml_file)
                    assert yaml_content['ai']['api_key'] == "${OPENAI_API_KEY}"
                    assert len(yaml_content['mcp']['servers']) >= 3  # Should have default servers
                
            finally:
                os.unlink(f.name)


class TestAudioConfig:
    def test_audio_config_defaults(self):
        """Test AudioConfig default values"""
        config = AudioConfig()
        
        assert config.input_device == "default"
        assert config.output_device == "default"
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.chunk_size == 1024
        assert config.speech_threshold == 200.0
        assert config.silence_duration == 2.0


class TestAIConfig:
    def test_ai_config_defaults(self):
        """Test AIConfig default values"""
        config = AIConfig()
        
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.voice == "nova"
        assert config.voice_model == "tts-1"
        assert config.max_tokens == 250
        assert config.temperature == 0.7


    def test_ai_config_env_expansion(self):
        """Test environment variable expansion in AIConfig"""
        os.environ["TEST_API_KEY"] = "expanded-key"
        
        try:
            config = AIConfig()
            config.api_key = "${TEST_API_KEY}"
            config.__post_init__()
            
            assert config.api_key == "expanded-key"
            
        finally:
            del os.environ["TEST_API_KEY"]


class TestMCPConfig:
    def test_mcp_config_defaults(self):
        """Test MCPConfig default values"""
        config = MCPConfig()
        
        assert config.enabled is True
        assert config.transport == "stdio"
        assert config.timeout == 30
        assert isinstance(config.servers, list)
        assert len(config.servers) == 0


class TestMCPServerConfig:
    def test_mcp_server_config(self):
        """Test MCPServerConfig creation"""
        config = MCPServerConfig(
            name="test-server",
            command=["python", "-m", "test"],
            enabled=True,
            env={"KEY": "value"}
        )
        
        assert config.name == "test-server"
        assert config.command == ["python", "-m", "test"]
        assert config.enabled is True
        assert config.env == {"KEY": "value"}


class TestWakeWordConfig:
    def test_wake_word_config_defaults(self):
        """Test WakeWordConfig default values"""
        config = WakeWordConfig()
        
        assert config.phrase == "Hey Chat"
        assert config.model_path != ""  # Should be auto-detected


    def test_wake_word_config_auto_detection(self):
        """Test automatic model path detection"""
        config = WakeWordConfig()
        config.model_path = ""  # Trigger auto-detection
        config.__post_init__()
        
        # Should set a platform-specific path
        assert config.model_path != ""
        assert config.model_path.endswith(".ppn")


def test_load_config_convenience_function(mock_env_vars):
    """Test the convenience load_config function"""
    config = load_config()
    
    assert isinstance(config, Config)
    assert config.ai.provider == "openai"