import googlemaps
import os
from typing import Tuple, Optional, Dict
from decimal import Decimal

class MapsService:
    """
    Service for handling Google Maps API operations
    """
    
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if self.api_key:
            self.gmaps = googlemaps.Client(key=self.api_key)
        else:
            self.gmaps = None
            print("Warning: GOOGLE_MAPS_API_KEY not found in environment variables")
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to latitude and longitude coordinates
        
        Args:
            address: Street address to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        if not self.gmaps:
            print("Google Maps client not available - using fallback coordinates")
            return self._get_fallback_coordinates(address)
        
        try:
            geocode_result = self.gmaps.geocode(address)
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return (location['lat'], location['lng'])
            return None
        except Exception as e:
            print(f"Geocoding error for address '{address}': {str(e)}")
            return self._get_fallback_coordinates(address)
    
    def calculate_distance_and_duration(self, 
                                      origin_address: str, 
                                      destination_address: str,
                                      origin_coords: Optional[Tuple[float, float]] = None,
                                      destination_coords: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Calculate distance and duration between two locations using Google Maps
        
        Args:
            origin_address: Starting address
            destination_address: Destination address
            origin_coords: Optional coordinates for origin (lat, lng)
            destination_coords: Optional coordinates for destination (lat, lng)
            
        Returns:
            Dictionary with distance_km, duration_minutes, and route info
        """
        if not self.gmaps:
            print("Google Maps client not available - using fallback calculation")
            return self._calculate_fallback_distance(
                origin_address, destination_address, origin_coords, destination_coords
            )
        
        try:
            # Use coordinates if available, otherwise use addresses
            origin = origin_coords if origin_coords else origin_address
            destination = destination_coords if destination_coords else destination_address
            
            # Get distance matrix
            result = self.gmaps.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode="driving",
                units="metric",
                avoid="tolls"
            )
            
            if result['status'] == 'OK' and result['rows'][0]['elements'][0]['status'] == 'OK':
                element = result['rows'][0]['elements'][0]
                
                # Extract distance and duration
                distance_meters = element['distance']['value']
                distance_km = distance_meters / 1000
                duration_seconds = element['duration']['value']
                duration_minutes = duration_seconds / 60
                
                return {
                    'distance_km': round(distance_km, 2),
                    'duration_minutes': round(duration_minutes, 0),
                    'distance_text': element['distance']['text'],
                    'duration_text': element['duration']['text'],
                    'status': 'success'
                }
            else:
                print(f"Distance calculation failed: {result}")
                return self._calculate_fallback_distance(
                    origin_address, destination_address, origin_coords, destination_coords
                )
                
        except Exception as e:
            print(f"Error calculating distance: {str(e)}")
            return self._calculate_fallback_distance(
                origin_address, destination_address, origin_coords, destination_coords
            )
    
    def _get_fallback_coordinates(self, address: str) -> Tuple[float, float]:
        """
        Provide fallback coordinates when geocoding is not available
        This is a simplified approach - in production you might want to use a local database
        """
        # Simple fallback based on common city patterns
        address_lower = address.lower()
        
        # Sample coordinates for major cities (you can expand this)
        if 'new york' in address_lower or 'nyc' in address_lower:
            return (40.7128, -74.0060)
        elif 'los angeles' in address_lower or 'la' in address_lower:
            return (34.0522, -118.2437)
        elif 'chicago' in address_lower:
            return (41.8781, -87.6298)
        elif 'toronto' in address_lower:
            return (43.6532, -79.3832)
        else:
            # Default to a central location (e.g., Toronto downtown)
            return (43.6532, -79.3832)
    
    def _calculate_fallback_distance(self, 
                                   origin_address: str, 
                                   destination_address: str,
                                   origin_coords: Optional[Tuple[float, float]] = None,
                                   destination_coords: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Calculate distance using Haversine formula when Google Maps is not available
        """
        if not origin_coords:
            origin_coords = self._get_fallback_coordinates(origin_address)
        if not destination_coords:
            destination_coords = self._get_fallback_coordinates(destination_address)
        
        distance_km = self._haversine_distance(
            origin_coords[0], origin_coords[1],
            destination_coords[0], destination_coords[1]
        )
        
        # Estimate duration based on average city driving speed (30 km/h)
        duration_minutes = (distance_km / 30) * 60
        
        return {
            'distance_km': round(distance_km, 2),
            'duration_minutes': round(duration_minutes, 0),
            'distance_text': f"{distance_km:.1f} km",
            'duration_text': f"{int(duration_minutes)} mins",
            'status': 'fallback'
        }
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        import math
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate that coordinates are within reasonable bounds
        """
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)


# Create a singleton instance
maps_service = MapsService() 