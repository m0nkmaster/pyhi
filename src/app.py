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
from .function_manager import FunctionManager
from .mcp_manager import MCPManager
from .config import (
    AppConfig,
    AudioConfig,
    AudioPlayerConfig,
    AudioRecorderConfig,
    ChatConfig,
    WordDetectionConfig,
    AudioDeviceConfig,
    AIConfig
)
from .audio.player import PyAudioPlayer, AudioPlayerError
from .audio.recorder import PyAudioRecorder, AudioRecorderError
from .word_detection.detector import PorcupineWakeWordDetector
from .config import (
    ACTIVATION_SOUND,
    CONFIRMATION_SOUND,
    READY_SOUND,
    SLEEP_SOUND,
    get_sound_path,
)

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
        
        self.audio_recorder = PyAudioRecorder(AudioConfig())
        self.words = words
        self.timeout_seconds = timeout_seconds or 10.0  # Set default timeout

        # Initialize components
        ai_config = AIConfig()
        
        # Initialize MCP manager for modern tool handling
        app_config = AppConfig()
        if app_config.mcp_config.enabled:
            self.mcp_manager = MCPManager(app_config.mcp_config)
            # MCP initialization needs to be async, so we'll defer it
            self.function_manager = None  # Disable legacy function manager
        else:
            # Fall back to legacy function manager if MCP is disabled
            self.mcp_manager = None
            self.function_manager = FunctionManager("src/functions")
        
        self.ai_client = AIWrapper(ai_config, self.function_manager, self.mcp_manager)
        self.conversation_manager = ChatConversationManager(
            system_prompt=ChatConfig().system_prompt,
            function_manager=self.function_manager,
            mcp_manager=self.mcp_manager,
            ai_client=self.ai_client
        )

        try:
            self.word_detector = PorcupineWakeWordDetector(
                config=WordDetectionConfig(),
                audio_config=AudioConfig()
            )
        except ValueError as e:
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

    def setup_audio_system(self):
        """Set up the audio system."""
        print_with_emoji("Setting up audio system...", "🔊")
        logging.info("Setting up audio system...")

        # Initialize PyAudio
        audio = pyaudio.PyAudio()

        # Get default devices
        default_input = audio.get_default_input_device_info()['index']
        default_output = audio.get_default_output_device_info()['index']

        # Log available input devices
        print("\n🎤 Available Audio Input Devices")
        logging.info("Available Audio Input Devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                # Add tick emoji if this is the default or selected device
                is_selected = (i == default_input)
                prefix = "✅ " if is_selected else "   "
                print(f"{prefix}Index {i}: {device_info['name']}")
                logging.info(f"Input Device - Index {i}: {device_info['name']}{' (Selected)' if is_selected else ''}")

        print()  # Add a blank line for better readability

        # Initialize audio player with list_devices_on_start=False since we'll list devices ourselves
        self.audio_player = PyAudioPlayer(
            on_error=lambda e: logging.error(f"Audio playback error: {e}"),
            config=AudioPlayerConfig(),
            device_config=AudioDeviceConfig(list_devices_on_start=False)
        )

        # Log available output devices
        print("🔊 Available Audio Output Devices")
        logging.info("Available Audio Output Devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxOutputChannels'] > 0:
                # Add tick emoji if this is the default or selected device
                is_selected = (i == default_output or i == self.audio_player.config.output_device_index)
                prefix = "✅ " if is_selected else "   "
                print(f"{prefix}Index {i}: {device_info['name']}")
                logging.info(f"Output Device - Index {i}: {device_info['name']}{' (Selected)' if is_selected else ''}")

        print()  # Add a blank line for better readability

    def load_activation_sound(self):
        """Load the activation sound file."""
        self.activation_sound_path = get_sound_path(ACTIVATION_SOUND)
        if not os.path.exists(self.activation_sound_path):
            logging.warning(f"Activation sound file not found at {self.activation_sound_path}")
            print_with_emoji(f"Warning: Activation sound file not found at {self.activation_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded activation sound from {self.activation_sound_path}")

    def load_confirmation_sound(self):
        """Load the confirmation sound file."""
        self.confirmation_sound_path = get_sound_path(CONFIRMATION_SOUND)
        if not os.path.exists(self.confirmation_sound_path):
            logging.warning(f"Confirmation sound file not found at {self.confirmation_sound_path}")
            print_with_emoji(f"Warning: Confirmation sound file not found at {self.confirmation_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded confirmation sound from {self.confirmation_sound_path}")

    def load_ready_sound(self):
        """Load the ready sound file."""
        self.ready_sound_path = get_sound_path(READY_SOUND)
        if not os.path.exists(self.ready_sound_path):
            logging.warning(f"Ready sound file not found at {self.ready_sound_path}")
            print_with_emoji(f"Warning: Ready sound file not found at {self.ready_sound_path}", "⚠️")
        else:
            logging.info(f"Loaded ready sound from {self.ready_sound_path}")

    def load_sleep_sound(self):
        """Load the sleep mode sound file."""
        self.sleep_sound_path = get_sound_path(SLEEP_SOUND)
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
                        if self.sleep_sound_path and os.path.exists(self.sleep_sound_path):
                            logging.info("Playing sleep sound...")
                            self.audio_player.play(self.sleep_sound_path, volume=1.0)
                        
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
                logging.info("Recording user input...")
                print_with_emoji("Recording user input...", "🎤")
                
                # Clear any previous audio buffer
                self.audio_recorder.clear_buffer()
                
                # Record audio without resetting timeout
                audio_data = self.audio_recorder.record_speech()
                if not audio_data:  # No speech detected
                    # Check for timeout without resetting last_interaction
                    if self._check_timeout():
                        continue
                    continue
                
                # Save audio with consistent format
                with wave.open("recording.wav", "wb") as wf:
                    wf.setnchannels(self.audio_recorder.config.channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(self.audio_recorder.config.sample_rate)
                    wf.writeframes(audio_data)
                logging.info("Audio recorded and saved")

                # Convert speech to text using speech_recognition
                try:
                    with sr.AudioFile("recording.wav") as source:
                        audio = self.recognizer.record(source)
                        try:
                            # Increase the recognition timeout and make it more strict
                            transcript = self.recognizer.recognize_google(
                                audio,
                                show_all=False,  # Only return most confident result
                            )
                            if not transcript or len(transcript.strip()) == 0:
                                logging.info("Empty transcript received")
                                # Check for timeout without resetting last_interaction
                                if self._check_timeout():
                                    continue
                                continue
                                
                            # Only reset the timeout counter when we get valid speech
                            self.last_interaction = datetime.now()
                            logging.info(f"You said: {transcript}")
                            
                            # Add message to conversation history immediately
                            self.conversation_manager.add_user_message(transcript)

                            # Start playing confirmation sound non-blocking while waiting for API
                            confirmation_sound_path = get_sound_path(CONFIRMATION_SOUND)
                            if os.path.exists(confirmation_sound_path):
                                print(f"[{datetime.now()}] Starting confirmation sound...")
                                self.audio_player.play(confirmation_sound_path, volume=0.5, block=False)
                                print(f"[{datetime.now()}] Confirmation sound started")

                            # Start API call immediately
                            print(f"[{datetime.now()}] Starting API call...")
                            logging.info("Getting assistant response...")
                            
                            # Print the message being sent to the API
                            print(f"Message sent to API: {self.conversation_manager.get_conversation_history()}")

                            # Make the API call
                            response = self.ai_client.get_completion(
                                self.conversation_manager.get_conversation_history()
                            )
                            logging.info(f"API Response: {response}")
                            
                            # Process the response and handle any function calls
                            text_response = self.conversation_manager.process_assistant_response(response)
                            
                            # Skip TTS if response is empty
                            if not text_response or len(text_response.strip()) == 0:
                                logging.warning("Empty text response received from AI, skipping TTS")
                                continue
                            
                            # Convert text response to speech
                            logging.info("Converting response to speech...")
                            print(f"[{datetime.now()}] Converting to speech...")
                            audio_data = self.ai_client.text_to_speech(text_response)
                            print(f"[{datetime.now()}] Got audio data, length: {len(audio_data)} bytes")
                            
                            if audio_data:
                                # Only stop confirmation sound when we're ready to play the response
                                print(f"[{datetime.now()}] Stopping confirmation sound...")
                                self.audio_player.stop()
                                print(f"[{datetime.now()}] Confirmation sound stopped")
                                
                                # Small pause to let the audio system stabilize
                                time.sleep(0.2)
                                
                                # Play the response
                                print(f"[{datetime.now()}] Starting TTS playback")
                                self.audio_player.play(audio_data, block=True)
                                print(f"[{datetime.now()}] TTS playback complete")
                                
                                # Small pause before ready sound
                                time.sleep(0.2)
                                
                                # Play ready sound
                                if self.ready_sound_path and os.path.exists(self.ready_sound_path):
                                    print(f"[{datetime.now()}] Playing ready sound...")
                                    self.audio_player.play(self.ready_sound_path, volume=1.0, block=True)
                                    print(f"[{datetime.now()}] Ready sound complete")
                                    print_with_emoji("Ready for your next question!", "👂")
                                
                                # Only update last interaction after all sounds are complete
                                self.last_interaction = datetime.now()
                            else:
                                logging.error("Failed to get audio data from TTS")
                                print(f"[{datetime.now()}] No audio data received from TTS")
                        except sr.UnknownValueError:
                            logging.error("Speech recognition failed: Could not understand audio")
                            print_with_emoji("Sorry, I couldn't understand that. Could you try again?", "🤔")
                        except sr.RequestError as e:
                            logging.error(f"Speech recognition request failed: {e}")
                            print_with_emoji("Speech recognition error. Please try again.", "❌")
                except Exception as e:
                    logging.error(f"Processing error: {e}")
        except Exception as e:
            logging.error(f"Error running voice assistant: {e}")
        finally:
            self._cleanup()

    def _listen_for_trigger_word(self) -> bool:
        """Listen for trigger word activation."""
        # Only log at debug level for continuous operations
        # logging.debug("Listening for trigger word...")
        audio_data = self.audio_recorder.record_chunk()
        
        if not audio_data:
            return False
        
        # Check for trigger word
        if self.word_detector.detect(audio_data):
            try:
                logging.info("Trigger word detected! Playing activation sound...")
                print_with_emoji("Trigger word detected! Playing activation sound...", "🎵")
                if self.activation_sound_path:
                    self.audio_player.play(self.activation_sound_path)
            except AudioPlayerError:
                logging.error("Failed to play activation sound")
            
            # Give a small pause after the activation sound
            time.sleep(0.2)
            
            logging.info("Trigger word detected! How can I help you?")
            print_with_emoji("Trigger word detected! How can I help you?", "🤔")
            return True
        
        return False

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
        if self.audio_recorder and self.audio_recorder.stream:
            self.audio_recorder.stream.stop_stream()
            self.audio_recorder.stream.close()
        if hasattr(self.audio_recorder, 'audio'):
            self.audio_recorder.audio.terminate()
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
    config = AppConfig()
    assistant = VoiceAssistant(config.words)
    assistant.run()

if __name__ == "__main__":
    exit(main())