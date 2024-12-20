"""Implementation of the train times function using Rail Data API."""

import logging
import json
import os
from typing import Optional
import requests

# Configure logging 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rail Data API Configuration
API_BASE_URL = "https://api1.raildata.org.uk/1010-live-arrival-and-departure-boards-arr-and-dep1_1/LDBWS/api/20220120/"
API_KEY = os.getenv("RAIL_LIVE_DEPARTURE_BOARD_API_KEY")

def format_service(service: dict) -> dict:
    """Format a service object into a user-friendly format."""
    try:
        return {
            "scheduled_departure": service.get('std'),
            "estimated_departure": service.get('etd'),
            "destination": service.get('destination', [{}])[0].get('locationName'),
            "platform": service.get('platform'),
            "operator": service.get('operator'),
            "status": service.get('etd', 'On time')
        }
    except Exception as e:
        logger.error(f"Error formatting service: {e}")
        return {}

def implementation(
    station: str,
    destination: Optional[str] = None,
    num_results: int = 5
) -> str:
    """
    Get live train departure information using Rail Data API.
    
    Args:
        station: Three-letter CRS code for the station
        destination: Optional three-letter CRS code for the destination station
        num_results: Number of services to return (max 10)
        
    Returns:
        JSON string containing departure information
    """
    try:
        url = f"{API_BASE_URL}GetArrDepBoardWithDetails/{station.upper()}"
        
        headers = {
            "x-apikey": API_KEY,
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, verify=True)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract services from the correct path in the response
        services = data.get('trainServices', [])[:num_results]
        formatted_services = [format_service(service) for service in services]
        
        if destination:
            formatted_services = [
                service for service in formatted_services 
                if service.get('destination', '').upper() == destination.upper()
            ]
        
        return json.dumps({
            "services": formatted_services,
            "status": "success",
            "message": f"Found {len(formatted_services)} services from {station}"
        })
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching train times: {e}", exc_info=True)
        return json.dumps({
            "trainServices": [],
            "message": f"No train services available for station or invalid station name {station}",
            "status": "error"
        })
    except Exception as e:
        logger.error(f"Error processing train times: {e}", exc_info=True)
        return json.dumps({
            "trainServices": [],
            "message": f"No train services available for station or invalid station name {station}",
            "status": "error"
        })