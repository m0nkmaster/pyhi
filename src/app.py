import os
from datetime import datetime
import time
from typing import Optional
import pyaudio
import wave
import logging
import speech_recognition as sr
import queue
import signal
import sys
import asyncio

# Set up logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ai_assistant.log"),
        logging.StreamHandler()
    ]
)

from .conversation.ai_client import AIWrapper
from .conversation.manager import ChatConversationManager
from .mcp_manager import MCPManager
from .config import load_config
from .audio import AudioHandler, AudioError
from .wake_word import WakeWordDetector, WakeWordError

def print_with_emoji(message: str, emoji: str):
    print(f"{emoji} {message}")

class VoiceAssistant:
    def __init__(self, words: list[str], timeout_seconds: float | None = None):
        """Initialize the voice assistant using SpeechRecognition."""
        self.running = True
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True  # Enable dynamic energy threshold
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Only log essential initialization
        logging.info("API: Initializing voice assistant services")
        
        # Load unified configuration
        self.config = load_config()
        
        self.audio_handler = AudioHandler(self.config.audio)
        self.words = words
        self.timeout_seconds = timeout_seconds or self.config.timeout_seconds

        # Initialize MCP manager for tool handling
        self.mcp_manager = MCPManager(self.config.mcp) if self.config.mcp.enabled else None
        
        self.ai_client = AIWrapper(self.config.ai, mcp_manager=self.mcp_manager)
        self.conversation_manager = ChatConversationManager(
            system_prompt="You are a helpful voice assistant. Respond concisely and naturally.",
            mcp_manager=self.mcp_manager,
            ai_client=self.ai_client
        )

        try:
            self.word_detector = WakeWordDetector(self.config)
        except Exception as e:
            logging.error(f"Wake word detector initialization failed: {e}")
            raise

        # Initialize remaining components
        self.setup_audio_system()
        self.load_activation_sound()
        self.load_confirmation_sound()
        self.load_ready_sound()
        self.load_sleep_sound()

        self.is_awake = False
        self.last_interaction = None
        self.response_queue = queue.Queue()
    
    def _get_sound_path(self, filename: str) -> str:
        """Get the full path to a sound file in the assets directory."""
        from pathlib import Path
        assets_dir = Path(__file__).parent / "assets"
        return str(assets_dir / filename)

    def setup_audio_system(self):
        """Set up the audio system."""
        print_with_emoji("Setting up audio system...", "🔊")
        logging.info("Audio system initialized with unified AudioHandler")

    def load_activation_sound(self):
        """Load the activation sound file."""
        self.activation_sound_path = self._get_sound_path(self.config.audio.activation_sound)
        if not os.path.exists(self.activation_sound_path):
            logging.warning(f"Activation sound file not found at {self.activation_sound_path}")
            print_with_emoji(f"Warning: Activation sound file not found at {self.activation_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded activation sound from {self.activation_sound_path}")

    def load_confirmation_sound(self):
        """Load the confirmation sound file."""
        self.confirmation_sound_path = self._get_sound_path(self.config.audio.confirmation_sound)
        if not os.path.exists(self.confirmation_sound_path):
            logging.warning(f"Confirmation sound file not found at {self.confirmation_sound_path}")
            print_with_emoji(f"Warning: Confirmation sound file not found at {self.confirmation_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded confirmation sound from {self.confirmation_sound_path}")

    def load_ready_sound(self):
        """Load the ready sound file."""
        self.ready_sound_path = self._get_sound_path(self.config.audio.ready_sound)
        if not os.path.exists(self.ready_sound_path):
            logging.warning(f"Ready sound file not found at {self.ready_sound_path}")
            print_with_emoji(f"Warning: Ready sound file not found at {self.ready_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded ready sound from {self.ready_sound_path}")

    def load_sleep_sound(self):
        """Load the sleep mode sound file."""
        self.sleep_sound_path = self._get_sound_path(self.config.audio.sleep_sound)
        if not os.path.exists(self.sleep_sound_path):
            logging.warning(f"Sleep sound file not found at {self.sleep_sound_path}")
            print_with_emoji(f"Warning: Sleep sound file not found at {self.sleep_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded sleep sound from {self.sleep_sound_path}")

    def listen_for_command(self) -> Optional[str]:
        """Listen for a voice command and return the recognized text."""
        logging.info("Listening for command...")
        print_with_emoji("Listening for command...", "🎤")
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjust for ambient noise
            try:
                audio = self.recognizer.listen(source, timeout=5)  # Add timeout to listen
                command = self.recognizer.recognize_google(audio, show_all=False, phrase_list=self.words)
                logging.info(f"Recognized command: {command}")
                print_with_emoji(f"Recognized command: {command}", "✅")
                return command
            except sr.UnknownValueError:
                logging.warning("Could not understand audio")
                print_with_emoji("Sorry, I couldn't understand that.", "🤔")
            except sr.RequestError as e:
                logging.error(f"Could not request results; {e}")
                print_with_emoji("Speech recognition error. Please try again.", "❌")
            except sr.WaitTimeoutError:
                logging.warning("Listening timed out while waiting for phrase to start")
                print_with_emoji("Listening timed out.", "⏰")
        return None

    def run(self):
        """Run the voice assistant main loop."""
        # Initialize MCP if enabled
        if self.mcp_manager:
            logging.info("Initializing MCP servers...")
            print_with_emoji("Initializing MCP servers...", "🔧")
            try:
                # Initialize MCP manager asynchronously
                asyncio.run(self.mcp_manager.initialize())
                logging.info("MCP servers initialized successfully")
                print_with_emoji("MCP servers ready!", "✅")
            except Exception as e:
                logging.error(f"Failed to initialize MCP servers: {e}")
                print_with_emoji(f"Warning: MCP initialization failed, continuing with limited functionality", "⚠️")
        
        logging.info("Voice Assistant is ready! Say one of the trigger words to begin...")
        print_with_emoji("Voice Assistant is ready! Say one of the trigger words to begin...", "🚀")
        logging.info("Press Ctrl+C to quit")
        
        try:
            while self.running:
                # Check for timeout when awake
                if self.is_awake:
                    if self._check_timeout():
                        # Play sleep sound before going to sleep
                        logging.info("Playing sleep sound...")
                        self.audio_handler.play_sleep_sound()
                        
                        logging.info("Going back to sleep. Say a trigger word to start a new conversation.")
                        print_with_emoji("Going back to sleep. Say a trigger word to start a new conversation.", "😴")
                        self.is_awake = False
                        self.last_interaction = None
                        continue
                    time.sleep(0.1)  # Small delay to prevent CPU spinning
                
                if not self.is_awake:
                    # Listen for trigger word
                    if self._listen_for_trigger_word():
                        self.is_awake = True
                        self.last_interaction = datetime.now()
                        continue
                    else:
                        continue
                
                # Process conversation when awake
                try:
                    # Record speech using the audio handler
                    transcript = asyncio.run(self.audio_handler.record_speech())
                    
                    if not transcript or len(transcript.strip()) == 0:
                        logging.info("No speech detected")
                        continue
                    
                    # Reset timeout on valid speech
                    self.last_interaction = datetime.now()
                    logging.info(f"You said: {transcript}")
                    print_with_emoji(f"You said: {transcript}", "💬")
                    
                    # Play confirmation sound
                    self.audio_handler.play_confirmation_sound()
                    
                    # Add to conversation and get response
                    self.conversation_manager.add_user_message(transcript)
                    response = self.ai_client.get_completion(
                        self.conversation_manager.get_conversation_history()
                    )
                    
                    # Process response
                    text_response = self.conversation_manager.process_assistant_response(response)
                    
                    if text_response and len(text_response.strip()) > 0:
                        logging.info(f"Assistant: {text_response}")
                        print_with_emoji(f"Assistant: {text_response}", "🤖")
                        
                        # Convert to speech and play
                        audio_data = self.ai_client.text_to_speech(text_response)
                        if audio_data:
                            self.audio_handler.play_audio_data(audio_data, "mp3")
                        
                        # Play ready sound
                        self.audio_handler.play_ready_sound()
                        print_with_emoji("Ready for your next question!", "👂")
                    
                    # Update interaction time
                    self.last_interaction = datetime.now()
                    
                except Exception as e:
                    logging.error(f"Error processing conversation: {e}")
                    print_with_emoji("Sorry, I had trouble processing that. Please try again.", "❌")
        except Exception as e:
            logging.error(f"Error running voice assistant: {e}")
        finally:
            self._cleanup()

    def _listen_for_trigger_word(self) -> bool:
        """Listen for trigger word activation."""
        try:
            # Initialize audio stream if needed
            if not hasattr(self, '_direct_stream'):
                self._init_direct_stream()
            
            # Read and process audio
            data = self._direct_stream.read(512, exception_on_overflow=False)
            pcm = __import__('numpy').frombuffer(data, dtype=__import__('numpy').int16)
            
            # Check for wake word
            if self.word_detector.porcupine.process(pcm) >= 0:
                logging.info("Wake word detected!")
                print_with_emoji("Wake word detected!", "🎵")
                
                self.audio_handler.play_activation_sound()
                print_with_emoji("How can I help you?", "🤔")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error in wake word detection: {e}")
            return False
    
    def _init_direct_stream(self):
        """Initialize audio stream for wake word detection."""
        import pyaudio
        
        pa = pyaudio.PyAudio()
        self._direct_stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=512
        )
        logging.info("Wake word detection initialized")

    def _check_timeout(self) -> bool:
        """Check if the session should timeout."""
        if not self.last_interaction:
            return False
        
        elapsed = (datetime.now() - self.last_interaction).total_seconds()
        remaining = self.timeout_seconds - elapsed
        
        if remaining > 0:
            logging.info(f"Session timeout in: {remaining:.1f}s...")
            print_with_emoji(f"Session timeout in: {remaining:.1f}s...", "⏰")
            return False
        
        return True

    def _signal_handler(self, signal_received, frame):
        """Handle termination signals."""
        logging.info("Signal received, stopping VoiceAssistant...")
        self.running = False
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Clean up temporary files and MCP connections."""
        logging.info("Cleaning up temporary files and connections...")
        
        # Cleanup MCP servers
        if self.mcp_manager:
            try:
                asyncio.run(self.mcp_manager.shutdown())
            except Exception as e:
                logging.error(f"Error shutting down MCP servers: {e}")
        
        # Cleanup temporary files
        try:
            if os.path.exists("recording.wav"):
                os.remove("recording.wav")
            if os.path.exists("response.mp3"):
                os.remove("response.mp3")
        except Exception as e:
            logging.error(f"Error cleaning up files: {e}")

def main():
    """Main entry point."""
    config = load_config()
    assistant = VoiceAssistant(["hey chat"], config.timeout_seconds)
    assistant.run()

if __name__ == "__main__":
    exit(main())