import os
import sys
import pytest
import tempfile
from unittest.mock import Mock, patch

# Get the absolute path of the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root directory to the Python path
sys.path.insert(0, project_root)

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
        'PICOVOICE_API_KEY': 'test-picovoice-key',
        'TOMORROW_IO_API_KEY': 'test-weather-key',
        'WATCHMODE_API_KEY': 'test-streaming-key'
    }
    with patch.dict('os.environ', env_vars):
        yield env_vars

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    config_content = """
audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 1024

ai:
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "${OPENAI_API_KEY}"

mcp:
  enabled: true
  servers:
    - name: "test-server"
      command: ["python", "-m", "test"]
      enabled: true

wake_word:
  phrase: "Hey Chat"
  model_path: "/test/model.ppn"

timeout_seconds: 10.0
debug: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name
    
    os.unlink(f.name)
