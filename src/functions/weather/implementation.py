"""Weather function implementation using Tomorrow.io API."""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Union, TypedDict, Literal
from dotenv import load_dotenv
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("TOMORROW_IO_API_KEY")
WEATHER_BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"
GEOCODE_BASE_URL = "https://nominatim.openstreetmap.org/search"

# Constants
VALID_UNITS = Literal["imperial", "metric"]
DEFAULT_TIMEOUT = 10
RATE_LIMIT_DELAY = 1.0

# Type definitions
class LocationData(TypedDict):
    lat: float
    lon: float
    name: str

class WeatherResponse(TypedDict):
    temperature: float
    condition: str
    humidity: float
    wind_speed: float
    precipitation_probability: float
    location: str
    units: str
    timestamp: str

def validate_location(location: str) -> bool:
    """Validate location string."""
    if not location or not isinstance(location, str):
        return False
    return bool(location.strip())

def get_location_coordinates(location: str) -> Optional[LocationData]:
    """Get coordinates for a location using OpenStreetMap's Nominatim service."""
    if not validate_location(location):
        raise ValueError("Invalid location string")
        
    try:
        time.sleep(RATE_LIMIT_DELAY)
        
        headers = {
            'User-Agent': 'PyHi Voice Assistant/1.0',
            'Accept': 'application/json'
        }
        
        params = {
            'q': location.strip(),
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        response = requests.get(
            GEOCODE_BASE_URL,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        if not data:
            logger.warning(f"No coordinates found for location: {location}")
            return None
            
        location_data = data[0]
        address = location_data.get('address', {})
        name = (
            address.get('city') or 
            address.get('town') or 
            address.get('village') or 
            location_data.get('display_name', location).split(',')[0]
        )
        
        return {
            "lat": float(location_data["lat"]),
            "lon": float(location_data["lon"]),
            "name": name
        }
    except requests.Timeout:
        logger.error("Timeout while getting location coordinates")
        raise Exception("Request timed out while getting location coordinates")
    except requests.RequestException as e:
        logger.error(f"Request failed while getting coordinates: {str(e)}")
        raise Exception(f"Error getting location coordinates: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while getting coordinates: {str(e)}")
        raise

def get_weather_code_description(code: int) -> str:
    """Convert weather code to description."""
    weather_codes = {
        1000: "Clear, Sunny",
        1100: "Mostly Clear",
        1101: "Partly Cloudy",
        1102: "Mostly Cloudy",
        1001: "Cloudy",
        2000: "Fog",
        2100: "Light Fog",
        4000: "Drizzle",
        4001: "Rain",
        4200: "Light Rain",
        4201: "Heavy Rain",
        5000: "Snow",
        5001: "Flurries",
        5100: "Light Snow",
        5101: "Heavy Snow",
        6000: "Freezing Drizzle",
        6001: "Freezing Rain",
        6200: "Light Freezing Rain",
        6201: "Heavy Freezing Rain",
        7000: "Ice Pellets",
        7101: "Heavy Ice Pellets",
        7102: "Light Ice Pellets",
        8000: "Thunderstorm"
    }
    return weather_codes.get(code, "Unknown")

def implementation(location: str, units: VALID_UNITS = "imperial") -> str:
    """Get current weather for a location."""
    try:
        if not validate_location(location):
            return json.dumps({"error": "Please provide a valid location."})
            
        if units not in ("imperial", "metric"):
            return json.dumps({"error": "Invalid units. Must be 'imperial' or 'metric'."})
            
        if not API_KEY:
            logger.error("TOMORROW_IO_API_KEY not found in environment variables")
            return json.dumps({"error": "Weather API key not configured."})
            
        try:
            location_data = get_location_coordinates(location)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": f"Could not find location '{location}'."})
            
        if not location_data:
            return json.dumps({"error": f"Could not find location '{location}'."})
            
        params = {
            "apikey": API_KEY,
            "location": f"{location_data['lat']},{location_data['lon']}",
            "units": "metric"
        }
        
        response = requests.get(
            WEATHER_BASE_URL,
            params=params,
            timeout=DEFAULT_TIMEOUT,
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        
        data = response.json()
        weather = data.get("data", {}).get("values", {})
        
        if not weather:
            return json.dumps({"error": "No weather data available for this location."})
        
        temp = weather.get("temperature", 0)
        if units == "imperial":
            temp = round(temp * 9/5 + 32, 1)
            wind_speed = round(weather.get('windSpeed', 0) * 0.621371, 1)  # Convert to mph
        else:
            temp = round(temp, 1)
            wind_speed = round(weather.get('windSpeed', 0), 1)
            
        result = {
            "temperature": temp,
            "condition": get_weather_code_description(weather.get("weatherCode", 0)),
            "humidity": round(weather.get('humidity', 0), 1),
            "wind_speed": wind_speed,
            "precipitation_probability": round(weather.get('precipitationProbability', 0)),
            "location": location_data["name"],
            "units": units,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result)
        
    except requests.RequestException as e:
        logger.error(f"Weather API request failed: {str(e)}")
        return json.dumps({"error": "Unable to fetch weather data. Please try again later."})
    except Exception as e:
        logger.error(f"Unexpected error while getting weather data: {str(e)}")
        return json.dumps({"error": "An unexpected error occurred."})

