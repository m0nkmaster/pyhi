# ChatGPT Voice Button

A Raspberry Pi-based device that initiates voice conversations with ChatGPT at the press of a button.

## Hardware Requirements

- Raspberry Pi (any recent model)
- Wi-Fi button (compatible with GPIO)
- USB Microphone
- Speaker/Audio output device
- Internet connection

## Software Requirements

- Python 3.7+
- Required Python packages (install via requirements.txt)
- OpenAI API key

## Setup Instructions

1. Clone this repository to your Raspberry Pi
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
4. Connect your microphone and speaker
5. Run the main program:
   ```bash
   python main.py
   ```

## Hardware Setup

- Connect the Wi-Fi button to GPIO pin 18 (can be configured in config.py)
- Ensure microphone is recognized by the system
- Connect speaker to the audio output

## Configuration

Edit `config.py` to modify:
- GPIO pin assignments
- Audio settings
- ChatGPT parameters
