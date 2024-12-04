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
from .wake_word.detector import WhisperWakeWordDetector
from .conversation.manager import ChatConversationManager
from .conversation.openai_client import OpenAIWrapper
from .config import (
    AudioConfig,
    AudioRecorderConfig,
    ChatConfig,
    TTSConfig,
    AppConfig,
    AudioPlayerConfig,
    WakeWordConfig
)

class VoiceAssistant:
    def __init__(self, wake_words: list[str], timeout_seconds: float = 30.0):
        """Initialize the voice assistant."""
        # Initialize configurations
        self.app_config = AppConfig(
            timeout_seconds=timeout_seconds,
            wake_words=wake_words
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
        self.conversation_manager = ChatConversationManager(
            system_prompt="You are a helpful voice assistant. Please keep your responses concise and natural."
        )
        
        self.wake_word_detector = WhisperWakeWordDetector(
            client=openai_client,
            wake_words=wake_words,
            config=WakeWordConfig(),
            audio_config=self.audio_config
        )
        
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
    
    def is_speech(self, audio_data: bytes, config: AudioConfig) -> bool:
        """Implement AudioAnalyzer protocol."""
        result = is_speech(audio_data, config)
        if result:
            print("\rSpeech detected!", end="", flush=True)
        return result
    
    def run(self):
        """Run the voice assistant main loop."""
        print(f"Voice Assistant is ready! Say one of the wake words to begin...")
        print(f"Wake words: {', '.join(self.wake_word_detector.wake_words)}")
        print("Press Ctrl+C to quit")
        
        try:
            while True:
                # Check for timeout when awake
                if self.is_awake:
                    if self._check_timeout():
                        print("\nGoing back to sleep. Say a wake word to start a new conversation.")
                        self.is_awake = False
                        self.last_interaction = None
                        continue
                    time.sleep(0.1)  # Small delay to prevent CPU spinning
                
                if not self.is_awake:
                    # Listen for wake word
                    print("\nStarting wake word detection cycle...")
                    if self._listen_for_wake_word():
                        self.is_awake = True
                        self.last_interaction = datetime.now()
                        continue
                    else:
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
                    if self.openai_wrapper.text_to_speech(response):
                        try:
                            print("Playing response...")
                            # Read the entire MP3 file
                            with open("response.mp3", "rb") as f:
                                audio_data = f.read()
                            self.audio_player.play(audio_data)
                            print("Response playback complete")
                        except AudioPlayerError as e:
                            print(f"Error playing response: {e}")
                    
                    self.last_interaction = datetime.now()
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self._cleanup()
    
    def _listen_for_wake_word(self) -> bool:
        """Listen for wake word activation."""
        print("\rListening for wake word...", end="", flush=True)
        
        self.audio_recorder.start_recording()
        audio_data = self.audio_recorder.stop_recording(is_wake_word_mode=True)
        
        if not audio_data:
            print("No audio data recorded")
            return False
        
        # Save audio for wake word detection
        with open("recording.wav", "wb") as f:
            f.write(audio_data)
        
        # Check for wake word
        if self.wake_word_detector.detect(audio_data):
            try:
                print("Wake word detected! Playing activation sound...")
                self.audio_player.play(self.activation_sound)
            except AudioPlayerError:
                print("Failed to play activation sound")
            print("\nWake word detected! How can I help you?")
            return True
        
        return False
    
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
        """Clean up temporary files."""
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
    
    # Load wake words from config
    wake_words = [
        "hey chat",
        "hey, chat",
        "hi chat",
        "hi, chat",
        "hello chat",
        "hello, chat",
        "hey chat bot",
        "hey chatbot",
        "hi chatbot",
        "hello chatbot",
        "ok chat",
        "okay chat",
        "yo chat",
        "chat.",
        "chads.",
        "hey chads",
        "hey, chads",
        "hi chads",
        "hi, chads",
        "hello chads",
        "hello, chads",
        "8 chat",
        "chats.",
        "chat",
        "chats",
        "stay chat",
        
        "stay, chat"
    ]
    
    assistant = VoiceAssistant(wake_words=wake_words)
    assistant.run()
    return 0

if __name__ == "__main__":
    exit(main()) 