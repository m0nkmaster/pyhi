"""Alarms and timers function implementation."""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlarmManager:
    """Singleton class to manage alarms."""
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating new AlarmManager instance")
            cls._instance = super(AlarmManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            logger.info("Initializing AlarmManager")
            self.active_alarms: Dict[str, Dict[str, Any]] = {}
            self.audio_player = None
            self._initialized = True
            logger.info(f"AlarmManager initialized at {id(self)}")

    def set_audio_player(self, player):
        """Set the audio player instance."""
        self.audio_player = player
        logger.info(f"Audio player set for AlarmManager at {id(self)}")

    def play_alarm_sound(self):
        """Play a sound when alarm goes off."""
        try:
            logger.info("Attempting to play alarm sound...")
            if not self.audio_player:
                logger.error("No audio player available!")
                return
                
            # Get the absolute path to the assets directory
            current_dir = Path(__file__).resolve()
            src_dir = current_dir.parent.parent.parent
            sound_path = src_dir / 'assets' / 'beep.mp3'
            
            if not sound_path.exists():
                logger.error(f"Alarm sound not found at {sound_path}")
                return
                
            # Play sound with higher volume and more repetitions
            for _ in range(3):  # Play 3 times
                try:
                    logger.info("Playing alarm sound...")
                    self.audio_player.play(str(sound_path), volume=2.0, block=True)
                    time.sleep(0.5)  # Shorter delay between repeats
                except Exception as e:
                    logger.error(f"Error playing alarm sound: {e}", exc_info=True)
                    time.sleep(0.5)  # Still wait even if play fails
            
        except Exception as e:
            logger.error(f"Failed to play alarm sound: {e}", exc_info=True)

    def check_alarms(self):
        """Check and trigger alarms that are due."""
        try:
            now = datetime.now()
            if not self.active_alarms:
                logger.debug("No active alarms")
                return
                
            logger.info(f"Checking {len(self.active_alarms)} active alarms at {now}")
            to_remove = []
            
            for alarm_id, alarm in self.active_alarms.items():
                try:
                    scheduled_time = datetime.fromisoformat(alarm['scheduled_time'])
                    logger.info(f"Checking alarm {alarm_id}: scheduled for {scheduled_time}, current time {now}")
                    
                    if now >= scheduled_time:
                        logger.info(f"Alarm due: {alarm.get('label', 'Unnamed alarm')}")
                        self.play_alarm_sound()
                        to_remove.append(alarm_id)
                except Exception as e:
                    logger.error(f"Error checking individual alarm {alarm_id}: {e}", exc_info=True)
            
            # Remove triggered alarms
            for alarm_id in to_remove:
                try:
                    del self.active_alarms[alarm_id]
                    logger.info(f"Removed alarm {alarm_id}")
                except Exception as e:
                    logger.error(f"Error removing alarm {alarm_id}: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error checking alarms: {e}", exc_info=True)
            raise  # Re-raise to let the app handle it

    def set_timer(self, duration: str, label: Optional[str] = None) -> Dict[str, Any]:
        """Set a timer for a specific duration."""
        try:
            # Parse duration
            delay = self._parse_time(duration)
            
            # Calculate when timer will go off
            end_time = datetime.now() + delay
            
            # Create unique ID for this timer
            timer_id = str(uuid.uuid4())
            
            # Store timer info
            self.active_alarms[timer_id] = {
                'type': 'timer',
                'duration': duration,
                'label': label,
                'scheduled_time': end_time.isoformat()
            }
            
            logger.info(f"Setting timer for {duration} (ends at {end_time.strftime('%H:%M')})")
            logger.info(f"Timer ID: {timer_id}")
            logger.info(f"Active alarms after setting timer: {json.dumps(self.active_alarms, indent=2)}")
            logger.info(f"AlarmManager instance at {id(self)}")
            
            return {
                "status": "success",
                "message": f"Timer set for {duration} (ends at {end_time.strftime('%H:%M')})",
                "alarm_id": timer_id
            }
        except Exception as e:
            logger.error(f"Failed to set timer: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Failed to set timer: {str(e)}"}

    def _parse_time(self, time_str: str) -> timedelta:
        """Parse time string into timedelta."""
        try:
            # Check if it's just minutes
            if time_str.isdigit():
                return timedelta(minutes=int(time_str))
            
            # Parse HH:MM format
            hours, minutes = map(int, time_str.split(':'))
            return timedelta(hours=hours, minutes=minutes)
        except Exception as e:
            raise ValueError(f"Invalid time format. Use HH:MM or minutes: {e}")

    def set_alarm(self, time_str: str, label: Optional[str] = None) -> Dict[str, Any]:
        """Set an alarm for a specific time."""
        try:
            # Parse the time (HH:MM)
            alarm_time = datetime.strptime(time_str, "%H:%M").time()
            now = datetime.now()
            
            # Calculate when the alarm should go off
            alarm_datetime = datetime.combine(now.date(), alarm_time)
            if alarm_datetime <= now:
                # If the time has passed today, set for tomorrow
                alarm_datetime += timedelta(days=1)
            
            # Create unique ID for this alarm
            alarm_id = str(uuid.uuid4())
            
            # Store alarm info
            self.active_alarms[alarm_id] = {
                'type': 'alarm',
                'time': time_str,
                'label': label,
                'scheduled_time': alarm_datetime.isoformat()
            }
            
            logger.info(f"Setting alarm for {time_str} ({alarm_datetime.strftime('%Y-%m-%d %H:%M')})")
            logger.info(f"Active alarms after setting alarm: {json.dumps(self.active_alarms, indent=2)}")
            
            return {
                "status": "success",
                "message": f"Alarm set for {time_str} ({alarm_datetime.strftime('%Y-%m-%d %H:%M')})",
                "alarm_id": alarm_id
            }
        except Exception as e:
            logger.error(f"Failed to set alarm: {str(e)}")
            return {"status": "error", "message": f"Failed to set alarm: {str(e)}"}

    def list_alarms(self) -> Dict[str, Any]:
        """List all active alarms and timers."""
        try:
            if not self.active_alarms:
                return {"status": "success", "message": "No active alarms or timers"}
            
            formatted_alarms = []
            for alarm_id, alarm in self.active_alarms.items():
                formatted_alarms.append({
                    'id': alarm_id,
                    'type': alarm['type'],
                    'scheduled_time': alarm['scheduled_time'],
                    'label': alarm.get('label', 'Unnamed alarm')
                })
            
            return {
                "status": "success",
                "alarms": formatted_alarms
            }
        except Exception as e:
            logger.error(f"Failed to list alarms: {str(e)}")
            return {"status": "error", "message": f"Failed to list alarms: {str(e)}"}

    def delete_alarm(self, alarm_id: str) -> Dict[str, Any]:
        """Delete a specific alarm or timer."""
        try:
            if alarm_id not in self.active_alarms:
                return {"status": "error", "message": "Alarm not found"}
            
            del self.active_alarms[alarm_id]
            return {
                "status": "success",
                "message": f"Alarm {alarm_id} deleted successfully"
            }
        except Exception as e:
            logger.error(f"Failed to delete alarm: {str(e)}")
            return {"status": "error", "message": f"Failed to delete alarm: {str(e)}"}

# Create the singleton instance
alarm_manager = AlarmManager()

def set_audio_player(player):
    """Set the audio player instance."""
    alarm_manager.set_audio_player(player)

def check_alarms():
    """Check and trigger alarms that are due."""
    alarm_manager.check_alarms()

def implementation(action: str, time: Optional[str] = None, label: Optional[str] = None, alarm_id: Optional[str] = None) -> str:
    """Main implementation function for alarm management."""
    try:
        logger.info(f"Alarm action requested: {action} with time={time}, label={label}, alarm_id={alarm_id}")
        logger.info(f"Current active alarms before action: {json.dumps(alarm_manager.active_alarms, indent=2)}")
        
        if action == "set_alarm":
            if not time:
                return json.dumps({"error": "Time required for setting alarm"})
            result = alarm_manager.set_alarm(time, label)
            
        elif action == "set_timer":
            if not time:
                return json.dumps({"error": "Duration required for setting timer"})
            result = alarm_manager.set_timer(time, label)
            
        elif action == "list_alarms":
            result = alarm_manager.list_alarms()
            
        elif action == "delete_alarm":
            if not alarm_id:
                return json.dumps({"error": "Alarm ID required for deletion"})
            result = alarm_manager.delete_alarm(alarm_id)
            
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
        
        logger.info(f"Action {action} completed with result: {json.dumps(result, indent=2)}")
        logger.info(f"Active alarms after action: {json.dumps(alarm_manager.active_alarms, indent=2)}")
        logger.info(f"AlarmManager instance at {id(alarm_manager)}")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Alarm operation failed: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Alarm operation failed: {str(e)}"}) 