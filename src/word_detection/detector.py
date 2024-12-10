from typing import List, Optional
import pvporcupine
import numpy as np
import os
import logging
from ..utils.types import WordDetector, AudioConfig
from ..config import WordDetectionConfig

class PorcupineWakeWordDetector(WordDetector):
    def __init__(
        self,
        config: Optional[WordDetectionConfig] = None,
        audio_config: Optional[AudioConfig] = None
    ):
        """Initialize the Porcupine-based wake word detector."""
        self.audio_config = audio_config or AudioConfig()
        self.config = config or WordDetectionConfig()
        
        # Get access key from environment
        access_key = os.getenv("PICOVOICE_API_KEY")
        if not access_key:
            raise ValueError("PICOVOICE_API_KEY environment variable not set")
        
        try:
            # Get the absolute path to the model file
            model_path = self.config.model_path
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found at {model_path}")
            
            # Initialize Porcupine with model file path
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[model_path]  # Pass as a list with the absolute path
            )
            logging.info(f"Initialized Porcupine with wake word model: {model_path}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Porcupine: {str(e)}")

    def detect(self, audio_data: bytes) -> bool:
        """Detect if the wake word is present in the audio data."""
        try:
            # Convert bytes to int16 array
            pcm = np.frombuffer(audio_data, dtype=np.int16)
            
            # Process the audio in frame-sized chunks
            for i in range(0, len(pcm) - self.porcupine.frame_length + 1, self.porcupine.frame_length):
                frame = pcm[i:i + self.porcupine.frame_length]
                if len(frame) == self.porcupine.frame_length:  # Only process complete frames
                    if self.porcupine.process(frame) >= 0:
                        return True
            return False
            
        except Exception as e:
            logging.error(f"Error in wake word detection: {e}")
            return False
            
    def __del__(self):
        """Clean up Porcupine resources."""
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()
