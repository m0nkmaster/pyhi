"""Date and time utility functions for use with OpenAI function calling."""

from datetime import datetime, timedelta
from typing import Dict, Union, List, Optional
from zoneinfo import ZoneInfo

class DateTimeUtils:
    """Utility class for date and time operations."""
    
    def __init__(self, default_timezone: str = "UTC"):
        """Initialize with default timezone."""
        self.default_timezone = default_timezone
    
    def get_current_time(self, timezone: Optional[str] = None) -> Dict[str, str]:
        """Get the current time in the specified timezone."""
        try:
            tz = timezone or self.default_timezone
            current_time = datetime.now(ZoneInfo(tz))
            return {
                "time": current_time.strftime("%H:%M:%S"),
                "timezone": tz,
                "timestamp": current_time.isoformat()
            }
        except Exception as e:
            return {"error": f"Error getting current time: {str(e)}"}

    def get_current_date(self, timezone: Optional[str] = None) -> Dict[str, str]:
        """Get the current date in the specified timezone."""
        try:
            tz = timezone or self.default_timezone
            current_date = datetime.now(ZoneInfo(tz))
            return {
                "date": current_date.strftime("%Y-%m-%d"),
                "day_of_week": current_date.strftime("%A"),
                "timezone": tz,
                "timestamp": current_date.isoformat()
            }
        except Exception as e:
            return {"error": f"Error getting current date: {str(e)}"}

    def calculate_days_between(self, start_date: str, end_date: str) -> Dict[str, Union[int, str]]:
        """Calculate the number of days between two dates."""
        try:
            date1 = datetime.strptime(start_date, "%Y-%m-%d")
            date2 = datetime.strptime(end_date, "%Y-%m-%d")
            days_diff = abs((date2 - date1).days)
            return {
                "days_difference": days_diff,
                "start_date": start_date,
                "end_date": end_date
            }
        except Exception as e:
            return {"error": f"Error calculating days between dates: {str(e)}"}

    def days_until_date(self, target_date: str) -> Dict[str, Union[int, str]]:
        """Calculate the number of days until a specific date."""
        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            days_remaining = (target - today).days
            return {
                "days_remaining": days_remaining,
                "target_date": target_date,
                "current_date": today.strftime("%Y-%m-%d")
            }
        except Exception as e:
            return {"error": f"Error calculating days until date: {str(e)}"}

    def format_date(self, date: str, format: str = "default") -> Dict[str, str]:
        """Format a date string into various formats."""
        format_templates = {
            "default": "%Y-%m-%d",
            "full": "%A, %B %d, %Y",
            "short": "%b %d, %Y",
            "iso": "%Y-%m-%dT%H:%M:%S",
            "custom": format
        }
        
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            format_str = format_templates.get(format, format_templates["default"])
            return {
                "formatted_date": date_obj.strftime(format_str),
                "original_date": date,
                "format_used": format
            }
        except Exception as e:
            return {"error": f"Error formatting date: {str(e)}"}

    @staticmethod
    def get_openai_function_definitions() -> List[Dict]:
        """Get the OpenAI function definitions for datetime utilities."""
        return [{
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get the current time in a specified timezone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone to get the time in (e.g., 'UTC', 'America/New_York', 'Europe/London'). Defaults to UTC if not specified."
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_date",
                "description": "Get the current date and related information in a specified timezone",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone to get the date in (e.g., 'UTC', 'America/New_York', 'Europe/London'). Defaults to UTC if not specified."
                        }
                    },
                    "required": [],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_days_between",
                "description": "Calculate the number of days between two dates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "The start date in YYYY-MM-DD format"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "The end date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["start_date", "end_date"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "days_until_date",
                "description": "Calculate the number of days until a specific date from today",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_date": {
                            "type": "string",
                            "description": "The target date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["target_date"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "format_date",
                "description": "Format a date into various formats",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date to format in YYYY-MM-DD format"
                        },
                        "format": {
                            "type": "string",
                            "description": "The format to use: 'default' (YYYY-MM-DD), 'full' (Monday, January 1, 2024), 'short' (Jan 1, 2024), 'iso' (2024-01-01T00:00:00), or a custom format string",
                            "enum": ["default", "full", "short", "iso", "custom"]
                        }
                    },
                    "required": ["date"],
                    "additionalProperties": False
                }
            }
        }] 