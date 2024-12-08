import os
from datetime import datetime
import time
from typing import Optional
import pyaudio
from openai import OpenAI
import wave
import logging

# Configure logging
logging.basicConfig(
    filename='voice_assistant.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from .audio.analyzer import is_speech
from .audio.recorder import PyAudioRecorder
from .audio.player import SystemAudioPlayer, AudioPlayerError
from .word_detection.detector import WhisperWordDetector
from .conversation.manager import ChatConversationManager
from .conversation.openai_client import OpenAIWrapper
from .config import (
    AudioConfig,
    AudioRecorderConfig,
    ChatConfig,
    TTSConfig,
    AppConfig,
    AudioPlayerConfig,
    WordDetectionConfig
)

def print_with_emoji(message: str, emoji: str):
    print(f"{emoji} {message}")

class VoiceAssistant:
    def __init__(self, words: list[str], timeout_seconds: float | None = None):
        """Initialize the voice assistant."""
        logging.info("Initializing VoiceAssistant...")
        print_with_emoji("Initializing VoiceAssistant...", "🤖")
        self.initialize_configurations(words, timeout_seconds)
        self.initialize_openai_client()
        self.setup_audio_system()
        self.load_activation_sound()
        
        # Initialize state
        self.is_awake = False
        self.last_interaction: Optional[datetime] = None

    def initialize_configurations(self, words: list[str], timeout_seconds: float | None):
        """Initialize configurations for the voice assistant."""
        self.app_config = AppConfig(
            words=words,
            timeout_seconds=timeout_seconds or AppConfig().timeout_seconds,
            temp_recording_path="recording.wav",
            temp_response_path="response.mp3"
        )
        self.audio_config = AudioConfig()
        self.audio_player_config = AudioPlayerConfig()

    def initialize_openai_client(self):
        """Initialize OpenAI client and related components."""
        logging.info("Initializing OpenAI client...")
        print_with_emoji("Initializing OpenAI client...", "🔧")
        openai_client = OpenAI()
        
        logging.info("Initializing components...")
        print_with_emoji("Initializing components...", "🔧")
        self.openai_wrapper = OpenAIWrapper(
            client=openai_client,
            chat_config=ChatConfig(),
            tts_config=TTSConfig()
        )
        
        # Initialize conversation manager
        self.chat_config = ChatConfig()
        self.conversation_manager = ChatConversationManager(
            system_prompt=self.chat_config.system_prompt
        )
        
        self.word_detector = WhisperWordDetector(
            client=openai_client,
            words=self.app_config.words,
            config=WordDetectionConfig(),
            audio_config=self.audio_config
        )

    def setup_audio_system(self):
        """Setup the audio system for playback and recording."""
        logging.info("Setting up audio system...")
        print_with_emoji("Setting up audio system...", "🔊")
        
        # Initialize audio player
        self.audio_player = SystemAudioPlayer(
            on_error=lambda e: logging.error(f"Audio playback error: {e}"),
            config=self.audio_player_config
        )
        
        # Get and log output device info
        if self.audio_player_config.output_device_index is not None:
            try:
                pa = pyaudio.PyAudio()
                dev_info = pa.get_device_info_by_index(self.audio_player_config.output_device_index)
                print_with_emoji(f"Using output device: {dev_info.get('name', 'Unknown')}", "🔈")
                pa.terminate()
            except Exception as e:
                logging.warning(f"Could not get output device info: {e}")
        
        # Initialize audio recorder
        self.audio_recorder = PyAudioRecorder(
            config=self.audio_config,
            analyzer=self,
            on_error=lambda e: logging.error(f"Recording error: {e}"),
            recorder_config=AudioRecorderConfig()
        )
        
        # Get and log input device info
        if self.audio_config.input_device_index is not None:
            try:
                pa = pyaudio.PyAudio()
                dev_info = pa.get_device_info_by_index(self.audio_config.input_device_index)
                print_with_emoji(f"Using input device: {dev_info.get('name', 'Unknown')}", "🎤")
                pa.terminate()
            except Exception as e:
                logging.warning(f"Could not get input device info: {e}")

    def load_activation_sound(self):
        """Load the activation sound for the voice assistant."""
        logging.info("Loading activation sound...")
        print_with_emoji("Loading activation sound...", "🎵")
        try:
            with open(self.audio_player_config.activation_sound_path, "rb") as f:
                self.activation_sound = f.read()
            logging.info("Activation sound loaded successfully!")
            print_with_emoji("Activation sound loaded successfully!", "✅")
        except FileNotFoundError:
            logging.warning(f"{self.audio_player_config.activation_sound_path} not found. No activation sound will be played.")
            print_with_emoji(f"{self.audio_player_config.activation_sound_path} not found. No activation sound will be played.", "⚠️")
            self.activation_sound = None

    def is_speech(self, audio_data: bytes, config: AudioConfig) -> bool:
        """Implement AudioAnalyzer protocol."""
        try:
            result = is_speech(audio_data, config)
            if result:
                logging.info("Speech detected!")
                print_with_emoji("Speech detected!", "🗣️")
            return result
        except Exception as e:
            logging.error(f"Speech detection error: {e}")
            print_with_emoji(f"Speech detection error: {e}", "❌")
            return False

    def run(self):
        """Run the voice assistant main loop."""
        logging.info("Voice Assistant is ready! Say one of the trigger words to begin...")
        print_with_emoji("Voice Assistant is ready! Say one of the trigger words to begin...", "🚀")
        logging.info(f"Detection words: {', '.join(self.word_detector.words)}")
        logging.info("Press Ctrl+C to quit")
        
        try:
            while True:
                # Check for timeout when awake
                if self.is_awake:
                    if self._check_timeout():
                        logging.info("Going back to sleep. Say a trigger word to start a new conversation.")
                        print_with_emoji("Going back to sleep. Say a trigger word to start a new conversation.", "😴")
                        self.is_awake = False
                        self.last_interaction = None
                        continue
                    time.sleep(0.1)  # Small delay to prevent CPU spinning
                
                if not self.is_awake:
                    # Listen for trigger word
                    logging.info("Starting trigger word detection cycle...")
                    print_with_emoji("Starting trigger word detection cycle...", "👂")
                    if self._listen_for_trigger_word():
                        self.is_awake = True
                        self.last_interaction = datetime.now()
                        continue
                    else:
                        continue
                
                # Process conversation when awake
                logging.info("Recording user input...")
                print_with_emoji("Recording user input...", "🎤")
                audio_data = self._record_user_input()
                if not audio_data:  # No speech detected
                    logging.info("No speech detected in recording")
                    continue
                
                logging.info("Transcribing audio...")
                transcript = self.openai_wrapper.transcribe_audio("recording.wav")
                if not transcript:
                    logging.info("Failed to transcribe audio")
                    continue
                
                logging.info(f"\nYou said: {transcript}")
                
                # Get assistant response
                logging.info("Getting assistant response...")
                self.conversation_manager.add_user_message(transcript)
                response = self.openai_wrapper.get_chat_completion(
                    self.conversation_manager.get_conversation_history()
                )
                
                if response:
                    logging.info(f"Assistant: {response}")
                    self.conversation_manager.add_assistant_message(response)
                    
                    # Convert response to speech and play it
                    logging.info("Converting response to speech...")
                    audio_data = self.openai_wrapper.text_to_speech(response)
                    if audio_data:
                        try:
                            logging.info("Playing response...")
                            self.audio_player.play(audio_data)
                            logging.info("Response playback complete")
                        except AudioPlayerError as e:
                            logging.error(f"Error playing response: {e}")
                    
                    self.last_interaction = datetime.now()
        
        except KeyboardInterrupt:
            logging.info("Shutting down...")
            print_with_emoji("Shutting down...", "🔌")
        finally:
            self._cleanup()

    def _listen_for_trigger_word(self) -> bool:
        """Listen for trigger word activation."""
        logging.info("Listening for trigger word...")
        print_with_emoji("Listening for trigger word...", "👂")
        self.audio_recorder.start_recording()
        audio_data = self.audio_recorder.stop_recording(is_wake_word_mode=True)
        
        if not audio_data:
            logging.info("No audio data recorded")
            return False
        
        # Save audio for trigger word detection
        with open("recording.wav", "wb") as f:
            f.write(audio_data)
        
        # Check for trigger word
        if self.word_detector.detect(audio_data):
            try:
                logging.info("Trigger word detected! Playing activation sound...")
                print_with_emoji("Trigger word detected! Playing activation sound...", "🎵")
                self.audio_player.play(self.activation_sound)
            except AudioPlayerError:
                logging.error("Failed to play activation sound")
            logging.info("Trigger word detected! How can I help you?")
            print_with_emoji("Trigger word detected! How can I help you?", "🤔")
            return True
        
        return False

    def _record_user_input(self) -> Optional[bytes]:
        """Record user input with silence detection."""
        logging.info("Listening for your question...")
        print_with_emoji("Listening for your question...", "🎤")
        
        self.audio_recorder.start_recording()
        audio_data = self.audio_recorder.stop_recording(is_wake_word_mode=False)
        
        if audio_data:
            # Save audio with consistent format
            with wave.open("recording.wav", "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(audio_data)
            logging.info("Audio recorded and saved")
        else:
            logging.info("No audio recorded")
        
        return audio_data

    def _check_timeout(self) -> bool:
        """Check if the session should timeout."""
        if not self.last_interaction:
            return False
        
        elapsed = (datetime.now() - self.last_interaction).total_seconds()
        remaining = self.app_config.timeout_seconds - elapsed
        
        if remaining > 0:
            logging.info(f"Session timeout in: {remaining:.1f}s...")
            print_with_emoji(f"Session timeout in: {remaining:.1f}s...", "⏰")
            return False
        
        return True

    def _cleanup(self):
        """Clean up temporary files."""
        logging.info("Cleaning up temporary files...")
        print_with_emoji("Cleaning up temporary files...", "🧹")
        for file in ["recording.wav", "response.mp3"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    logging.info(f"Removed {file}")
                except Exception as e:
                    logging.error(f"Failed to remove {file}: {e}")

def main():
    """Main entry point."""
    if not os.getenv("OPENAI_API_KEY"):
        logging.error("Error: OPENAI_API_KEY not found in environment variables")
        return 1
    
    try:
        # Create AppConfig with default configuration
        app_config = AppConfig()
        
        # Initialize assistant with config values
        assistant = VoiceAssistant(
            words=app_config.words,
            timeout_seconds=app_config.timeout_seconds
        )
        assistant.run()
        return 0
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 