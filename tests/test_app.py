import pytest
from unittest.mock import Mock, patch
from src.app import VoiceAssistant
from src.config import Config


class TestVoiceAssistant:
    def test_initialization(self, mock_env_vars):
        """Test VoiceAssistant initialization"""
        with patch('src.app.load_config') as mock_load_config, \
             patch('src.app.AudioHandler'), \
             patch('src.app.WakeWordDetector'), \
             patch('src.app.MCPManager'), \
             patch('src.app.AIWrapper'), \
             patch('src.app.ChatConversationManager'):
            
            config = Config()
            config.ai.api_key = "test-key"
            mock_load_config.return_value = config
            
            assistant = VoiceAssistant(words=['hey', 'chat'], timeout_seconds=10.0)
            
            assert assistant.config is not None
            assert assistant.running is True
            assert assistant.words == ['hey', 'chat']
            assert assistant.timeout_seconds == 10.0
            assert assistant.is_awake is False


    def test_signal_handler(self, mock_env_vars):
        """Test signal handler for graceful shutdown"""
        with patch('src.app.load_config') as mock_load_config, \
             patch('src.app.AudioHandler'), \
             patch('src.app.WakeWordDetector'), \
             patch('src.app.MCPManager'), \
             patch('src.app.AIWrapper'), \
             patch('src.app.ChatConversationManager'), \
             patch('sys.exit') as mock_exit:
            
            config = Config()
            config.ai.api_key = "test-key"
            mock_load_config.return_value = config
            
            assistant = VoiceAssistant(words=['hey'])
            
            import signal
            assistant._signal_handler(signal.SIGINT, None)
            
            assert assistant.running is False
            mock_exit.assert_called_once_with(0)


    def test_timeout_check(self, mock_env_vars):
        """Test timeout checking functionality"""
        with patch('src.app.load_config') as mock_load_config, \
             patch('src.app.AudioHandler'), \
             patch('src.app.WakeWordDetector'), \
             patch('src.app.MCPManager'), \
             patch('src.app.AIWrapper'), \
             patch('src.app.ChatConversationManager'):
            
            config = Config()
            config.ai.api_key = "test-key"
            mock_load_config.return_value = config
            
            assistant = VoiceAssistant(words=['hey'])
            
            assert assistant._check_timeout() is False
            
            from datetime import datetime, timedelta
            assistant.last_interaction = datetime.now() - timedelta(seconds=15)
            assert assistant._check_timeout() is True


    def test_sound_file_loading(self, mock_env_vars):
        """Test sound file loading"""
        with patch('src.app.load_config') as mock_load_config, \
             patch('src.app.AudioHandler'), \
             patch('src.app.WakeWordDetector'), \
             patch('src.app.MCPManager'), \
             patch('src.app.AIWrapper'), \
             patch('src.app.ChatConversationManager'), \
             patch('os.path.exists', return_value=True):
            
            config = Config()
            config.ai.api_key = "test-key"
            mock_load_config.return_value = config
            
            assistant = VoiceAssistant(words=['hey'])
            
            sound_path = assistant._get_sound_path("test.mp3")
            assert sound_path.endswith("test.mp3")
            assert "assets" in sound_path


    def test_cleanup(self, mock_env_vars):
        """Test cleanup functionality"""
        with patch('src.app.load_config') as mock_load_config, \
             patch('src.app.AudioHandler'), \
             patch('src.app.WakeWordDetector'), \
             patch('src.app.MCPManager') as mock_mcp_class, \
             patch('src.app.AIWrapper'), \
             patch('src.app.ChatConversationManager'), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            config = Config()
            config.ai.api_key = "test-key"
            mock_load_config.return_value = config
            
            mock_mcp = Mock()
            mock_mcp.shutdown = Mock()
            mock_mcp_class.return_value = mock_mcp
            
            assistant = VoiceAssistant(words=['hey'])
            assistant._cleanup()
            
            mock_remove.assert_called()