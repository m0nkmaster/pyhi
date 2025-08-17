#!/usr/bin/env python3
"""
Alarms MCP Server for PyHi Voice Assistant.
Provides timer and alarm functionality through MCP.
"""

import json
import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Literal, Dict, Any, List
from pathlib import Path

from pydantic import BaseModel, Field
from mcp.server import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class AlarmData(BaseModel):
    """Alarm data response model."""
    alarm_id: str = Field(description="Unique alarm identifier")
    type: Literal["alarm", "timer"] = Field(description="Type of alarm")
    scheduled_time: str = Field(description="ISO timestamp when alarm will trigger")
    label: Optional[str] = Field(description="Optional alarm label")
    status: str = Field(description="Alarm status")

class AlarmError(BaseModel):
    """Error response model."""
    error: str = Field(description="Error message")

# Initialize MCP server
mcp = FastMCP("alarms-server")

# Simple in-memory alarm storage (in production, you'd use persistent storage)
active_alarms: Dict[str, Dict[str, Any]] = {}

def parse_time_duration(time_str: str) -> timedelta:
    """Parse time string into timedelta for timers."""
    try:
        # Check if it's just minutes
        if time_str.isdigit():
            return timedelta(minutes=int(time_str))
        
        # Parse HH:MM format as duration
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                hours, minutes = map(int, parts)
                return timedelta(hours=hours, minutes=minutes)
        
        # Parse simple minute format
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            return timedelta(minutes=minutes)
            
        # Parse simple hour format
        if time_str.endswith('h'):
            hours = int(time_str[:-1])
            return timedelta(hours=hours)
        
        raise ValueError(f"Unsupported time format: {time_str}")
        
    except Exception as e:
        raise ValueError(f"Invalid time format. Use minutes (e.g., '15'), HH:MM, or '15m'/'2h': {e}")

def parse_alarm_time(time_str: str) -> datetime:
    """Parse time string into datetime for alarms."""
    try:
        # Parse the time (HH:MM)
        alarm_time = datetime.strptime(time_str, "%H:%M").time()
        now = datetime.now()
        
        # Calculate when the alarm should go off
        alarm_datetime = datetime.combine(now.date(), alarm_time)
        if alarm_datetime <= now:
            # If the time has passed today, set for tomorrow
            alarm_datetime += timedelta(days=1)
            
        return alarm_datetime
        
    except Exception as e:
        raise ValueError(f"Invalid time format. Use HH:MM (e.g., '14:30'): {e}")

