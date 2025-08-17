#!/usr/bin/env python3
"""
Streaming/Watchmode MCP Server
Provides streaming service search and availability tools for PyHi voice assistant.
"""

import asyncio
import json
import logging
import os
from typing import Optional, List

from mcp.server import FastMCP
from pydantic import BaseModel, Field
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Watchmode API Configuration
API_BASE_URL = "https://api.watchmode.com/v1"
API_KEY = os.getenv("WATCHMODE_API_KEY")
DEFAULT_REGION = "GB"  # United Kingdom

# Initialize MCP server
mcp = FastMCP("streaming")


class StreamingSource(BaseModel):
    """Streaming source model."""
    service: str = Field(..., description="Name of the streaming service")
    type: str = Field(..., description="Type of access (subscription, free, rent, buy)")
    price: Optional[str] = Field(None, description="Price if applicable")
    url: Optional[str] = Field(None, description="Direct URL to watch")


class SearchResult(BaseModel):
    """Search result model."""
    id: str = Field(..., description="Watchmode title ID")
    name: str = Field(..., description="Title name")
    type: str = Field(..., description="Type (movie, tv_series)")
    year: Optional[str] = Field(None, description="Release year")


class StreamingResponse(BaseModel):
    """Standard streaming response."""
    status: str = Field(..., description="Success or error status")
    message: Optional[str] = Field(None, description="Response message")
    results: Optional[List[SearchResult]] = Field(None, description="Search results")
    title: Optional[str] = Field(None, description="Title name")
    year: Optional[str] = Field(None, description="Release year")
    type: Optional[str] = Field(None, description="Content type")
    sources: Optional[List[StreamingSource]] = Field(None, description="Streaming sources")


@mcp.tool()
async def search_streaming_titles(query: str) -> StreamingResponse:
    """
    Search for movies and TV shows.
    
    Args:
        query: The search query for finding movies or TV shows
    
    Returns:
        StreamingResponse with search results
    """
    try:
        if not API_KEY:
            return StreamingResponse(
                status="error",
                message="Watchmode API key not configured"
            )
        
        url = f"{API_BASE_URL}/autocomplete-search/"
        
        params = {
            "apiKey": API_KEY,
            "search_value": query,
            "search_type": 1  # 1 for title search
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Format the results
        results = []
        for result in data.get('results', []):
            results.append(SearchResult(
                id=str(result['id']),
                name=result['name'],
                type=result['type'],
                year=str(result.get('year', 'N/A'))
            ))
        
        return StreamingResponse(
            status="success",
            message=f"Found {len(results)} results for '{query}'",
            results=results
        )
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error searching for titles: {e}")
        return StreamingResponse(
            status="error",
            message=f"Failed to search for titles: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error searching for titles: {e}")
        return StreamingResponse(
            status="error",
            message=f"Unexpected error: {str(e)}"
        )


@mcp.tool()
async def get_streaming_sources(title_id: str, region: str = DEFAULT_REGION) -> StreamingResponse:
    """
    Get streaming availability for a specific title.
    
    Args:
        title_id: The Watchmode title ID
        region: Two-letter country code (default: GB for United Kingdom)
    
    Returns:
        StreamingResponse with streaming availability information
    """
    try:
        if not API_KEY:
            return StreamingResponse(
                status="error",
                message="Watchmode API key not configured"
            )
        
        url = f"{API_BASE_URL}/title/{title_id}/details/"
        
        params = {
            "apiKey": API_KEY,
            "append_to_response": "sources",
            "regions": region
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Extract and format streaming sources
        sources = []
        for source in data.get('sources', []):
            if source.get('region') == region:
                sources.append(StreamingSource(
                    service=source.get('name', 'Unknown'),
                    type=source.get('type', 'Unknown'),
                    price=source.get('price'),
                    url=source.get('web_url')
                ))
        
        return StreamingResponse(
            status="success",
            message=f"Found {len(sources)} streaming options",
            title=data.get('title'),
            year=str(data.get('year', 'N/A')),
            type=data.get('type'),
            sources=sources
        )
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching streaming sources: {e}")
        return StreamingResponse(
            status="error",
            message=f"Failed to fetch streaming sources: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching streaming sources: {e}")
        return StreamingResponse(
            status="error",
            message=f"Unexpected error: {str(e)}"
        )


@mcp.tool()
async def find_where_to_watch(title: str, region: str = DEFAULT_REGION) -> StreamingResponse:
    """
    Search for a title and get its streaming availability in one step.
    
    Args:
        title: The title to search for and find streaming options
        region: Two-letter country code (default: GB for United Kingdom)
    
    Returns:
        StreamingResponse with streaming availability for the best match
    """
    try:
        # First search for the title
        search_response = await search_streaming_titles(title)
        
        if search_response.status != "success" or not search_response.results:
            return StreamingResponse(
                status="error",
                message=f"No results found for '{title}'"
            )
        
        # Use the first (best) match
        best_match = search_response.results[0]
        
        # Get streaming sources for the best match
        sources_response = await get_streaming_sources(best_match.id, region)
        
        if sources_response.status != "success":
            return sources_response
        
        return StreamingResponse(
            status="success",
            message=f"Found streaming options for '{best_match.name}' ({best_match.year})",
            title=sources_response.title,
            year=sources_response.year,
            type=sources_response.type,
            sources=sources_response.sources
        )
        
    except Exception as e:
        logger.error(f"Error in find_where_to_watch: {e}")
        return StreamingResponse(
            status="error",
            message=f"Failed to find streaming options: {str(e)}"
        )


@mcp.resource("streaming://popular")
async def get_popular_content() -> str:
    """Get popular streaming content as a resource."""
    return json.dumps({
        "message": "Popular streaming content resource (requires API implementation)",
        "note": "This would show trending movies and TV shows"
    })


@mcp.prompt("streaming-guide")
async def streaming_guide_prompt() -> str:
    """Provide guidance on finding streaming content."""
    return """
    I can help you find where movies and TV shows are available to stream in the UK.
    
    You can ask me to:
    - Search for a specific movie or TV show
    - Find where something is available to watch
    - Get streaming options for a particular title
    
    Just ask something like "Where can I watch [title]?" or "Find streaming options for [movie name]"
    """


if __name__ == "__main__":
    # Run the MCP server
    mcp.run("stdio")