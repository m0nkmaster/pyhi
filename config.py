# GPIO Configuration
BUTTON_PIN = 18  # GPIO pin for the button

# Audio Configuration
AUDIO_SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
RECORD_SECONDS = 5  # Default recording time
THRESHOLD = 500  # Audio threshold for detecting speech

# ChatGPT Configuration
MODEL_NAME = "gpt-3.5-turbo"
MAX_TOKENS = 150
REQUEST_TEMPERATURE = 0.2
RESPONSE_TEMPERATURE = 0.7

# Audio Device Names (configure these based on your hardware)
MICROPHONE_NAME = "default"
SPEAKER_NAME = "default"

# Wake Word Configuration
WAKE_WORDS = ["hey, chat", "hey chat", "hi chat", "hello chat"]
TIMEOUT_SECONDS = 30