# MCP Tools
@mcp.tool()
async def set_timer(
    duration: str,
    label: Optional[str] = None
) -> str:
    """
    Set a timer for a specific duration.
    
    Args:
        duration: Timer duration (e.g., '15', '15m', '1h', '1:30')
        label: Optional label for the timer
    
    Returns:
        JSON string with timer information or error message
    """
    try:
        # Parse duration
        delay = parse_time_duration(duration)
        
        # Calculate when timer will go off
        end_time = datetime.now() + delay
        
        # Create unique ID for this timer
        timer_id = str(uuid.uuid4())
        
        # Store timer info
        active_alarms[timer_id] = {
            'type': 'timer',
            'duration': duration,
            'label': label,
            'scheduled_time': end_time.isoformat()
        }
        
        logger.info(f"Setting timer for {duration} (ends at {end_time.strftime('%H:%M')})")
        
        result = {
            "status": "success",
            "message": f"Timer set for {duration} (ends at {end_time.strftime('%H:%M')})",
            "alarm_id": timer_id,
            "scheduled_time": end_time.isoformat()
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Failed to set timer: {str(e)}")
        return json.dumps({"error": f"Failed to set timer: {str(e)}"})

@mcp.tool()
async def set_alarm(
    time: str,
    label: Optional[str] = None
) -> str:
    """
    Set an alarm for a specific time.
    
    Args:
        time: Alarm time in HH:MM format (e.g., '14:30')
        label: Optional label for the alarm
    
    Returns:
        JSON string with alarm information or error message
    """
    try:
        # Parse the alarm time
        alarm_datetime = parse_alarm_time(time)
        
        # Create unique ID for this alarm
        alarm_id = str(uuid.uuid4())
        
        # Store alarm info
        active_alarms[alarm_id] = {
            'type': 'alarm',
            'time': time,
            'label': label,
            'scheduled_time': alarm_datetime.isoformat()
        }
        
        logger.info(f"Setting alarm for {time} ({alarm_datetime.strftime('%Y-%m-%d %H:%M')})")
        
        result = {
            "status": "success",
            "message": f"Alarm set for {time} ({alarm_datetime.strftime('%Y-%m-%d %H:%M')})",
            "alarm_id": alarm_id,
            "scheduled_time": alarm_datetime.isoformat()
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Failed to set alarm: {str(e)}")
        return json.dumps({"error": f"Failed to set alarm: {str(e)}"})

@mcp.tool()
async def list_alarms() -> str:
    """
    List all active alarms and timers.
    
    Returns:
        JSON string with list of active alarms or error message
    """
    try:
        if not active_alarms:
            return json.dumps({"status": "success", "message": "No active alarms or timers", "alarms": []})
        
        formatted_alarms = []
        for alarm_id, alarm in active_alarms.items():
            formatted_alarms.append({
                'id': alarm_id,
                'type': alarm['type'],
                'scheduled_time': alarm['scheduled_time'],
                'label': alarm.get('label', 'Unnamed alarm')
            })
        
        result = {
            "status": "success",
            "alarms": formatted_alarms,
            "count": len(formatted_alarms)
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Failed to list alarms: {str(e)}")
        return json.dumps({"error": f"Failed to list alarms: {str(e)}"})

@mcp.tool()
async def delete_alarm(alarm_id: str) -> str:
    """
    Delete a specific alarm or timer.
    
    Args:
        alarm_id: ID of the alarm to delete
    
    Returns:
        JSON string with deletion status or error message
    """
    try:
        if alarm_id not in active_alarms:
            return json.dumps({"error": "Alarm not found"})
        
        alarm_info = active_alarms[alarm_id]
        del active_alarms[alarm_id]
        
        result = {
            "status": "success",
            "message": f"Deleted {alarm_info['type']} '{alarm_info.get('label', 'Unnamed')}'"
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Failed to delete alarm: {str(e)}")
        return json.dumps({"error": f"Failed to delete alarm: {str(e)}"})

@mcp.tool()
async def check_alarms() -> str:
    """
    Check for any alarms that should trigger now.
    
    Returns:
        JSON string with triggered alarms or status message
    """
    try:
        now = datetime.now()
        triggered_alarms = []
        to_remove = []
        
        for alarm_id, alarm in active_alarms.items():
            try:
                scheduled_time = datetime.fromisoformat(alarm['scheduled_time'])
                
                if now >= scheduled_time:
                    triggered_alarms.append({
                        'id': alarm_id,
                        'type': alarm['type'],
                        'label': alarm.get('label', 'Unnamed alarm'),
                        'scheduled_time': alarm['scheduled_time']
                    })
                    to_remove.append(alarm_id)
            except Exception as e:
                logger.error(f"Error checking alarm {alarm_id}: {e}")
        
        # Remove triggered alarms
        for alarm_id in to_remove:
            del active_alarms[alarm_id]
        
        if triggered_alarms:
            result = {
                "status": "triggered",
                "message": f"{len(triggered_alarms)} alarm(s) triggered",
                "triggered_alarms": triggered_alarms
            }
        else:
            result = {
                "status": "none",
                "message": "No alarms triggered",
                "triggered_alarms": []
            }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error checking alarms: {str(e)}")
        return json.dumps({"error": f"Error checking alarms: {str(e)}"})

# MCP Resources
@mcp.resource("alarms://active")
async def active_alarms_resource() -> str:
    """
    Resource endpoint for active alarms data.
    """
    return await list_alarms()

@mcp.resource("alarms://count")
async def alarms_count_resource() -> str:
    """
    Resource endpoint for alarm count.
    """
    return json.dumps({"count": len(active_alarms)})

# MCP Prompts
@mcp.prompt("alarm-management")
async def alarm_management_prompt() -> str:
    """
    Prompt template for alarm management assistance.
    """
    return """Help the user manage their alarms and timers. You can:
1. Set timers with durations like '15m', '1h', or '1:30'
2. Set alarms for specific times like '14:30' or '7:00'
3. List all active alarms and timers
4. Delete specific alarms by their ID
5. Check for any alarms that should trigger now

Use the appropriate alarm tools to help with these tasks."""

@mcp.prompt("timer-help")
async def timer_help_prompt() -> str:
    """
    Prompt template for timer usage help.
    """
    return """To set a timer, you can use formats like:
- '15' or '15m' for 15 minutes
- '1h' for 1 hour  
- '1:30' for 1 hour and 30 minutes
- Add an optional label like 'cooking timer' or 'meeting reminder'

Use the set_timer tool to create timers."""

# Server startup
def main():
    """Run the MCP alarms server."""
    logger.info("Starting Alarms MCP Server...")
    
    # Run the server using stdio transport
    mcp.run("stdio")

if __name__ == "__main__":
    main()