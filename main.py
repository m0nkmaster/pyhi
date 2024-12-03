import os
import wave
import pyaudio
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

class VoiceButton:
    def __init__(self):
        # Initialize audio parameters
        self.sample_rate = 44100
        self.channels = 1
        self.chunk = 1024
        self.record_seconds = 5
        self.format = pyaudio.paFloat32
        
        # Initialize conversation history
        self.conversation_history = []
        
    def record_audio(self):
        """Record audio from microphone"""
        print("Recording... (5 seconds)")
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        # Open stream
        stream = audio.open(format=self.format,
                          channels=self.channels,
                          rate=self.sample_rate,
                          input=True,
                          frames_per_buffer=self.chunk)
        
        frames = []
        for _ in range(0, int(self.sample_rate / self.chunk * self.record_seconds)):
            data = stream.read(self.chunk)
            frames.append(data)
        
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
                    language="en"
                )
            return transcript.text
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
    
    def get_chatgpt_response(self, user_input):
        """Get response from ChatGPT"""
        try:
            self.conversation_history.append({
                "role": "system",
                "content": "You are a helpful assistant. Please respond in English."
            })
            self.conversation_history.append({"role": "user", "content": user_input})
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            return assistant_response
        except Exception as e:
            print(f"Error getting ChatGPT response: {e}")
            return None
    
    def text_to_speech(self, text):
        """Convert text to speech using OpenAI's TTS API"""
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
        print("Voice Button is ready! Press Enter to start a conversation (or 'q' to quit)...")
        
        try:
            while True:
                user_input = input()
                if user_input.lower() == 'q':
                    break
                    
                print("Starting conversation...")
                
                # Record audio
                audio_data = self.record_audio()
                self.save_audio(audio_data)
                
                # Transcribe audio
                transcript = self.transcribe_audio("recording.wav")
                print(f"You said: {transcript}")
                
                # Get ChatGPT response
                response = self.get_chatgpt_response(transcript)
                print(f"ChatGPT: {response}")
                
                # Convert response to speech
                self.text_to_speech(response)
                
                print("\nPress Enter for another conversation (or 'q' to quit)...")
                
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
