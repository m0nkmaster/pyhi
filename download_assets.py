import os
import requests

def download_bing_sound():
    """Download the bing.mp3 file if it doesn't exist."""
    if os.path.exists("bing.mp3"):
        print("bing.mp3 already exists")
        return
    
    print("Downloading bing.mp3...")
    url = "https://raw.githubusercontent.com/cursor-ai/chat-button/main/bing.mp3"
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open("bing.mp3", "wb") as f:
            f.write(response.content)
        print("Downloaded bing.mp3 successfully!")
    except Exception as e:
        print(f"Error downloading bing.mp3: {e}")

if __name__ == "__main__":
    download_bing_sound() 