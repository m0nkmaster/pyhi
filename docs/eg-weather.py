#!/usr/bin/env python3
"""
Example MCP Weather Server for PyHi Voice Assistant
This demonstrates how to convert your existing weather function to an MCP server.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path

import requests
from pydantic import BaseModel, Field
from mcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# API Configuration
API_KEY = os.getenv("TOMORROW_IO_API_KEY")
WEATHER_BASE_URL = "https://api.tomorrow.io/v4/weather/realtime"
GEOCODE_BASE_URL = "https://nominatim.openstreetmap.org/search"

# Pydantic Models for Type Safety
class WeatherData(BaseModel):
    """Weather data response model."""
    temperature: float = Field(description="Temperature in specified units")
    condition: str = Field(description="Weather condition description")
    humidity: float = Field(description="Humidity percentage")
    wind_speed: float = Field(description="Wind speed in specified units")
    precipitation_probability: float = Field(description="Chance of precipitation (0-100)")
    location: str = Field(description="Location name")
    units: str = Field(description="Unit system used")
    timestamp: str = Field(description="ISO timestamp of data")

class LocationData(BaseModel):
    """Location coordinate data."""
    lat: float
    lon: float
    name: str

class WeatherError(BaseModel):
    """Error response model."""
    error: str = Field(description="Error message")

# Initialize MCP server
mcp = FastMCP("weather-server")

# Utility Functions (from your existing implementation)
def validate_location(location: str) -> bool:
    """Validate location string."""
    if not location or not isinstance(location, str):
        return False
    return bool(location.strip())

async def get_location_coordinates(location: str) -> Optional[LocationData]:
    """Get coordinates for a location using OpenStreetMap's Nominatim service."""
    if not validate_location(location):
        raise ValueError("Invalid location string")
        
    try:
        headers = {
            'User-Agent': 'PyHi Voice Assistant MCP Server/1.0',
            'Accept': 'application/json'
        }
        
        params = {
            'q': location.strip(),
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        # Use asyncio-compatible requests (you might want to use httpx for true async)
        response = requests.get(
            GEOCODE_BASE_URL,
            params=params,
            headers=headers,
            timeout=10
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
        
        return LocationData(
            lat=float(location_data["lat"]),
            lon=float(location_data["lon"]),
            name=name
        )
    except Exception as e:
        logger.error(f"Error getting location coordinates: {str(e)}")
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

# MCP Tools
@mcp.tool()
async def get_weather(
    location: str,
    units: Literal["imperial", "metric"] = "imperial"
) -> WeatherData | WeatherError:
    """
    Get detailed current weather information for any location using the Tomorrow.io API.
    
    Args:
        location: The location to get weather for. Can be a city name, address, or landmark
                 (e.g., 'San Francisco, CA', 'Tokyo, Japan', 'Eiffel Tower')
        units: The unit system to use for temperature and wind speed (imperial or metric)
    
    Returns:
        WeatherData with current conditions or WeatherError if something goes wrong
    """
    try:
        if not validate_location(location):
            return WeatherError(error="Please provide a valid location.")
            
        if not API_KEY:
            logger.error("TOMORROW_IO_API_KEY not found in environment variables")
            return WeatherError(error="Weather API key not configured.")
            
        # Get location coordinates
        try:
            location_data = await get_location_coordinates(location)
        except ValueError as e:
            return WeatherError(error=str(e))
        except Exception:
            return WeatherError(error=f"Could not find location '{location}'.")
            
        if not location_data:
            return WeatherError(error=f"Could not find location '{location}'.")
            
        # Get weather data
        params = {
            "apikey": API_KEY,
            "location": f"{location_data.lat},{location_data.lon}",
            "units": "metric"  # Always get metric from API, convert if needed
        }
        
        response = requests.get(
            WEATHER_BASE_URL,
            params=params,
            timeout=10,
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        
        data = response.json()
        weather = data.get("data", {}).get("values", {})
        
        if not weather:
            return WeatherError(error="No weather data available for this location.")
        
        # Convert temperature and wind speed based on units
        temp = weather.get("temperature", 0)
        wind_speed = weather.get('windSpeed', 0)
        
        if units == "imperial":
            temp = round(temp * 9/5 + 32, 1)
            wind_speed = round(wind_speed * 0.621371, 1)  # Convert to mph
        else:
            temp = round(temp, 1)
            wind_speed = round(wind_speed, 1)
            
        return WeatherData(
            temperature=temp,
            condition=get_weather_code_description(weather.get("weatherCode", 0)),
            humidity=round(weather.get('humidity', 0), 1),
            wind_speed=wind_speed,
            precipitation_probability=round(weather.get('precipitationProbability', 0)),
            location=location_data.name,
            units=units,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except requests.RequestException as e:
        logger.error(f"Weather API request failed: {str(e)}")
        return WeatherError(error="Unable to fetch weather data. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error while getting weather data: {str(e)}")
        return WeatherError(error="An unexpected error occurred.")

# MCP Resources
@mcp.resource("weather://current/{location}")
async def current_weather_resource(location: str) -> str:
    """
    Resource endpoint for current weather data.
    This provides cached weather data access without side effects.
    """
    result = await get_weather(location)
    if isinstance(result, WeatherError):
        return json.dumps(result.model_dump())
    return json.dumps(result.model_dump())

@mcp.resource("weather://locations")
async def weather_locations_resource() -> str:
    """
    Resource endpoint listing recently queried weather locations.
    This could be enhanced to track usage history.
    """
    # This is a simple example - you could implement actual tracking
    recent_locations = [
        "San Francisco, CA",
        "New York, NY", 
        "London, UK",
        "Tokyo, Japan"
    ]
    return json.dumps({"recent_locations": recent_locations})

# MCP Prompts
@mcp.prompt("weather-summary")
async def weather_summary_prompt(location: str) -> str:
    """
    Prompt template for getting a comprehensive weather summary.
    """
    return f"""Please provide a detailed weather summary for {location}. 
Include current conditions, temperature, humidity, wind, and any relevant 
advice for outdoor activities. Use the get_weather tool to fetch current data."""

@mcp.prompt("weather-comparison")
async def weather_comparison_prompt(location1: str, location2: str) -> str:
    """
    Prompt template for comparing weather between two locations.
    """
    return f"""Compare the current weather conditions between {location1} and {location2}.
Use the get_weather tool for both locations and provide insights about 
the differences in temperature, conditions, and which location might be 
better for outdoor activities."""

# Server Configuration and Startup
async def main():
    """Run the MCP weather server."""
    logger.info("Starting MCP Weather Server...")
    
    # Run the server
    async with mcp.run_server() as server:
        logger.info("Weather MCP Server is running...")
        await server.wait_for_completion()

if __name__ == "__main__":
    # This allows the server to be run standalone or imported
    asyncio.run(main())
