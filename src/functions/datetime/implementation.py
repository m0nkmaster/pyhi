"""Implementation of datetime utility functions."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Union, Any
import re
import calendar

# Try to import dateutil with proper error handling
try:
    from dateutil import parser
    from dateutil.relativedelta import relativedelta
except ImportError:
    raise ImportError(
        "python-dateutil is required for date parsing functionality. "
        "Please install it with: pip install python-dateutil"
    )

# Default timezone
DEFAULT_TIMEZONE = "UTC"

# Common time expressions with more natural variations
COMMON_TIMES = {
    "noon": "12:00 pm",
    "midnight": "12:00 am",
    "midday": "12:00 pm",
    "lunchtime": "12:00 pm",
    "morning": "9:00 am",
    "afternoon": "2:00 pm",
    "evening": "6:00 pm",
    "night": "8:00 pm",
    "dawn": "6:00 am",
    "dusk": "6:00 pm",
    "sunrise": "6:30 am",
    "sunset": "6:30 pm",
    "breakfast": "8:00 am",
    "dinner": "7:00 pm",
}

# Common date expressions
COMMON_DATES = {
    "christmas": "December 25",
    "new year": "January 1",
    "new year's": "January 1",
    "new years": "January 1",
    "halloween": "October 31",
    "valentine": "February 14",
    "valentine's": "February 14",
    "valentines": "February 14",
}

# Enhanced time expressions with more natural context
DAYTIME_CONTEXTS = {
    "early_morning": (5, 8, ["early in the morning", "at dawn", "as the sun rises"]),
    "morning": (8, 12, ["in the morning", "before noon", "during the morning"]),
    "afternoon": (12, 17, ["in the afternoon", "after lunch", "during the day"]),
    "evening": (17, 21, ["in the evening", "around sunset", "as night approaches"]),
    "night": (21, 24, ["at night", "late in the evening", "tonight"]),
    "late_night": (0, 5, ["late at night", "in the early hours", "before dawn"])
}

SEASONAL_CONTEXTS = {
    "spring": ((3, 1), (5, 31), "during spring"),
    "summer": ((6, 1), (8, 31), "during summer"),
    "fall": ((9, 1), (11, 30), "during fall"),
    "winter": ((12, 1), (2, 28), "during winter")
}

# Date format templates
FORMAT_TEMPLATES = {
    "default": "%Y-%m-%d",
    "full": "%A, %B %d, %Y",
    "short": "%b %d, %Y",
    "iso": "%Y-%m-%dT%H:%M:%S",
    "custom": None  # Will be replaced by the format parameter if provided
}

def parse_time(time_str: str) -> Union[datetime, None]:
    """Parse time string in various formats."""
    time_str = time_str.lower().strip()
    
    # Check common time expressions
    if time_str in COMMON_TIMES:
        time_str = COMMON_TIMES[time_str]
    
    # Try different time formats
    formats = [
        "%I:%M %p",  # 2:30 pm
        "%H:%M",     # 14:30
        "%I%p",      # 2pm
        "%I %p",     # 2 pm
        "%H",        # 14
        "%I"         # 2
    ]
    
    for fmt in formats:
        try:
            parsed_time = datetime.strptime(time_str, fmt)
            return datetime.now().replace(
                hour=parsed_time.hour,
                minute=parsed_time.minute,
                second=0,
                microsecond=0
            )
        except ValueError:
            continue
    
    # Try dateutil parser as a fallback
    try:
        return parser.parse(time_str)
    except:
        return None

def parse_date(date_str: str) -> Union[datetime, None]:
    """Parse date string in various formats."""
    date_str = date_str.lower().strip()
    
    # Check common date expressions
    for key, value in COMMON_DATES.items():
        if key in date_str:
            # If year is not specified, use current or next occurrence
            current_year = datetime.now().year
            date_with_year = f"{value}, {current_year}"
            parsed_date = parser.parse(date_with_year)
            
            # If the date has passed this year, use next year
            if parsed_date.date() < datetime.now().date():
                date_with_year = f"{value}, {current_year + 1}"
                parsed_date = parser.parse(date_with_year)
            
            return parsed_date
    
    try:
        return parser.parse(date_str, fuzzy=True)
    except:
        return None

def get_daytime_context(hour: int, variation: int = None) -> str:
    """Get a natural context for the time of day with variations."""
    for _, (start, end, phrases) in DAYTIME_CONTEXTS.items():
        if start <= hour < end:
            if variation is None:
                variation = datetime.now().minute % len(phrases)
            return phrases[variation % len(phrases)]
    return "at night"

def get_seasonal_context(date: datetime) -> str:
    """Get the seasonal context for a given date."""
    month = date.month
    day = date.day
    
    for _, ((start_month, start_day), (end_month, end_day), description) in SEASONAL_CONTEXTS.items():
        if (start_month <= month <= end_month and 
            (month != start_month or day >= start_day) and 
            (month != end_month or day <= end_day)):
            return description
    return ""  # No specific season context

def get_current_time(timezone: str = None, format: str = "natural") -> Dict[str, str]:
    """Get the current time with enhanced natural language and contextual awareness."""
    try:
        tz = timezone or DEFAULT_TIMEZONE
        current_time = datetime.now(ZoneInfo(tz))
        
        if format == "natural":
            hour = current_time.hour
            minute = current_time.minute
            daytime_context = get_daytime_context(hour)
            
            # More natural time expressions
            if minute == 0:
                if hour == 12:
                    time_str = "It's noon"
                elif hour == 0:
                    time_str = "It's midnight"
                else:
                    hour_12 = hour if hour <= 12 else hour-12
                    if hour in [6, 7]:
                        time_str = f"It's early morning, around {hour_12}"
                    elif hour in [8, 9]:
                        time_str = f"It's morning, around {hour_12}"
                    else:
                        time_str = f"It's {hour_12} o'clock {daytime_context}"
            elif minute <= 5:
                hour_12 = hour if hour <= 12 else hour-12
                time_str = f"It's just past {hour_12} {daytime_context}"
            elif minute >= 55:
                next_hour = (hour + 1) % 24
                next_hour_12 = next_hour if next_hour <= 12 else next_hour-12
                time_str = f"It's almost {next_hour_12} {get_daytime_context(next_hour)}"
            elif minute == 30:
                hour_12 = hour if hour <= 12 else hour-12
                time_str = f"It's half past {hour_12} {daytime_context}"
            elif minute == 15:
                hour_12 = hour if hour <= 12 else hour-12
                time_str = f"It's quarter past {hour_12} {daytime_context}"
            elif minute == 45:
                next_hour = (hour + 1) % 24
                next_hour_12 = next_hour if next_hour <= 12 else next_hour-12
                time_str = f"It's quarter to {next_hour_12} {get_daytime_context(next_hour)}"
            else:
                hour_12 = hour if hour <= 12 else hour-12
                if minute < 30:
                    time_str = f"It's about {minute} minutes past {hour_12} {daytime_context}"
                else:
                    next_hour = (hour + 1) % 24
                    next_hour_12 = next_hour if next_hour <= 12 else next_hour-12
                    mins_to = 60 - minute
                    time_str = f"It's about {mins_to} minutes to {next_hour_12} {get_daytime_context(next_hour)}"
                
            if timezone and timezone != DEFAULT_TIMEZONE:
                time_str += f" ({timezone})"
                
            return {"description": time_str}
        else:
            return get_current_time_structured(current_time, tz)
            
    except Exception as e:
        return {"error": f"I couldn't figure out the time: {str(e)}"}

def get_current_time_structured(current_time: datetime, tz: str) -> Dict[str, str]:
    """Helper function for structured time output."""
    return {
        "time": current_time.strftime("%H:%M:%S"),
        "hour": int(current_time.strftime("%H")),
        "minute": int(current_time.strftime("%M")),
        "timezone": tz,
        "timestamp": current_time.isoformat()
    }

def get_current_date(timezone: str = None, format: str = "natural") -> Dict[str, str]:
    """Get the current date with enhanced contextual awareness."""
    try:
        tz = timezone or DEFAULT_TIMEZONE
        current_date = datetime.now(ZoneInfo(tz))
        
        if format == "natural":
            # Check for special dates first
            date_str = current_date.strftime("%B %d")
            for name, date in COMMON_DATES.items():
                if date.lower() == date_str.lower():
                    seasonal_context = get_seasonal_context(current_date)
                    response = f"It's {name.title()}"
                    if seasonal_context:
                        response += f" {seasonal_context}"
                    return {"description": response}
            
            # Regular date with context
            day_of_week = current_date.strftime("%A")
            month = current_date.strftime("%B")
            day = current_date.day
            seasonal_context = get_seasonal_context(current_date)
            
            response = f"It's {day_of_week}"
            if seasonal_context:
                response += f", {seasonal_context}"
            
            if timezone and timezone != DEFAULT_TIMEZONE:
                response += f" ({timezone})"
                
            return {"description": response}
        else:
            return {
                "date": current_date.strftime("%Y-%m-%d"),
                "day_of_week": current_date.strftime("%A"),
                "month": current_date.strftime("%B"),
                "day": int(current_date.strftime("%d")),
                "year": int(current_date.strftime("%Y")),
                "timezone": tz,
                "timestamp": current_date.isoformat()
            }
    except Exception as e:
        return {"error": f"Error getting current date: {str(e)}"}

def time_until(target_time: str, timezone: str = None) -> Dict[str, Any]:
    """Calculate time until a specific time with contextual awareness."""
    try:
        tz = timezone or DEFAULT_TIMEZONE
        now = datetime.now(ZoneInfo(tz))
        
        parsed_time = parse_time(target_time)
        if not parsed_time:
            return {"error": "I don't understand that time format"}
        
        # Set the target time to today
        target = now.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=0,
            microsecond=0
        )
        
        # If the target time is earlier today, assume tomorrow
        if target < now:
            target += timedelta(days=1)
            tomorrow = True
        else:
            tomorrow = False
        
        time_diff = target - now
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60
        
        # Natural language description
        if hours == 0 and minutes == 0:
            return {"description": "That's right now!"}
        
        target_context = get_daytime_context(target.hour)
        parts = []
        
        if hours > 0:
            parts.append(f"{'1 hour' if hours == 1 else f'{hours} hours'}")
        if minutes > 0:
            parts.append(f"{'1 minute' if minutes == 1 else f'{minutes} minutes'}")
        
        time_str = " and ".join(parts) if parts else "less than a minute"
        
        if tomorrow:
            response = f"That will be in {time_str}, tomorrow {target_context}"
        else:
            response = f"That's in {time_str}, {target_context}"
            
        return {"description": response}
        
    except Exception as e:
        return {"error": f"I couldn't calculate that time: {str(e)}"}

def calculate_days_between(start_date: str, end_date: str, format: str = "natural") -> Dict[str, Union[int, str]]:
    """Calculate the days between two dates with enhanced natural language."""
    try:
        date1 = parse_date(start_date)
        date2 = parse_date(end_date)
        
        if not date1 or not date2:
            return {"error": "I don't understand one or both of those dates"}
        
        days_diff = abs((date2.date() - date1.date()).days)
        
        if format == "natural":
            # Get seasonal context for both dates
            season1 = get_seasonal_context(date1)
            season2 = get_seasonal_context(date2)
            
            if days_diff == 0:
                return {"description": "Those dates are the same day"}
            
            # Check if dates are in different seasons
            if season1 != season2:
                season_context = f", from {season1} to {season2}"
            else:
                season_context = f" {season1}"
            
            if days_diff == 1:
                response = "Those dates are just a day apart"
            elif days_diff < 7:
                response = f"Those dates are {days_diff} days apart"
            elif days_diff < 14:
                response = "Those dates are about a week apart"
            elif days_diff < 30:
                weeks = days_diff // 7
                remaining_days = days_diff % 7
                if remaining_days == 0:
                    response = f"Those dates are {weeks} {'week' if weeks == 1 else 'weeks'} apart"
                else:
                    response = f"Those dates are about {weeks} {'week' if weeks == 1 else 'weeks'} apart"
            elif days_diff < 60:
                response = "Those dates are about a month apart"
            else:
                months = days_diff // 30
                response = f"Those dates are about {months} {'month' if months == 1 else 'months'} apart"
            
            # Add seasonal context if relevant
            if season_context and days_diff > 7:
                response += season_context
                
            return {"description": response}
        else:
            return {
                "days_difference": days_diff,
                "start_date": date1.strftime("%Y-%m-%d"),
                "end_date": date2.strftime("%Y-%m-%d")
            }
    except Exception as e:
        return {"error": f"I couldn't compare those dates: {str(e)}"}

def format_templates_for_year(date_obj: datetime, current_year: int) -> str:
    """Helper function to format year context naturally."""
    year = date_obj.year
    if year == current_year:
        return ""
    elif year == current_year + 1:
        return " next year"
    elif year == current_year - 1:
        return " last year"
    else:
        return f" in {year}"

def format_date(date: str, format: str = "natural") -> Dict[str, str]:
    """Format a date string with enhanced natural language and context."""
    try:
        date_obj = parse_date(date)
        if not date_obj:
            return {"error": "I don't understand that date format"}
        
        if format == "natural":
            today = datetime.now().date()
            date_diff = (date_obj.date() - today).days
            seasonal_context = get_seasonal_context(date_obj)
            year_context = format_templates_for_year(date_obj, today.year)
            
            # Check for special dates first
            date_str = date_obj.strftime("%B %d").lower()
            for name, special_date in COMMON_DATES.items():
                if special_date.lower() == date_str:
                    response = f"That's {name.title()}{year_context}"
                    if seasonal_context:
                        response += f", {seasonal_context}"
                    return {"description": response}
            
            # Regular date formatting with context
            if date_diff == 0:
                response = "That's today"
            elif date_diff == 1:
                response = "That's tomorrow"
            elif date_diff == -1:
                response = "That was yesterday"
            elif 0 < date_diff <= 7:
                day_name = date_obj.strftime("%A")
                response = f"That's this coming {day_name}"
            elif -7 <= date_diff < 0:
                day_name = date_obj.strftime("%A")
                response = f"That was last {day_name}"
            elif date_diff > 7 and date_diff <= 14:
                day_name = date_obj.strftime("%A")
                response = f"That's next {day_name}"
            else:
                month_name = date_obj.strftime("%B")
                day = int(date_obj.strftime("%d"))
                
                # More natural day formatting
                if day == 1:
                    day_str = "1st"
                elif day == 2:
                    day_str = "2nd"
                elif day == 3:
                    day_str = "3rd"
                elif day == 21:
                    day_str = "21st"
                elif day == 22:
                    day_str = "22nd"
                elif day == 23:
                    day_str = "23rd"
                elif day == 31:
                    day_str = "31st"
                else:
                    day_str = f"{day}th"
                
                response = f"That's {month_name} {day_str}{year_context}"
            
            # Add seasonal context for dates not immediate
            if seasonal_context and abs(date_diff) > 7:
                response += f", {seasonal_context}"
                
            return {"description": response}
        else:
            format_str = FORMAT_TEMPLATES.get(format, FORMAT_TEMPLATES["default"])
            if format == "custom" and isinstance(format, str):
                format_str = format
            return {
                "formatted_date": date_obj.strftime(format_str),
                "original_date": date,
                "format_used": format
            }
    except Exception as e:
        return {"error": f"I couldn't format that date: {str(e)}"}

def days_until_date(target_date: str, format: str = "natural") -> Dict[str, Union[int, str]]:
    """Calculate days until a specific date with enhanced natural language."""
    try:
        target = parse_date(target_date)
        if not target:
            return {"error": "I don't understand that date format"}
            
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_remaining = (target.date() - today.date()).days
        
        if format == "natural":
            target_season = get_seasonal_context(target)
            
            if days_remaining < 0:
                if days_remaining == -1:
                    response = "That was yesterday"
                elif days_remaining > -7:
                    response = f"That was {abs(days_remaining)} days ago"
                elif days_remaining > -30:
                    weeks = abs(days_remaining) // 7
                    response = f"That was {weeks} {'week' if weeks == 1 else 'weeks'} ago"
                else:
                    months = abs(days_remaining) // 30
                    response = f"That was about {months} {'month' if months == 1 else 'months'} ago"
            elif days_remaining == 0:
                response = "That's today"
            elif days_remaining == 1:
                response = f"That's tomorrow {target_season}"
            elif days_remaining < 7:
                day_name = target.strftime("%A")
                response = f"That's this coming {day_name} {target_season}"
            elif days_remaining < 14:
                day_name = target.strftime("%A")
                response = f"That's next {day_name} {target_season}"
            elif days_remaining < 30:
                weeks = days_remaining // 7
                response = f"That's in {weeks} {'week' if weeks == 1 else 'weeks'} {target_season}"
            else:
                months = days_remaining // 30
                response = f"That's in about {months} {'month' if months == 1 else 'months'} {target_season}"
            
            # Add special date context if applicable
            date_str = target.strftime("%B %d")
            for name, special_date in COMMON_DATES.items():
                if special_date.lower() == date_str.lower():
                    response += f" (it's {name.title()}!)"
                    break
                    
            return {"description": response.strip()}
        else:
            return {
                "days_remaining": days_remaining,
                "target_date": target.strftime("%Y-%m-%d"),
                "current_date": today.strftime("%Y-%m-%d")
            }
            
    except Exception as e:
        return {"error": f"I couldn't calculate that date: {str(e)}"}

def implementation(function: str, **kwargs) -> Dict[str, Any]:
    """Main implementation function that routes to the appropriate datetime function."""
    function_map = {
        "get_current_time": get_current_time,
        "get_current_date": get_current_date,
        "calculate_days_between": calculate_days_between,
        "days_until_date": days_until_date,
        "format_date": format_date,
        "time_until": time_until
    }
    
    if function not in function_map:
        return {"error": f"Unknown function: {function}"}
        
    return function_map[function](**kwargs) 