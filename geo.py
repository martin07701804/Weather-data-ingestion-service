from geopy.geocoders import Nominatim
import logging # Optional: Use logging for cleaner output


def get_coordinates(location_name: str, api_counts: dict):
    """
    Gets coordinates for a location using Nominatim geocoder.
    Increments the geocoding API call count.

    Args:
        location_name: The name of the location to geocode.
        api_counts: Dictionary to track API call counts.

    Returns:
        A tuple (latitude, longitude).

    Raises:
        ValueError: If the location is not found.
    """
    geolocator = Nominatim(user_agent="openmeteo_chatbot_v2")
    print(f"  [API Call] Attempting geocoding for: {location_name}")


    api_counts["geocoding"] += 1

    try:
        loc = geolocator.geocode(location_name, timeout=10)
        if loc:

            return (loc.latitude, loc.longitude)
        else:

            raise ValueError(f"Location '{location_name}' not found.")
    except Exception as e:

        raise ValueError(f"Geocoding failed for '{location_name}': {e}") from e