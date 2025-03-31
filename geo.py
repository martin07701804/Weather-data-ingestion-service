from geopy.geocoders import Nominatim

def get_coordinates(location_name: str):
    geolocator = Nominatim(user_agent="openmeteo_chatbot")
    loc = geolocator.geocode(location_name)
    if loc:
        return (loc.latitude, loc.longitude)
    else:
        raise ValueError(f"Location '{location_name}' not found.")