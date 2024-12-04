#!/bin/bash

# Update and upgrade the system
sudo apt-get update && sudo apt-get upgrade -y

# Install necessary system packages
sudo apt-get install -y python3-pip python3-venv portaudio19-dev python3-pyaudio mpg123 git

# Create a directory for the voice assistant
mkdir -p ~/voice_assistant
cd ~/voice_assistant

# Clone your repository (replace with your actual repository URL)
# git clone https://github.com/yourusername/yourrepository.git .
# cd yourrepository

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt

# Set up environment variables
echo "OPENAI_API_KEY=your_api_key_here" > .env

# Create a systemd service file
sudo bash -c 'cat << EOF > /etc/systemd/system/voice-assistant.service
[Unit]
Description=Voice Assistant Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/voice_assistant
Environment=PYTHONPATH=/home/pi/voice_assistant
EnvironmentFile=/home/pi/voice_assistant/.env
ExecStart=/home/pi/voice_assistant/venv/bin/python -m src.app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF'

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable voice-assistant.service

# Start the voice assistant service
sudo systemctl start voice-assistant.service

echo "Voice Assistant setup complete. The service is running and will start on boot."