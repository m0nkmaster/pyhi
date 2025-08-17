#!/usr/bin/env python3
"""
Google Calendar MCP Server
Provides calendar management tools for PyHi voice assistant.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

from mcp.server import FastMCP
from pydantic import BaseModel, Field

# Google Calendar API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import zoneinfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'rob@robmacdonald.com'
TIMEZONE = 'Europe/London'

# Initialize MCP server
mcp = FastMCP("google-calendar")


class CalendarEvent(BaseModel):
    """Calendar event model."""
    summary: str = Field(..., description="Title of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    start_time: str = Field(..., description="Start time in ISO format (YYYY-MM-DDTHH:MM:SS)")
    end_time: str = Field(..., description="End time in ISO format (YYYY-MM-DDTHH:MM:SS)")
    event_id: Optional[str] = Field(None, description="Event ID (for updates/deletions)")


class CalendarResponse(BaseModel):
    """Standard calendar response."""
    status: str = Field(..., description="Success or error status")
    message: str = Field(..., description="Response message")
    event_id: Optional[str] = Field(None, description="Event ID if applicable")
    events: Optional[list] = Field(None, description="List of events if applicable")


def get_calendar_service():
    """Initialize the Google Calendar API service."""
    try:
        # Look for credentials file
        creds_path = './private/pyhi-google.json'
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Google Calendar credentials not found at {creds_path}")
        
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=creds)
        return service
        
    except Exception as e:
        logger.error(f"Failed to create calendar service: {e}")
        raise


@mcp.tool()
async def add_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = ""
) -> CalendarResponse:
    """
    Add a new event to Google Calendar.
    
    Args:
        summary: Title of the event
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
        description: Optional description of the event
    
    Returns:
        CalendarResponse with status and event details
    """
    try:
        service = get_calendar_service()
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': TIMEZONE,
            },
        }
        
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        
        return CalendarResponse(
            status="success",
            message=f"Event '{summary}' created successfully",
            event_id=created_event['id']
        )
        
    except HttpError as e:
        logger.error(f"Failed to add calendar event: {e}")
        return CalendarResponse(
            status="error",
            message=f"Failed to add event: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error adding calendar event: {e}")
        return CalendarResponse(
            status="error",
            message=f"Unexpected error: {str(e)}"
        )


@mcp.tool()
async def delete_calendar_event(event_id: str) -> CalendarResponse:
    """
    Delete an event from Google Calendar.
    
    Args:
        event_id: The ID of the event to delete
    
    Returns:
        CalendarResponse with deletion status
    """
    try:
        service = get_calendar_service()
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        
        return CalendarResponse(
            status="success",
            message=f"Event {event_id} deleted successfully"
        )
        
    except HttpError as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return CalendarResponse(
            status="error",
            message=f"Failed to delete event: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting calendar event: {e}")
        return CalendarResponse(
            status="error",
            message=f"Unexpected error: {str(e)}"
        )


@mcp.tool()
async def view_calendar_events(max_results: int = 10) -> CalendarResponse:
    """
    View upcoming calendar events.
    
    Args:
        max_results: Maximum number of events to return (default: 10)
    
    Returns:
        CalendarResponse with list of upcoming events
    """
    try:
        service = get_calendar_service()
        
        # Get current time in local timezone
        local_tz = zoneinfo.ZoneInfo(TIMEZONE)
        time_min = datetime.now(local_tz).isoformat()
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
            timeZone=TIMEZONE
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return CalendarResponse(
                status="success",
                message="No upcoming events found",
                events=[]
            )
        
        formatted_events = []
        for event in events:
            formatted_events.append({
                'id': event['id'],
                'summary': event['summary'],
                'description': event.get('description', ''),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date'))
            })
        
        return CalendarResponse(
            status="success",
            message=f"Found {len(formatted_events)} upcoming events",
            events=formatted_events
        )
        
    except HttpError as e:
        logger.error(f"Failed to view calendar events: {e}")
        return CalendarResponse(
            status="error",
            message=f"Failed to view calendar: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error viewing calendar events: {e}")
        return CalendarResponse(
            status="error",
            message=f"Unexpected error: {str(e)}"
        )


@mcp.resource("calendar://events")
async def get_calendar_events() -> str:
    """Get upcoming calendar events as a resource."""
    try:
        response = await view_calendar_events()
        return json.dumps(response.dict(), indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to get calendar events: {e}"})


@mcp.prompt("calendar-summary")
async def calendar_summary_prompt() -> str:
    """Get a summary of today's calendar events."""
    return """
    Please provide a summary of today's calendar events in a natural, conversational way.
    Include the time, title, and any important details of each event.
    If there are no events, mention that the calendar is clear for today.
    """


if __name__ == "__main__":
    # Run the MCP server
    mcp.run("stdio")