"""Google Calendar function implementation."""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import zoneinfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'rob@robmacdonald.com'  # Specified calendar ID
TIMEZONE = 'Europe/London'  # UK Time

def get_calendar_service():
    """Initialize the Calendar API service."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            './private/pyhi-google.json',  # Updated path
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to create calendar service: {str(e)}")
        raise

def add_event(event_details: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new event to the calendar."""
    try:
        service = get_calendar_service()
        
        event = {
            'summary': event_details['summary'],
            'description': event_details.get('description', ''),
            'start': {
                'dateTime': event_details['start_time'],
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': event_details['end_time'],
                'timeZone': TIMEZONE,
            },
        }
        
        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return {
            "status": "success",
            "message": "Event created successfully",
            "event_id": event['id']
        }
    except HttpError as e:
        logger.error(f"Failed to add event: {str(e)}")
        return {"status": "error", "message": f"Failed to add event: {str(e)}"}

def delete_event(event_id: str) -> Dict[str, Any]:
    """Delete an event from the calendar."""
    try:
        service = get_calendar_service()
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return {
            "status": "success",
            "message": f"Event {event_id} deleted successfully"
        }
    except HttpError as e:
        logger.error(f"Failed to delete event: {str(e)}")
        return {"status": "error", "message": f"Failed to delete event: {str(e)}"}

def view_calendar(time_min: Optional[str] = None) -> Dict[str, Any]:
    """View upcoming calendar events."""
    try:
        service = get_calendar_service()
        
        # If no time provided, use current time in local timezone
        if not time_min:
            local_tz = zoneinfo.ZoneInfo(TIMEZONE)
            time_min = datetime.now(local_tz).isoformat()
            
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
            timeZone=TIMEZONE
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return {"status": "success", "message": "No upcoming events found"}
            
        formatted_events = []
        for event in events:
            formatted_events.append({
                'id': event['id'],
                'summary': event['summary'],
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date'))
            })
            
        return {
            "status": "success",
            "events": formatted_events
        }
    except HttpError as e:
        logger.error(f"Failed to view calendar: {str(e)}")
        return {"status": "error", "message": f"Failed to view calendar: {str(e)}"}

def implementation(action: str, event: Optional[Dict[str, Any]] = None) -> str:
    """Main implementation function for calendar management."""
    try:
        if action == "add_event":
            if not event:
                return json.dumps({"error": "Event details required for adding event"})
            result = add_event(event)
            
        elif action == "delete_event":
            if not event or 'event_id' not in event:
                return json.dumps({"error": "Event ID required for deletion"})
            result = delete_event(event['event_id'])
            
        elif action == "view_calendar":
            result = view_calendar()
            
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
            
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Calendar operation failed: {str(e)}")
        return json.dumps({"error": f"Calendar operation failed: {str(e)}"})