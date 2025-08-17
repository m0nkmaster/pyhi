import pytest
import tempfile
import os
from src.config import Config, load_config


def test_config_defaults():
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


def test_load_config_from_yaml():
    """Test loading config from YAML file"""
    yaml_content = """
audio:
  sample_rate: 22050
  channels: 2

ai:
  provider: "anthropic"
  model: "claude-3-haiku-20240307"

mcp:
  enabled: false
  timeout: 60

timeout_seconds: 15.0
debug: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        try:
            config = load_config(f.name)
            
            # Verify overridden values
            assert config.audio.sample_rate == 22050
            assert config.audio.channels == 2
            assert config.ai.provider == "anthropic"
            assert config.ai.model == "claude-3-haiku-20240307"
            assert config.mcp.enabled is False
            assert config.mcp.timeout == 60
            assert config.timeout_seconds == 15.0
            assert config.debug is True
            
            # Verify defaults remain for non-overridden values
            assert config.audio.input_device == "default"
            assert config.ai.voice == "nova"
            
        finally:
            os.unlink(f.name)


def test_environment_variable_expansion():
    """Test environment variable expansion in config"""
    os.environ["TEST_API_KEY"] = "secret_key_123"
    os.environ["TEST_MODEL"] = "gpt-4"
    
    yaml_content = """
ai:
  api_key: "${TEST_API_KEY}"
  model: "${TEST_MODEL}"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        try:
            config = load_config(f.name)
            
            assert config.ai.api_key == "secret_key_123"
            assert config.ai.model == "gpt-4"
            
        finally:
            os.unlink(f.name)
            del os.environ["TEST_API_KEY"]
            del os.environ["TEST_MODEL"]


def test_load_config_file_not_found():
    """Test loading config with non-existent file returns defaults"""
    config = load_config("/nonexistent/config.yaml")
    
    # Should return default config
    assert isinstance(config, Config)
    assert config.ai.provider == "openai"  # Default value


def test_mcp_server_config():
    """Test MCP server configuration structure"""
    yaml_content = """
mcp:
  servers:
    - name: "weather"
      command: ["python", "-m", "src.mcp_servers.weather"]
      enabled: true
    - name: "alarms"
      command: ["python", "-m", "src.mcp_servers.alarms"]
      enabled: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        
        try:
            config = load_config(f.name)
            
            assert len(config.mcp.servers) == 2
            
            weather_server = config.mcp.servers[0]
            assert weather_server.name == "weather"
            assert weather_server.command == ["python", "-m", "src.mcp_servers.weather"]
            assert weather_server.enabled is True
            
            alarms_server = config.mcp.servers[1]
            assert alarms_server.name == "alarms"
            assert alarms_server.enabled is False
            
        finally:
            os.unlink(f.name)