import logging
from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)

def reverse_geocode(latitude: float, longitude: float) -> str:
    """Uses geopy Nominatim to convert coordinates to address. 
    Returns formatted address with Google Maps link."""
    try:
        # User_agent is required by Nominatim terms of service
        geolocator = Nominatim(user_agent="pomoshnik-telegram-bot")
        location = geolocator.reverse(f"{latitude}, {longitude}", language='ru')
        
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        
        if location:
            return f"📍 Адрес: {location.address}\n🗺️ Google Maps: {maps_link}"
        else:
            return f"📍 Координаты: {latitude}, {longitude}\n🗺️ Google Maps: {maps_link}\n(Не удалось определить точный адрес)"
            
    except Exception as e:
        logger.error(f"Reverse geocode failed: {e}")
        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        return f"📍 Координаты: {latitude}, {longitude}\n🗺️ Google Maps: {maps_link}\n(Ошибка геокодинга: {e})"
