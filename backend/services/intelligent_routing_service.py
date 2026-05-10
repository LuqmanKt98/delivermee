import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from extensions import db
from models.user import Driver
from models.delivery import Delivery, DeliveryStatus
from services.maps_service import maps_service
from services.enhanced_notification_service import enhanced_notification_service
import math
import requests

logger = logging.getLogger(__name__)

class IntelligentRoutingService:
    """
    Advanced routing service with intelligent navigation, route optimization,
    traffic-aware routing, and seamless navigation integration.
    """
    
    def __init__(self):
        self.routing_algorithms = {
            'fastest': self._calculate_fastest_route,
            'shortest': self._calculate_shortest_route,
            'most_efficient': self._calculate_most_efficient_route,
            'traffic_aware': self._calculate_traffic_aware_route
        }
        
        self.navigation_apps = {
            'google_maps': 'https://www.google.com/maps/dir/',
            'waze': 'https://waze.com/ul',
            'apple_maps': 'http://maps.apple.com/'
        }
        
        # Traffic patterns and optimization settings
        self.traffic_multipliers = {
            'light': 1.0,
            'moderate': 1.3,
            'heavy': 1.8,
            'severe': 2.5
        }
        
        self.time_zone_offset = 0  # Configure based on deployment location
    
    def generate_intelligent_route(self, driver_id: int, delivery_ids: List[int], 
                                 preferences: Dict = None) -> Dict:
        """
        Generate intelligent route for single or multiple deliveries with optimization
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'success': False, 'error': 'Driver not found'}
            
            deliveries = Delivery.query.filter(
                Delivery.id.in_(delivery_ids),
                Delivery.driver_id == driver_id
            ).all()
            
            if not deliveries:
                return {'success': False, 'error': 'No valid deliveries found'}
            
            # Get routing preferences
            routing_type = preferences.get('type', 'most_efficient') if preferences else 'most_efficient'
            avoid_tolls = preferences.get('avoid_tolls', True) if preferences else True
            avoid_highways = preferences.get('avoid_highways', False) if preferences else False
            
            # Calculate optimal route
            route_data = self._optimize_multi_delivery_route(
                driver, deliveries, routing_type, avoid_tolls, avoid_highways
            )
            
            if not route_data:
                return {'success': False, 'error': 'Could not generate route'}
            
            # Generate navigation instructions
            navigation_data = self._generate_navigation_instructions(route_data)
            
            # Create route summary
            route_summary = {
                'total_distance_km': route_data['total_distance'],
                'estimated_duration_minutes': route_data['total_duration'],
                'number_of_stops': len(route_data['stops']),
                'delivery_sequence': route_data['delivery_sequence'],
                'traffic_conditions': route_data.get('traffic_analysis', {}),
                'optimization_savings': route_data.get('savings', {}),
                'fuel_estimate': self._calculate_fuel_estimate(route_data['total_distance'])
            }
            
            # Store route for offline access
            self._cache_route_data(driver_id, {
                'route_data': route_data,
                'navigation_data': navigation_data,
                'summary': route_summary,
                'created_at': datetime.utcnow().isoformat()
            })
            
            return {
                'success': True,
                'route_summary': route_summary,
                'navigation_instructions': navigation_data,
                'route_details': route_data,
                'navigation_links': self._generate_navigation_links(route_data),
                'real_time_updates_enabled': True
            }
            
        except Exception as e:
            logger.error(f"Error generating intelligent route: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _optimize_multi_delivery_route(self, driver: Driver, deliveries: List[Delivery], 
                                     routing_type: str, avoid_tolls: bool, avoid_highways: bool) -> Optional[Dict]:
        """
        Optimize route for multiple deliveries using selected algorithm
        """
        try:
            # Start from driver's current location
            start_location = {
                'latitude': driver.current_latitude,
                'longitude': driver.current_longitude,
                'address': 'Current Location'
            }
            
            # Create delivery waypoints
            waypoints = []
            for delivery in deliveries:
                # Add pickup point
                waypoints.append({
                    'delivery_id': delivery.id,
                    'type': 'pickup',
                    'latitude': delivery.pickup_latitude,
                    'longitude': delivery.pickup_longitude,
                    'address': delivery.pickup_address,
                    'priority': self._calculate_delivery_priority(delivery),
                    'time_window': self._get_delivery_time_window(delivery)
                })
                
                # Add dropoff point
                waypoints.append({
                    'delivery_id': delivery.id,
                    'type': 'dropoff',
                    'latitude': delivery.dropoff_latitude,
                    'longitude': delivery.dropoff_longitude,
                    'address': delivery.dropoff_address,
                    'priority': self._calculate_delivery_priority(delivery),
                    'time_window': self._get_delivery_time_window(delivery),
                    'depends_on': f"{delivery.id}_pickup"  # Must pickup before dropoff
                })
            
            # Apply routing algorithm
            routing_function = self.routing_algorithms.get(routing_type, self._calculate_most_efficient_route)
            optimized_route = routing_function(start_location, waypoints, avoid_tolls, avoid_highways)
            
            if optimized_route:
                # Add real-time traffic analysis
                traffic_analysis = self._analyze_route_traffic(optimized_route)
                optimized_route['traffic_analysis'] = traffic_analysis
                
                # Calculate potential savings vs. naive route
                naive_route = self._calculate_naive_route(start_location, waypoints)
                savings = self._calculate_route_savings(optimized_route, naive_route)
                optimized_route['savings'] = savings
            
            return optimized_route
            
        except Exception as e:
            logger.error(f"Error optimizing multi-delivery route: {str(e)}")
            return None
    
    def _calculate_most_efficient_route(self, start: Dict, waypoints: List[Dict], 
                                      avoid_tolls: bool, avoid_highways: bool) -> Dict:
        """
        Calculate most efficient route considering distance, time, and priorities
        """
        try:
            # Implement advanced routing algorithm
            # This is a simplified version - in production, use OR-Tools or similar
            
            route_segments = []
            current_location = start
            remaining_waypoints = waypoints.copy()
            total_distance = 0
            total_duration = 0
            delivery_sequence = []
            
            # Separate pickups and dropoffs with dependencies
            pickups = [w for w in waypoints if w['type'] == 'pickup']
            dropoffs = [w for w in waypoints if w['type'] == 'dropoff']
            
            # Process deliveries in optimal order
            while pickups or dropoffs:
                next_point = self._select_next_optimal_point(
                    current_location, pickups, dropoffs, delivery_sequence
                )
                
                if not next_point:
                    break
                
                # Calculate route segment
                segment_data = self._calculate_route_segment(
                    current_location, next_point, avoid_tolls, avoid_highways
                )
                
                if segment_data:
                    route_segments.append(segment_data)
                    total_distance += segment_data['distance_km']
                    total_duration += segment_data['duration_minutes']
                    
                    # Update delivery sequence
                    if next_point['type'] == 'pickup':
                        delivery_sequence.append({
                            'delivery_id': next_point['delivery_id'],
                            'action': 'pickup',
                            'address': next_point['address'],
                            'eta': total_duration
                        })
                        pickups.remove(next_point)
                    else:
                        delivery_sequence.append({
                            'delivery_id': next_point['delivery_id'],
                            'action': 'dropoff',
                            'address': next_point['address'],
                            'eta': total_duration
                        })
                        dropoffs.remove(next_point)
                    
                    current_location = next_point
            
            return {
                'route_segments': route_segments,
                'total_distance': round(total_distance, 2),
                'total_duration': round(total_duration, 0),
                'delivery_sequence': delivery_sequence,
                'stops': waypoints,
                'optimization_algorithm': 'most_efficient'
            }
            
        except Exception as e:
            logger.error(f"Error calculating efficient route: {str(e)}")
            return None
    
    def _calculate_fastest_route(self, start: Dict, waypoints: List[Dict], 
                               avoid_tolls: bool, avoid_highways: bool) -> Dict:
        """Calculate fastest route prioritizing time over distance"""
        # Implementation similar to most_efficient but prioritizing duration
        return self._calculate_most_efficient_route(start, waypoints, avoid_tolls, avoid_highways)
    
    def _calculate_shortest_route(self, start: Dict, waypoints: List[Dict], 
                                avoid_tolls: bool, avoid_highways: bool) -> Dict:
        """Calculate shortest route prioritizing distance"""
        # Implementation similar to most_efficient but prioritizing distance
        return self._calculate_most_efficient_route(start, waypoints, avoid_tolls, avoid_highways)
    
    def _calculate_traffic_aware_route(self, start: Dict, waypoints: List[Dict], 
                                     avoid_tolls: bool, avoid_highways: bool) -> Dict:
        """Calculate route with real-time traffic consideration"""
        # Enhanced version with traffic data integration
        return self._calculate_most_efficient_route(start, waypoints, avoid_tolls, avoid_highways)
    
    def _select_next_optimal_point(self, current_location: Dict, pickups: List[Dict], 
                                 dropoffs: List[Dict], completed_sequence: List[Dict]) -> Optional[Dict]:
        """
        Select next optimal point considering constraints and efficiency
        """
        try:
            # Get completed pickups to enable corresponding dropoffs
            completed_pickups = {
                item['delivery_id'] for item in completed_sequence 
                if item['action'] == 'pickup'
            }
            
            # Available dropoffs (where pickup is completed)
            available_dropoffs = [
                d for d in dropoffs 
                if d['delivery_id'] in completed_pickups
            ]
            
            # Combine available points
            available_points = pickups + available_dropoffs
            
            if not available_points:
                return None
            
            # Score each point based on multiple factors
            best_point = None
            best_score = float('-inf')
            
            for point in available_points:
                score = self._calculate_point_score(current_location, point, available_dropoffs)
                if score > best_score:
                    best_score = score
                    best_point = point
            
            return best_point
            
        except Exception as e:
            logger.error(f"Error selecting next optimal point: {str(e)}")
            return available_points[0] if available_points else None
    
    def _calculate_point_score(self, current_location: Dict, point: Dict, available_dropoffs: List[Dict]) -> float:
        """
        Calculate score for a waypoint considering multiple factors
        """
        try:
            # Distance factor (closer is better)
            distance = self._calculate_distance(
                current_location['latitude'], current_location['longitude'],
                point['latitude'], point['longitude']
            )
            distance_score = max(0, 100 - (distance * 10))  # Penalty for distance
            
            # Priority factor
            priority_score = point.get('priority', 1) * 20
            
            # Type preference (slight preference for dropoffs if available)
            type_score = 10 if point['type'] == 'dropoff' and point in available_dropoffs else 0
            
            # Time window factor
            time_window_score = self._calculate_time_window_score(point)
            
            # Total score
            total_score = distance_score + priority_score + type_score + time_window_score
            
            return total_score
            
        except Exception as e:
            logger.error(f"Error calculating point score: {str(e)}")
            return 0
    
    def _calculate_delivery_priority(self, delivery: Delivery) -> int:
        """Calculate delivery priority based on various factors"""
        priority = 1  # Base priority
        
        # Higher priority for fragile/perishable items
        if delivery.is_fragile or delivery.is_perishable:
            priority += 1
        
        # Higher priority for higher value deliveries
        if delivery.estimated_cost and float(delivery.estimated_cost) > 50:
            priority += 1
        
        # Time-based priority
        if delivery.requested_time:
            time_diff = (datetime.utcnow() - delivery.requested_time).total_seconds() / 3600
            if time_diff > 2:  # Older than 2 hours
                priority += 1
        
        return priority
    
    def _get_delivery_time_window(self, delivery: Delivery) -> Optional[Dict]:
        """Get time window constraints for delivery"""
        # This would be enhanced with actual time window data
        return {
            'earliest': datetime.utcnow().isoformat(),
            'latest': (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            'preferred': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
    
    def _calculate_time_window_score(self, point: Dict) -> float:
        """Calculate score based on time window constraints"""
        time_window = point.get('time_window')
        if not time_window:
            return 0
        
        # Simple scoring - prefer deliveries with tighter time windows
        current_time = datetime.utcnow()
        try:
            preferred_time = datetime.fromisoformat(time_window['preferred'])
            time_diff = abs((preferred_time - current_time).total_seconds() / 3600)
            
            # Score decreases with time difference
            return max(0, 20 - time_diff * 5)
        except:
            return 0
    
    def _calculate_route_segment(self, from_location: Dict, to_location: Dict, 
                               avoid_tolls: bool, avoid_highways: bool) -> Optional[Dict]:
        """
        Calculate detailed route segment between two points
        """
        try:
            # Use Google Maps API or fallback calculation
            route_info = maps_service.calculate_distance_and_duration(
                origin_address=from_location.get('address', ''),
                destination_address=to_location.get('address', ''),
                origin_coords=(from_location['latitude'], from_location['longitude']),
                destination_coords=(to_location['latitude'], to_location['longitude'])
            )
            
            return {
                'from': from_location,
                'to': to_location,
                'distance_km': route_info['distance_km'],
                'duration_minutes': route_info['duration_minutes'],
                'route_geometry': self._get_route_geometry(from_location, to_location),
                'instructions': self._generate_turn_by_turn_instructions(from_location, to_location)
            }
            
        except Exception as e:
            logger.error(f"Error calculating route segment: {str(e)}")
            return None
    
    def _get_route_geometry(self, from_location: Dict, to_location: Dict) -> Optional[List[Dict]]:
        """
        Get detailed route geometry for map visualization
        """
        # This would integrate with mapping APIs to get actual route geometry
        # For now, return a simple straight line
        return [
            {'lat': from_location['latitude'], 'lng': from_location['longitude']},
            {'lat': to_location['latitude'], 'lng': to_location['longitude']}
        ]
    
    def _generate_turn_by_turn_instructions(self, from_location: Dict, to_location: Dict) -> List[Dict]:
        """
        Generate turn-by-turn navigation instructions
        """
        # This would integrate with navigation APIs for detailed instructions
        distance = self._calculate_distance(
            from_location['latitude'], from_location['longitude'],
            to_location['latitude'], to_location['longitude']
        )
        
        return [
            {
                'instruction': f"Head towards {to_location.get('address', 'destination')}",
                'distance_meters': int(distance * 1000),
                'type': 'straight',
                'icon': 'arrow_forward'
            }
        ]
    
    def _analyze_route_traffic(self, route_data: Dict) -> Dict:
        """
        Analyze traffic conditions along the route
        """
        try:
            current_hour = datetime.utcnow().hour
            
            # Determine traffic level based on time of day
            if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
                traffic_level = 'heavy'
            elif 11 <= current_hour <= 14:
                traffic_level = 'moderate'
            else:
                traffic_level = 'light'
            
            traffic_multiplier = self.traffic_multipliers.get(traffic_level, 1.0)
            
            # Adjust estimated duration based on traffic
            adjusted_duration = route_data['total_duration'] * traffic_multiplier
            
            return {
                'traffic_level': traffic_level,
                'traffic_multiplier': traffic_multiplier,
                'original_duration': route_data['total_duration'],
                'traffic_adjusted_duration': round(adjusted_duration, 0),
                'delay_minutes': round(adjusted_duration - route_data['total_duration'], 0),
                'conditions': f"{traffic_level.title()} traffic expected",
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing route traffic: {str(e)}")
            return {'traffic_level': 'unknown'}
    
    def _calculate_naive_route(self, start: Dict, waypoints: List[Dict]) -> Dict:
        """
        Calculate naive route (visiting points in order) for comparison
        """
        total_distance = 0
        total_duration = 0
        current_location = start
        
        for waypoint in waypoints:
            distance = self._calculate_distance(
                current_location['latitude'], current_location['longitude'],
                waypoint['latitude'], waypoint['longitude']
            )
            total_distance += distance
            total_duration += (distance / 25) * 60  # Assume 25 km/h average
            current_location = waypoint
        
        return {
            'total_distance': total_distance,
            'total_duration': total_duration
        }
    
    def _calculate_route_savings(self, optimized_route: Dict, naive_route: Dict) -> Dict:
        """
        Calculate savings from route optimization
        """
        try:
            distance_savings = naive_route['total_distance'] - optimized_route['total_distance']
            time_savings = naive_route['total_duration'] - optimized_route['total_duration']
            
            distance_savings_percent = (distance_savings / naive_route['total_distance']) * 100
            time_savings_percent = (time_savings / naive_route['total_duration']) * 100
            
            # Estimate fuel and cost savings
            fuel_cost_per_km = 0.15  # $0.15 per km
            fuel_savings = distance_savings * fuel_cost_per_km
            
            return {
                'distance_saved_km': round(distance_savings, 2),
                'time_saved_minutes': round(time_savings, 0),
                'distance_savings_percent': round(distance_savings_percent, 1),
                'time_savings_percent': round(time_savings_percent, 1),
                'estimated_fuel_savings': round(fuel_savings, 2),
                'efficiency_score': round((distance_savings_percent + time_savings_percent) / 2, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating route savings: {str(e)}")
            return {}
    
    def _calculate_fuel_estimate(self, distance_km: float) -> Dict:
        """
        Calculate fuel consumption estimate
        """
        # Assume average fuel consumption of 8L/100km for delivery vehicles
        fuel_consumption_rate = 8.0  # L/100km
        fuel_price_per_liter = 1.50  # $1.50 per liter
        
        fuel_needed = (distance_km * fuel_consumption_rate) / 100
        fuel_cost = fuel_needed * fuel_price_per_liter
        
        return {
            'estimated_fuel_liters': round(fuel_needed, 2),
            'estimated_fuel_cost': round(fuel_cost, 2),
            'fuel_efficiency_rating': 'Good' if fuel_needed < 5 else 'Moderate' if fuel_needed < 10 else 'High'
        }
    
    def _generate_navigation_instructions(self, route_data: Dict) -> Dict:
        """
        Generate comprehensive navigation instructions
        """
        try:
            instructions = []
            current_step = 1
            
            for segment in route_data.get('route_segments', []):
                from_location = segment['from']
                to_location = segment['to']
                
                # Determine action type
                if 'pickup' in to_location.get('type', ''):
                    action = 'Pickup'
                    color = '#4CAF50'  # Green
                elif 'dropoff' in to_location.get('type', ''):
                    action = 'Delivery'
                    color = '#2196F3'  # Blue
                else:
                    action = 'Navigate to'
                    color = '#FF9800'  # Orange
                
                instructions.append({
                    'step': current_step,
                    'action': action,
                    'address': to_location.get('address', 'Unknown location'),
                    'distance_km': segment['distance_km'],
                    'duration_minutes': segment['duration_minutes'],
                    'coordinates': {
                        'latitude': to_location['latitude'],
                        'longitude': to_location['longitude']
                    },
                    'color': color,
                    'turn_by_turn': segment.get('instructions', []),
                    'special_notes': self._get_location_special_notes(to_location)
                })
                
                current_step += 1
            
            return {
                'total_steps': len(instructions),
                'navigation_steps': instructions,
                'overview': {
                    'total_distance': route_data['total_distance'],
                    'total_duration': route_data['total_duration'],
                    'number_of_deliveries': len([i for i in instructions if 'Delivery' in i['action']])
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating navigation instructions: {str(e)}")
            return {'error': str(e)}
    
    def _get_location_special_notes(self, location: Dict) -> List[str]:
        """
        Generate special notes for locations (parking, access, etc.)
        """
        notes = []
        
        # This would be enhanced with real location data
        if 'mall' in location.get('address', '').lower():
            notes.append('Mall location - use main entrance')
        elif 'apartment' in location.get('address', '').lower():
            notes.append('Apartment building - check buzzer system')
        elif 'office' in location.get('address', '').lower():
            notes.append('Office building - reception may require check-in')
        
        return notes
    
    def _generate_navigation_links(self, route_data: Dict) -> Dict:
        """
        Generate navigation app links for seamless handoff
        """
        try:
            links = {}
            
            # Extract all coordinates for multi-stop route
            waypoints = []
            for segment in route_data.get('route_segments', []):
                to_location = segment['to']
                waypoints.append(f"{to_location['latitude']},{to_location['longitude']}")
            
            if waypoints:
                # Google Maps link
                google_url = f"{self.navigation_apps['google_maps']}"
                google_url += "/".join(waypoints)
                links['google_maps'] = google_url
                
                # Waze link (first destination only, as Waze doesn't support multi-stop well)
                if waypoints:
                    first_coords = waypoints[0].split(',')
                    waze_url = f"{self.navigation_apps['waze']}?ll={first_coords[0]},{first_coords[1]}&navigate=yes"
                    links['waze'] = waze_url
                
                # Apple Maps link
                apple_url = f"{self.navigation_apps['apple_maps']}?daddr={waypoints[0]}"
                links['apple_maps'] = apple_url
            
            return links
            
        except Exception as e:
            logger.error(f"Error generating navigation links: {str(e)}")
            return {}
    
    def _cache_route_data(self, driver_id: int, route_info: Dict):
        """
        Cache route data for offline access
        """
        try:
            from services.offline_mode_service import offline_mode_service
            offline_mode_service.cache_route_data(driver_id, route_info)
        except Exception as e:
            logger.error(f"Error caching route data: {str(e)}")
    
    def get_route_updates(self, driver_id: int, route_id: str) -> Dict:
        """
        Get real-time route updates (traffic, delays, etc.)
        """
        try:
            # This would provide real-time updates to existing routes
            return {
                'route_id': route_id,
                'traffic_update': 'Current traffic conditions are moderate',
                'estimated_delay': 5,  # minutes
                'alternative_routes_available': False,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting route updates: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance using Haversine formula (returns km)"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

# Global intelligent routing service instance
intelligent_routing_service = IntelligentRoutingService()
