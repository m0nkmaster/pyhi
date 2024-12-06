from fastapi import FastAPI
import uvicorn
from datetime import datetime
from src.config import APIConfig
from src.app import VoiceAssistant

app = FastAPI()

class AssistantState:
    instance = None
    
    @classmethod
    def set_assistant(cls, assistant):
        cls.instance = assistant
    
    @classmethod
    def get_assistant(cls):
        return cls.instance

@app.get("/wake")
async def wake_device():
    assistant = AssistantState.get_assistant()
    if assistant is None:
        return {"status": "Error: Voice Assistant not initialized", "success": False}
    
    if not assistant.is_awake:
        assistant.is_awake = True
        assistant.last_interaction = datetime.now()
        # Play activation sound if available
        if assistant.activation_sound:
            try:
                assistant.audio_player.play(assistant.activation_sound)
            except Exception as e:
                print(f"Failed to play activation sound: {e}")
        return {"status": "Device waking up", "success": True}
    return {"status": "Device is already awake", "success": False}

@app.get("/sleep")
async def sleep_device():
    assistant = AssistantState.get_assistant()
    if assistant is None:
        return {"status": "Error: Voice Assistant not initialized", "success": False}
    
    if assistant.is_awake:
        assistant.is_awake = False
        assistant.last_interaction = None
        return {"status": "Device going to sleep", "success": True}
    return {"status": "Device is already sleeping", "success": False}

def start_api():
    config = APIConfig()
    uvicorn.run(app, host=config.host, port=config.port)

if __name__ == "__main__":
    start_api()
