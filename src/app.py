import os
from datetime import datetime
import time
from typing import Optional
import pyaudio
from openai import OpenAI
import wave
import logging
import speech_recognition as sr
import threading
import queue

# Configure logging
logging.basicConfig(
    filename='voice_assistant.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from .audio.recorder import PyAudioRecorder
from .audio.player import SystemAudioPlayer, AudioPlayerError
from .word_detection.detector import PorcupineWakeWordDetector
from .conversation.manager import ChatConversationManager
from .conversation.openai_client import OpenAIWrapper
from .config import (
    AudioConfig,
    AudioRecorderConfig,
    ChatConfig,
    TTSConfig,
    AppConfig,
    AudioPlayerConfig,
    WordDetectionConfig,
    AudioDeviceConfig,
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
        """Initialize the voice assistant."""
        logging.info("Initializing VoiceAssistant...")
        print_with_emoji("Initializing VoiceAssistant...", "🤖")
        
        # Warn about speech recognition limitations
        print_with_emoji("Note: Using free Google Speech Recognition API (limited to ~50 requests/day)", "ℹ️")
        logging.warning("Using free Google Speech Recognition API with daily request limits")
        
        self.initialize_configurations(words, timeout_seconds)
        self.initialize_openai_client()
        self.setup_audio_system()
        self.load_activation_sound()
        self.load_confirmation_sound()
        self.load_ready_sound()
        self.load_sleep_sound()
        
        # Initialize state
        self.is_awake = False
        self.last_interaction: Optional[datetime] = None
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        self.response_queue = queue.Queue()

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
        """Initialize OpenAI client and components."""
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
        
        # Initialize wake word detector with Porcupine
        try:
            self.word_detector = PorcupineWakeWordDetector(
                config=WordDetectionConfig(),
                audio_config=self.audio_config
            )
            logging.info("Wake word detector initialized successfully!")
            print_with_emoji("Wake word detector initialized successfully!", "✅")
        except ValueError as e:
            logging.error(f"Error initializing wake word detector: {e}")
            print_with_emoji(f"Error initializing wake word detector: {e}", "❌")
            raise

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
        self.audio_player = SystemAudioPlayer(
            on_error=lambda e: logging.error(f"Audio playback error: {e}"),
            config=self.audio_player_config,
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

        # Initialize audio recorder
        self.audio_recorder = PyAudioRecorder(
            config=self.audio_config,
            recorder_config=AudioRecorderConfig()
        )

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

    def run(self):
        """Run the voice assistant main loop."""
        logging.info("Voice Assistant is ready! Say one of the trigger words to begin...")
        print_with_emoji("Voice Assistant is ready! Say one of the trigger words to begin...", "🚀")
        logging.info("Press Ctrl+C to quit")
        
        try:
            while True:
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
                    wf.setnchannels(self.audio_config.channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(self.audio_config.sample_rate)
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
                            if self.confirmation_sound_path and os.path.exists(self.confirmation_sound_path):
                                print(f"[{datetime.now()}] Starting confirmation sound...")
                                self.audio_player.play(self.confirmation_sound_path, volume=1.0, block=False)
                                print(f"[{datetime.now()}] Confirmation sound started")

                            # Start API call immediately
                            print(f"[{datetime.now()}] Starting API call...")
                            logging.info("Getting assistant response...")
                            
                            # Make the API call
                            response = self.openai_wrapper.get_chat_completion(
                                self.conversation_manager.get_conversation_history()
                            )
                            print(f"[{datetime.now()}] Got API response")
                            
                            # Convert response to speech and play it
                            logging.info("Converting response to speech...")
                            audio_data = self.openai_wrapper.text_to_speech(response)
                            if audio_data:
                                try:
                                    logging.info("Playing response...")
                                    self.audio_player.play(audio_data, block=True)  # Block for TTS
                                    logging.info("Response playback complete")
                                    
                                    # Stop the confirmation sound as soon as we get the response
                                    print(f"[{datetime.now()}] Stopping confirmation sound...")
                                    self.audio_player.stop()
                                    print(f"[{datetime.now()}] Confirmation sound stopped")
                                    
                                    # Play ready sound after TTS finishes
                                    if self.ready_sound_path and os.path.exists(self.ready_sound_path):
                                        print(f"[{datetime.now()}] Playing ready sound...")
                                        self.audio_player.play(self.ready_sound_path, volume=1.0, block=True)
                                        print(f"[{datetime.now()}] Ready sound complete")
                                        print_with_emoji("Ready for your next question!", "👂")
                                        
                                    # Only update last interaction after all sounds are complete
                                    self.last_interaction = datetime.now()
                                    
                                except AudioPlayerError as e:
                                    logging.error(f"Error playing response: {e}")
                        except sr.UnknownValueError:
                            logging.info("Could not understand audio")
                            print_with_emoji("Sorry, I couldn't understand that. Could you try again?", "🤔")
                        except sr.RequestError as e:
                            if "recognition request failed" in str(e):
                                logging.error("Daily limit for free Google Speech Recognition may have been reached")
                                print_with_emoji("Speech recognition limit reached. Consider upgrading to Google Cloud Speech API", "⚠️")
                            else:
                                logging.error(f"Could not request results; {e}")
                                print_with_emoji("Speech recognition error. Please try again.", "❌")
                except Exception as e:
                    logging.error(f"Error processing audio: {e}")
        except KeyboardInterrupt:
            logging.info("Shutting down...")
            print_with_emoji("Shutting down...", "🔌")
        finally:
            self._cleanup()

    def _listen_for_trigger_word(self) -> bool:
        """Listen for trigger word activation."""
        # Only log at debug level for continuous operations
        logging.debug("Listening for trigger word...")
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

    def _record_user_input(self) -> Optional[str]:
        """Record user input with silence detection."""
        logging.info("Listening for your question...")
        print_with_emoji("Listening for your question...", "🎤")
        
        # Clear any previous audio buffer
        self.audio_recorder.clear_buffer()
        
        audio_data = self.audio_recorder.record_speech()
        if not audio_data:  # No speech detected
            return None
        
        # Save audio with consistent format
        with wave.open("recording.wav", "wb") as wf:
            wf.setnchannels(self.audio_config.channels)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(self.audio_config.sample_rate)
            wf.writeframes(audio_data)
        logging.info("Audio recorded and saved")

        # Convert speech to text using speech_recognition
        try:
            with sr.AudioFile("recording.wav") as source:
                audio = self.recognizer.record(source)
                try:
                    transcript = self.recognizer.recognize_google(audio)
                    logging.info(f"You said: {transcript}")
                    
                    # Only play confirmation sound if we got valid speech
                    if self.confirmation_sound_path and os.path.exists(self.confirmation_sound_path):
                        logging.info(f"Playing confirmation sound from {self.confirmation_sound_path}")
                        print_with_emoji("Processing your question...", "⚙️")
                        self.audio_player.play(self.confirmation_sound_path, volume=1.0)
                    
                    return transcript
                except sr.UnknownValueError:
                    logging.info("Could not understand audio")
                    print_with_emoji("Sorry, I couldn't understand that. Could you try again?", "🤔")
                    return None
                except sr.RequestError as e:
                    if "recognition request failed" in str(e):
                        logging.error("Daily limit for free Google Speech Recognition may have been reached")
                        print_with_emoji("Speech recognition limit reached. Consider upgrading to Google Cloud Speech API", "⚠️")
                    else:
                        logging.error(f"Could not request results; {e}")
                        print_with_emoji("Speech recognition error. Please try again.", "❌")
                    return None
        except Exception as e:
            logging.error(f"Error processing audio: {e}")
            return None

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
        try:
            if os.path.exists(self.app_config.temp_recording_path):
                os.remove(self.app_config.temp_recording_path)
            if os.path.exists(self.app_config.temp_response_path):
                os.remove(self.app_config.temp_response_path)
        except Exception as e:
            logging.error(f"Error cleaning up files: {e}")

def main():
    """Main entry point."""
    config = AppConfig()
    assistant = VoiceAssistant(config.words)
    assistant.run()

if __name__ == "__main__":
    exit(main())