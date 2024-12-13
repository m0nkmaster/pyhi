"""Weather function implementation."""

def implementation(location: str) -> dict:
    """
    Get the current weather for a location.
    This is a mock implementation - in a real app, you would call a weather API.
    """
    # Mock response - in reality you would call a weather API
    return {
        "temperature": "72°F",
        "condition": "Sunny",
        "location": location
    }
