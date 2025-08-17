"""
Simplified wake word detection for PyHi voice assistant.
Uses Porcupine for efficient wake word detection.
"""

import os
import logging
import asyncio
from typing import Optional

import pvporcupine
import numpy as np

from .config import Config


class WakeWordError(Exception):
    """Exception for wake word detection errors."""
    pass


class WakeWordDetector:
    """Simplified wake word detector using Porcupine."""
    
    def __init__(self, config: Config):
        """
        Initialize the wake word detector.
        
        Args:
            config: Wake word configuration
        """
        self.config = config.wake_word
        self.porcupine = None
        
        # Initialize Porcupine
        self._setup_porcupine()
        
    def __del__(self):
        """Cleanup Porcupine resources."""
        if self.porcupine:
            self.porcupine.delete()
    
    def _setup_porcupine(self):
        """Setup Porcupine wake word detection."""
        try:
            # Get access key from environment
            access_key = os.getenv("PICOVOICE_API_KEY")
            if not access_key:
                raise WakeWordError("PICOVOICE_API_KEY environment variable not set")
            
            # Auto-detect model path if not specified
            model_path = self.config.model_path
            if not model_path:
                model_path = self._get_model_path()
            
            # Check model file exists
            if not os.path.exists(model_path):
                raise WakeWordError(f"Wake word model not found at {model_path}")
            
            # Initialize Porcupine
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[model_path]
            )
            
            logging.info(f"Initialized wake word detection: '{self.config.phrase}' using {model_path}")
            
        except Exception as e:
            raise WakeWordError(f"Failed to initialize wake word detection: {e}")
    
    def _get_model_path(self) -> str:
        """Auto-detect the correct model path based on platform."""
        import platform
        from pathlib import Path
        
        assets_dir = Path(__file__).parent / "assets"
        system = platform.system().lower()
        
        if system == "darwin":  # macOS
            model_file = "Hey-Chat_en_mac_v3_0_0.ppn"
        elif system == "linux":
            # Check if it's Raspberry Pi
            try:
                with open("/proc/cpuinfo", "r") as f:
                    if "raspberry pi" in f.read().lower():
                        model_file = "Hey-Chat_en_raspberry-pi_v3_0_0.ppn"
                    else:
                        model_file = "Hey-Chat_en_mac_v3_0_0.ppn"  # Use mac model for Linux
            except:
                model_file = "Hey-Chat_en_mac_v3_0_0.ppn"  # Fallback
        else:
            model_file = "Hey-Chat_en_mac_v3_0_0.ppn"  # Default fallback
        
        return str(assets_dir / model_file)
    
    def detect(self, audio_data: bytes) -> bool:
        """
        Detect wake word in audio data.
        
        Args:
            audio_data: Raw audio data as bytes
            
        Returns:
            True if wake word detected, False otherwise
        """
        try:
            # Convert bytes to int16 numpy array
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            

            
            # Porcupine expects exactly frame_length samples
            if len(pcm) == self.porcupine.frame_length:
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    logging.info(f"Wake word '{self.config.phrase}' detected!")
                    return True
            else:
                logging.debug(f"Frame size mismatch: got {len(pcm)}, expected {self.porcupine.frame_length}")
            
            return False
            
        except Exception as e:
            logging.error(f"Error in wake word detection: {e}")
            return False
    
    async def wait_for_wake_word(self, audio_handler) -> bool:
        """
        Continuously listen for wake word.
        
        Args:
            audio_handler: AudioHandler instance for recording
            
        Returns:
            True when wake word is detected
        """
        try:
            logging.info(f"Listening for wake word: '{self.config.phrase}'...")
            
            while True:
                # Record audio chunk
                audio_data = await asyncio.get_event_loop().run_in_executor(
                    None, audio_handler.record_chunk
                )
                
                # Check for wake word
                if self.detect(audio_data):
                    return True
                
                # Small delay to prevent excessive CPU usage
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            logging.info("Wake word detection stopped by user")
            return False
        except Exception as e:
            raise WakeWordError(f"Error waiting for wake word: {e}")


def create_wake_word_detector(config_path: Optional[str] = None) -> WakeWordDetector:
    """
    Convenience function to create a WakeWordDetector with configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured WakeWordDetector instance
    """
    config = Config.load(config_path)
    return WakeWordDetector(config.wake_word)