import os
from datetime import datetime
import time
from typing import Optional
import pyaudio
from openai import OpenAI
import wave

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
from .triggers import (
    TriggerManager,
    WakeWordTrigger,
    WakeWordTriggerConfig,
    BluetoothTrigger,
    BluetoothTriggerConfig
)

class VoiceAssistant:
    """Voice assistant implementation."""
    
    def __init__(self, words: list[str], timeout_seconds: float | None = None):
        """Initialize the voice assistant."""
        # Initialize configurations
        self.app_config = AppConfig(
            words=words,
            timeout_seconds=timeout_seconds or AppConfig().timeout_seconds,
            temp_recording_path="recording.wav",
            temp_response_path="response.mp3"
        )
        
        self.audio_config = AudioConfig()
        self.audio_player_config = AudioPlayerConfig()
        
        print("Initializing OpenAI client...")
        openai_client = OpenAI()
        
        print("Initializing components...")
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
        
        # Initialize trigger manager and triggers
        self.trigger_manager = TriggerManager()
        
        # Add wake word trigger
        wake_word_trigger = WakeWordTrigger(
            openai_client=openai_client,
            config=WakeWordTriggerConfig(
                words=words,
                audio_config=self.audio_config,
                word_detection_config=WordDetectionConfig()
            )
        )
        self.trigger_manager.add_trigger(wake_word_trigger)
        
        # Add Bluetooth trigger if configured
        bluetooth_config = BluetoothTriggerConfig(
            device_name="PyHi Button",  # Replace with your button's name
            characteristic_uuid="0000FFE1-0000-1000-8000-00805F9B34FB"  # Replace with your characteristic UUID
        )
        bluetooth_trigger = BluetoothTrigger(config=bluetooth_config)
        self.trigger_manager.add_trigger(bluetooth_trigger)
        
        print("Setting up audio system...")
        self.audio_player = SystemAudioPlayer(
            on_error=lambda e: print(f"Audio playback error: {e}"),
            config=self.audio_player_config
        )
        
        self.audio_recorder = PyAudioRecorder(
            config=self.audio_config,
            analyzer=self,
            on_error=lambda e: print(f"Recording error: {e}"),
            recorder_config=AudioRecorderConfig()
        )
        
        # Initialize state
        self.is_awake = False
        self.last_interaction: Optional[datetime] = None
        
        # Load activation sound
        print("Loading activation sound...")
        try:
            with open(self.audio_player_config.activation_sound_path, "rb") as f:
                self.activation_sound = f.read()
            print("Activation sound loaded successfully!")
        except FileNotFoundError:
            print(f"Warning: {self.audio_player_config.activation_sound_path} not found. No activation sound will be played.")
            self.activation_sound = None
        
        # Set up wake callback
        self.trigger_manager.set_wake_callback(self._on_wake_trigger)
    
    def is_speech(self, audio_data: bytes, config: AudioConfig) -> bool:
        """Implement AudioAnalyzer protocol."""
        try:
            result = is_speech(audio_data, config)
            if result:
                print("\rSpeech detected!", end="", flush=True)
            return result
        except Exception as e:
            print(f"\rSpeech detection error: {e}", end="", flush=True)
            return False
    
    def _on_wake_trigger(self) -> None:
        """Handle wake trigger activation."""
        try:
            print("\nTrigger activated! Playing activation sound...")
            if self.activation_sound:
                self.audio_player.play(self.activation_sound)
        except AudioPlayerError:
            print("Failed to play activation sound")
        
        print("\nHow can I help you?")
        self.is_awake = True
        self.last_interaction = datetime.now()
    
    def run(self):
        """Run the voice assistant main loop."""
        print(f"Voice Assistant is ready! Use wake word or Bluetooth button to begin...")
        print("Press Ctrl+C to quit")
        
        try:
            # Start all triggers
            self.trigger_manager.start_all()
            
            while True:
                # Check for timeout when awake
                if self.is_awake:
                    if self._check_timeout():
                        print("\nGoing back to sleep. Use wake word or button to start a new conversation.")
                        self.is_awake = False
                        self.last_interaction = None
                        continue
                    
                    # Process conversation when awake
                    print("\nRecording user input...")
                    audio_data = self._record_user_input()
                    if not audio_data:  # No speech detected
                        print("No speech detected in recording")
                        continue
                    
                    print("Transcribing audio...")
                    transcript = self.openai_wrapper.transcribe_audio("recording.wav")
                    if not transcript:
                        print("Failed to transcribe audio")
                        continue
                    
                    print(f"\nYou said: {transcript}")
                    
                    # Get assistant response
                    print("Getting assistant response...")
                    self.conversation_manager.add_user_message(transcript)
                    response = self.openai_wrapper.get_chat_completion(
                        self.conversation_manager.get_conversation_history()
                    )
                    
                    if response:
                        print(f"Assistant: {response}")
                        self.conversation_manager.add_assistant_message(response)
                        
                        # Convert response to speech and play it
                        print("Converting response to speech...")
                        audio_data = self.openai_wrapper.text_to_speech(response)
                        if audio_data:
                            try:
                                print("Playing response...")
                                self.audio_player.play(audio_data)
                                print("Response playback complete")
                            except AudioPlayerError as e:
                                print(f"Error playing response: {e}")
                        
                        self.last_interaction = datetime.now()
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self._cleanup()
    
    def _record_user_input(self) -> Optional[bytes]:
        """Record user input with silence detection."""
        print("\nListening for your question...")
        
        self.audio_recorder.start_recording()
        audio_data = self.audio_recorder.stop_recording(is_wake_word_mode=False)
        
        if audio_data:
            # Save audio with consistent format
            with wave.open("recording.wav", "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(audio_data)
            print("Audio recorded and saved")
        else:
            print("No audio recorded")
        
        return audio_data
    
    def _check_timeout(self) -> bool:
        """Check if the session should timeout."""
        if not self.last_interaction:
            return False
        
        elapsed = (datetime.now() - self.last_interaction).total_seconds()
        remaining = self.app_config.timeout_seconds - elapsed
        
        if remaining > 0:
            print(f"\rSession timeout in: {remaining:.1f}s...", end="", flush=True)
            return False
        
        return True
    
    def _cleanup(self):
        """Clean up resources."""
        self.trigger_manager.stop_all()
        print("\nCleaning up temporary files...")
        for file in ["recording.wav", "response.mp3"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    print(f"Removed {file}")
                except Exception as e:
                    print(f"Failed to remove {file}: {e}")

def main():
    """Main entry point."""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
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
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 