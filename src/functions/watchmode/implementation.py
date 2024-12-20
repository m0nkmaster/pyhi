"""Implementation of the Watchmode streaming service search function."""

import logging
import json
import os
from typing import Optional
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Watchmode API Configuration
API_BASE_URL = "https://api.watchmode.com/v1"
API_KEY = os.getenv("WATCHMODE_API_KEY")
DEFAULT_REGION = "GB"  # ISO 3166-1 alpha-2 code for United Kingdom

def search_title(query: str) -> dict:
    """Search for a title using Watchmode's autocomplete search."""
    try:
        url = f"{API_BASE_URL}/autocomplete-search/"
        
        params = {
            "apiKey": API_KEY,
            "search_value": query,
            "search_type": 1  # 1 for title search
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Format the results to be more user-friendly
        formatted_results = []
        for result in data.get('results', []):
            formatted_results.append({
                'id': result['id'],
                'name': result['name'],
                'type': result['type'],
                'year': result.get('year', 'N/A'),
            })
        
        return {
            "status": "success",
            "results": formatted_results
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching for title: {e}")
        return {
            "status": "error",
            "message": f"Failed to search for title: {str(e)}"
        }

def where_to_watch(title_id: str, region: str = DEFAULT_REGION) -> dict:
    """Get streaming availability for a specific title in the given region."""
    try:
        url = f"{API_BASE_URL}/title/{title_id}/details/"
        
        params = {
            "apiKey": API_KEY,
            "append_to_response": "sources",  # Include streaming source information
            "regions": region
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extract and format the streaming sources
        sources = data.get('sources', [])
        formatted_sources = []
        
        for source in sources:
            if source.get('region') == region:
                formatted_sources.append({
                    'service': source.get('name'),
                    'type': source.get('type'),  # subscription, free, rent, buy
                    'price': source.get('price'),
                    'url': source.get('web_url')
                })
        
        return {
            "status": "success",
            "title": data.get('title'),
            "year": data.get('year'),
            "type": data.get('type'),
            "sources": formatted_sources
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching streaming sources: {e}")
        return {
            "status": "error",
            "message": f"Failed to fetch streaming sources: {str(e)}"
        }

def implementation(
    action: str,
    query: Optional[str] = None,
    title_id: Optional[str] = None,
    region: str = DEFAULT_REGION
) -> str:
    """Main implementation function for Watchmode API integration."""
    try:
        if not API_KEY:
            raise ValueError("Watchmode API key not found in environment variables")

        if action == "search_title":
            if not query:
                return json.dumps({
                    "status": "error",
                    "message": "Search query is required"
                })
            result = search_title(query)
            
        elif action == "where_to_watch":
            if not title_id:
                return json.dumps({
                    "status": "error",
                    "message": "Title ID is required"
                })
            result = where_to_watch(title_id, region)
            
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unknown action: {action}"
            })

        return json.dumps(result)

    except Exception as e:
        logger.error(f"Watchmode operation failed: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Watchmode operation failed: {str(e)}"
        })
