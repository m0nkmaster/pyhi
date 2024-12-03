import os
import wave
import pyaudio
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from config import (
    AUDIO_SAMPLE_RATE, CHANNELS, CHUNK_SIZE, RECORD_SECONDS,
    MODEL_NAME, MAX_TOKENS, REQUEST_TEMPERATURE, RESPONSE_TEMPERATURE,
    MICROPHONE_NAME, SPEAKER_NAME, THRESHOLD
)

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
        
    def is_speech_detected(self, data):
        """Check if audio input exceeds the speech threshold"""
        # Convert bytes to integers
        audio_data = np.frombuffer(data, dtype=np.int16)
        # Calculate RMS value using absolute values to avoid negative numbers
        rms = np.sqrt(np.mean(np.square(np.abs(audio_data).astype(np.float64))))
        return rms > THRESHOLD
    
    def record_audio(self):
        """Record audio when speech is detected"""
        print("Listening for speech...")
        
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
        is_recording = False
        
        try:
            while True:
                data = stream.read(self.chunk)
                
                if self.is_speech_detected(data):
                    if not is_recording:
                        print("Speech detected, recording...")
                        is_recording = True
                    frames.append(data)
                    silence_counter = 0
                elif is_recording:
                    frames.append(data)
                    silence_counter += 1
                    
                    # Stop recording after ~1 second of silence
                    if silence_counter > int(self.sample_rate / self.chunk):
                        break
        
        finally:
            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            audio.terminate()
        
        return b''.join(frames)
    
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
    
    def run(self):
        """Main loop to run the voice button"""
        print("Voice Button is ready! Press Ctrl+C to quit...")
        
        try:
            while True:
                # Record audio when speech is detected
                audio_data = self.record_audio()
                self.save_audio(audio_data)
                
                # Transcribe audio
                transcript = self.transcribe_audio("recording.wav")
                if transcript:
                    print(f"You said: {transcript}")
                    
                    # Get ChatGPT response
                    response = self.get_chatgpt_response(transcript)
                    print(f"ChatGPT: {response}")
                    
                    # Convert response to speech
                    self.text_to_speech(response)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            # Cleanup
            if os.path.exists("recording.wav"):
                os.remove("recording.wav")
            if os.path.exists("response.mp3"):
                os.remove("response.mp3")

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment variables")
        exit(1)
    
    voice_button = VoiceButton()
    voice_button.run()
