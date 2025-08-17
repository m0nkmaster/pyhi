#!/usr/bin/env python3
"""
Train Times MCP Server for PyHi Voice Assistant.
Provides UK railway departure and arrival information through MCP.
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any

import requests
from pydantic import BaseModel, Field
from mcp.server import FastMCP
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Rail Data API Configuration
API_BASE_URL = "https://api1.raildata.org.uk/1010-live-arrival-and-departure-boards-arr-and-dep1_1/LDBWS/api/20220120/"
API_KEY = os.getenv("RAIL_LIVE_DEPARTURE_BOARD_API_KEY")

# Pydantic Models for Type Safety
class TrainService(BaseModel):
    """Train service information model."""
    scheduled_departure: Optional[str] = Field(description="Scheduled departure time (HH:MM)")
    estimated_departure: Optional[str] = Field(description="Estimated departure time or status")
    destination: Optional[str] = Field(description="Destination station name")
    platform: Optional[str] = Field(description="Platform number")
    operator: Optional[str] = Field(description="Train operator")
    status: Optional[str] = Field(description="Service status")

class TrainTimesResponse(BaseModel):
    """Train times response model."""
    services: List[TrainService] = Field(description="List of train services")
    status: str = Field(description="Response status")
    message: str = Field(description="Response message")
    station: str = Field(description="Station code requested")

class TrainTimesError(BaseModel):
    """Error response model."""
    error: str = Field(description="Error message")
    status: str = Field(description="Error status")

# Initialize MCP server
mcp = FastMCP("train-times-server")

# Common UK station codes for reference
COMMON_STATIONS = {
    "PAD": "London Paddington",
    "KGX": "London King's Cross", 
    "VIC": "London Victoria",
    "WAT": "London Waterloo",
    "EUS": "London Euston",
    "LST": "London Liverpool Street",
    "CHX": "London Charing Cross",
    "LBG": "London Bridge",
    "MAN": "Manchester Piccadilly",
    "BHM": "Birmingham New Street",
    "GLC": "Glasgow Central",
    "EDB": "Edinburgh Waverley",
    "BRI": "Bristol Temple Meads",
    "BAT": "Bath Spa",
    "OXF": "Oxford",
    "CBG": "Cambridge",
    "YRK": "York",
    "NEW": "Newcastle",
    "LDS": "Leeds",
    "SHF": "Sheffield",
    "NOT": "Nottingham",
    "LEI": "Leicester",
    "COV": "Coventry",
    "RDG": "Reading",
    "SOU": "Southampton Central",
    "BTN": "Brighton",
    "CDF": "Cardiff Central",
    "SWA": "Swansea"
}

def format_service(service: dict) -> TrainService:
    """Format a service object into a user-friendly format."""
    try:
        return TrainService(
            scheduled_departure=service.get('std'),
            estimated_departure=service.get('etd'),
            destination=service.get('destination', [{}])[0].get('locationName') if service.get('destination') else None,
            platform=service.get('platform'),
            operator=service.get('operator'),
            status=service.get('etd', 'On time')
        )
    except Exception as e:
        logger.error(f"Error formatting service: {e}")
        return TrainService()

# MCP Tools
@mcp.tool()
async def get_train_times(
    station: str,
    destination: Optional[str] = None,
    num_results: int = 5
) -> str:
    """
    Get live train departure and arrival information for a UK railway station.
    
    Args:
        station: The 3-letter CRS code for the station (e.g., 'PAD' for London Paddington)
        destination: Optional 3-letter CRS code for destination station to filter results
        num_results: Number of services to return (max 10, default 5)
    
    Returns:
        JSON string with train departure information or error message
    """
    try:
        if not API_KEY:
            logger.error("RAIL_LIVE_DEPARTURE_BOARD_API_KEY not found in environment variables")
            return json.dumps({"error": "Rail API key not configured.", "status": "error"})
        
        if not station or len(station) != 3:
            return json.dumps({"error": "Station code must be a 3-letter CRS code (e.g. 'PAD')", "status": "error"})
        
        if num_results < 1 or num_results > 10:
            num_results = 5
        
        url = f"{API_BASE_URL}GetArrDepBoardWithDetails/{station.upper()}"
        
        headers = {
            "x-apikey": API_KEY,
            "accept": "application/json",
            "User-Agent": "PyHi Voice Assistant/1.0"
        }
        
        logger.info(f"Fetching train times for station {station.upper()}")
        
        session = requests.Session()
        response = session.get(url, headers=headers, verify=True, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract services from the response
        services = data.get('trainServices', [])[:num_results]
        formatted_services = [format_service(service) for service in services]
        
        # Filter by destination if specified
        if destination:
            destination_upper = destination.upper()
            filtered_services = []
            for service in formatted_services:
                if service.destination and destination_upper in service.destination.upper():
                    filtered_services.append(service)
            formatted_services = filtered_services
        
        # Convert to dict for JSON serialization
        services_dict = [service.model_dump() for service in formatted_services]
        
        result = TrainTimesResponse(
            services=formatted_services,
            status="success",
            message=f"Found {len(formatted_services)} services from {station.upper()}",
            station=station.upper()
        )
        
        return json.dumps(result.model_dump())
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching train times: {e}")
        return json.dumps({
            "error": f"Unable to fetch train data for station {station}. Please check the station code.",
            "status": "error"
        })
    except Exception as e:
        logger.error(f"Error processing train times: {e}")
        return json.dumps({
            "error": f"Failed to process train times for {station}",
            "status": "error"
        })

@mcp.tool()
async def list_station_codes(search: Optional[str] = None) -> str:
    """
    List common UK railway station codes.
    
    Args:
        search: Optional search term to filter stations
    
    Returns:
        JSON string with station codes and names
    """
    try:
        stations = COMMON_STATIONS.copy()
        
        if search:
            search_term = search.lower()
            filtered_stations = {
                code: name for code, name in stations.items()
                if search_term in name.lower() or search_term in code.lower()
            }
            stations = filtered_stations
        
        result = {
            "stations": [
                {"code": code, "name": name}
                for code, name in stations.items()
            ],
            "count": len(stations),
            "status": "success"
        }
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error listing station codes: {e}")
        return json.dumps({"error": "Failed to list station codes", "status": "error"})

# MCP Resources
@mcp.resource("trains://stations")
async def stations_resource() -> str:
    """
    Resource endpoint for UK railway station codes.
    """
    return await list_station_codes()

@mcp.resource("trains://departures/{station}")
async def departures_resource(station: str) -> str:
    """
    Resource endpoint for live departure information.
    """
    return await get_train_times(station)

@mcp.resource("trains://common-routes")
async def common_routes_resource() -> str:
    """
    Resource endpoint for common UK railway routes.
    """
    common_routes = [
        {"from": "PAD", "to": "BAT", "description": "London Paddington to Bath Spa"},
        {"from": "PAD", "to": "BRI", "description": "London Paddington to Bristol Temple Meads"},
        {"from": "KGX", "to": "YRK", "description": "London King's Cross to York"},
        {"from": "KGX", "to": "EDB", "description": "London King's Cross to Edinburgh"},
        {"from": "EUS", "to": "MAN", "description": "London Euston to Manchester Piccadilly"},
        {"from": "EUS", "to": "BHM", "description": "London Euston to Birmingham New Street"},
        {"from": "VIC", "to": "BTN", "description": "London Victoria to Brighton"},
        {"from": "WAT", "to": "SOU", "description": "London Waterloo to Southampton Central"}
    ]
    
    return json.dumps({"routes": common_routes, "status": "success"})

# MCP Prompts
@mcp.prompt("train-journey-planning")
async def train_journey_prompt(origin: str, destination: str) -> str:
    """
    Prompt template for train journey planning assistance.
    """
    return f"""Help plan a train journey from {origin} to {destination}. 
Use the get_train_times tool to check departure times from the origin station.
If you need station codes, use the list_station_codes tool to find the correct 3-letter codes.
Provide helpful information about departure times, platforms, and any connections needed."""

@mcp.prompt("station-help")
async def station_help_prompt() -> str:
    """
    Prompt template for station code assistance.
    """
    return """To get train times, you need 3-letter station codes (CRS codes). 
Common examples:
- PAD = London Paddington
- KGX = London King's Cross  
- VIC = London Victoria
- MAN = Manchester Piccadilly
- BHM = Birmingham New Street

Use the list_station_codes tool to search for specific stations or get a full list."""

# Server startup
def main():
    """Run the MCP train times server."""
    logger.info("Starting Train Times MCP Server...")
    
    # Run the server using stdio transport
    mcp.run("stdio")

if __name__ == "__main__":
    main()