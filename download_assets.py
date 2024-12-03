import os
import requests

def download_bing_sound():
    """Download the bing.m4a file if it doesn't exist."""
    if os.path.exists("bing.m4a"):
        print("bing.m4a already exists")
        return
    
    print("Downloading bing.m4a...")
    url = "https://raw.githubusercontent.com/cursor-ai/chat-button/main/bing.m4a"
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open("bing.m4a", "wb") as f:
            f.write(response.content)
        print("Downloaded bing.m4a successfully!")
    except Exception as e:
        print(f"Error downloading bing.m4a: {e}")

if __name__ == "__main__":
    download_bing_sound() 