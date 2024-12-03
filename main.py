import os
import wave
import pyaudio
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from config import (
    AUDIO_SAMPLE_RATE, CHANNELS, CHUNK_SIZE, RECORD_SECONDS,
    MODEL_NAME, MAX_TOKENS, REQUEST_TEMPERATURE, RESPONSE_TEMPERATURE,
    MICROPHONE_NAME, SPEAKER_NAME, THRESHOLD, WAKE_WORDS, TIMEOUT_SECONDS,
    ACTIVATION_SOUND, WAKE_WORD_SILENCE_THRESHOLD, RESPONSE_SILENCE_THRESHOLD
)
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

class VoiceButton:
    def __init__(self):
        # Initialize audio parameters
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.channels = CHANNELS
        self.chunk = CHUNK_SIZE
        self.record_seconds = RECORD_SECONDS
        self.format = pyaudio.paInt16
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Initialize wake word and timeout settings
        self.wake_words = [word.lower() for word in WAKE_WORDS]
        self.is_awake = False
        self.last_interaction = None
        self.timeout_seconds = TIMEOUT_SECONDS
        
        # Generate activation sound on startup
        self.generate_activation_sound()
        
        # Initialize silence thresholds
        self.wake_word_silence_threshold = int(self.sample_rate * WAKE_WORD_SILENCE_THRESHOLD / self.chunk)
        self.response_silence_threshold = int(self.sample_rate * RESPONSE_SILENCE_THRESHOLD / self.chunk)

    def run(self):
        """Main loop to run the voice button"""
        print(f"Voice Button is ready! Say '{self.wake_words[0]}' to wake me up (Press Ctrl+C to quit)...")
        
        try:
            while True:
                # Check for timeout when awake
                if self.is_awake and self.check_timeout():
                    print("Going back to sleep. Say the wake word to start a new conversation.")
                    continue

                if not self.is_awake:
                    # Listen for wake word
                    if self.listen_for_wake_word():
                        self.is_awake = True
                        self.last_interaction = datetime.now()
                        continue
                    else:
                        continue  # Keep listening for wake word

                # If we're awake, process normal conversation
                audio_data = self.record_audio(self.response_silence_threshold)
                if audio_data is None:  # No speech detected
                    continue
                    
                self.save_audio(audio_data)
                
                # Transcribe audio
                transcript = self.transcribe_audio("recording.wav")
                if not transcript:
                    continue

                print(f"You said: {transcript}")
                
                # Get ChatGPT response
                response = self.get_chatgpt_response(transcript)
                if response:
                    print(f"ChatGPT: {response}")
                    self.text_to_speech(response)
                    self.last_interaction = datetime.now()
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            # Cleanup
            if os.path.exists("recording.wav"):
                os.remove("recording.wav")
            if os.path.exists("response.mp3"):
                os.remove("response.mp3")

    def listen_for_wake_word(self):
        """Listen for the wake word using Whisper API"""
        print("Listening for wake word...")
        
        # Record a short audio sample
        audio_data = self.record_audio(self.wake_word_silence_threshold)
        if audio_data is None:
            return False
        
        self.save_audio(audio_data)
        
        # Transcribe using Whisper
        transcript = self.transcribe_audio("recording.wav")
        if transcript:
            transcript = transcript.lower()
            print(f"Detected: {transcript}")
            for wake_word in WAKE_WORDS:
                if wake_word in transcript:
                    self.play_activation_sound()
                    print("Wake word detected! How can I help you?")
                    return True
        return False

    def record_audio(self, silence_threshold):
        """Record audio when speech is detected"""
        if not self.is_awake:
            print("Listening for wake word...")
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # Open stream
        stream = audio.open(format=self.format,
                           channels=self.channels,
                           rate=self.sample_rate,
                           input=True,
                           frames_per_buffer=self.chunk)
        
        frames = []
        silence_counter = 0
        speech_detection_buffer = []
        is_recording = False
        
        try:
            while True:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                except IOError as e:
                    continue
                
                # Keep a small buffer of recent audio analysis results
                is_speech = self.analyze_audio_frame(data)
                speech_detection_buffer.append(is_speech)
                if len(speech_detection_buffer) > 3:
                    speech_detection_buffer.pop(0)
                
                # Only trigger recording if we have consistent speech detection
                if sum(speech_detection_buffer) >= 2:  # At least 2 out of 3 frames are speech
                    if not is_recording:
                        print("Speech detected, recording...")
                        is_recording = True
                    frames.append(data)
                    silence_counter = 0
                elif is_recording:
                    frames.append(data)
                    silence_counter += 1
                    
                    # Stop recording after configured silence duration
                    if silence_counter > silence_threshold:
                        if len(frames) > silence_threshold:
                            break
                        else:
                            # Reset if the recording was too short
                            frames = []
                            is_recording = False
                            silence_counter = 0
                            return None
        
        finally:
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        return b''.join(frames) if frames else None

    def save_audio(self, audio_data, filename="recording.wav"):
        """Save recorded audio to WAV file"""
        audio = pyaudio.PyAudio()
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)
        audio.terminate()

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using OpenAI's Whisper API"""
        try:
            with open(audio_file, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language="en",
                    response_format="text",
                    temperature=REQUEST_TEMPERATURE
                )
            return transcript
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def check_timeout(self):
        """Check if the system should go to sleep due to inactivity"""
        if not self.last_interaction:
            return False
        
        time_elapsed = datetime.now() - self.last_interaction
        if time_elapsed.seconds >= self.timeout_seconds:
            self.is_awake = False
            print("\nGoing to sleep due to inactivity...")
            return True
        return False

    def get_chatgpt_response(self, user_input):
        """Get response from ChatGPT"""
        if not user_input:
            print("No valid input to process")
            return None
        
        try:
            self.conversation_history.append({
                "role": "system",
                "content": "You are a helpful assistant. Please respond in English."
            })
            self.conversation_history.append({"role": "user", "content": user_input})
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=self.conversation_history,
                max_tokens=MAX_TOKENS,
                temperature=RESPONSE_TEMPERATURE
            )
            
            assistant_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            return assistant_response
        except Exception as e:
            print(f"Error getting ChatGPT response: {e}")
            return None

    def text_to_speech(self, text):
        """Convert text to speech using OpenAI's TTS API"""
        if not text:
            print("No text to convert to speech")
            return
        
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text
            )
            
            # Save the audio response
            response.stream_to_file("response.mp3")
            
            # Play the audio
            os.system("afplay response.mp3")  # Using afplay for macOS
        except Exception as e:
            print(f"Error converting text to speech: {e}")

    def analyze_audio_frame(self, data):
        """Analyze audio frame for speech-like characteristics"""
        # Convert bytes to integers
        audio_data = np.frombuffer(data, dtype=np.int16)
        
        # Calculate RMS amplitude
        rms = np.sqrt(np.mean(np.square(np.abs(audio_data).astype(np.float64))))
        
        # Perform FFT to get frequency components
        fft = np.fft.fft(audio_data)
        frequencies = np.abs(fft)
        
        # Focus on frequency range for human speech (roughly 100-3000 Hz)
        freq_bins = len(frequencies)
        speech_range_start = int(100 * freq_bins / self.sample_rate)
        speech_range_end = int(3000 * freq_bins / self.sample_rate)
        speech_frequencies = frequencies[speech_range_start:speech_range_end]
        
        # Calculate metrics
        avg_speech_magnitude = np.mean(speech_frequencies)
        peak_frequency = np.argmax(speech_frequencies) + speech_range_start
        peak_hz = peak_frequency * self.sample_rate / freq_bins
        
        # Define speech characteristics
        is_loud_enough = rms > THRESHOLD
        has_speech_frequencies = (100 < peak_hz < 3000)
        has_sufficient_variation = np.std(speech_frequencies) > THRESHOLD/4
        
        return (is_loud_enough and has_speech_frequencies and has_sufficient_variation)

    def generate_activation_sound(self):
        """Generate a simple activation beep sound"""
        duration = 0.2  # seconds
        frequency = 1000  # Hz
        samples = (np.sin(2 * np.pi * np.arange(duration * self.sample_rate) * frequency / self.sample_rate)).astype(np.float32)
        
        # Normalize and convert to 16-bit PCM
        samples = (samples * 32767).astype(np.int16)
        
        # Save as WAV file
        with wave.open("activation.wav", 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 2 bytes for 16-bit audio
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())

    def play_activation_sound(self):
        """Play the activation sound"""
        try:
            # Using afplay for macOS which can handle m4a files
            os.system(f"afplay {ACTIVATION_SOUND}")
        except Exception as e:
            print(f"Error playing activation sound: {e}")

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment variables")
        exit(1)
    
    voice_button = VoiceButton()
    voice_button.run()
