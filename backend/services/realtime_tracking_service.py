import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from extensions import db
from models.user import Customer, Driver, DriverStatus
from models.delivery import Delivery, DeliveryStatus
from services.enhanced_notification_service import enhanced_notification_service
from services.offline_mode_service import offline_mode_service
import math
import redis
import asyncio

logger = logging.getLogger(__name__)

class RealTimeTrackingService:
    """
    Advanced real-time tracking service for seamless driver experience.
    Provides intelligent location tracking, predictive routing, and real-time updates.
    """
    
    def __init__(self):
        # Initialize Redis for real-time data (if available)
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_available = True
        except:
            self.redis_client = None
            self.redis_available = False
            logger.warning("Redis not available - using database fallback for real-time features")
        
        self.location_update_intervals = {
            'high_frequency': 10,  # 10 seconds for active deliveries
            'normal': 30,          # 30 seconds for available drivers
            'low': 120             # 2 minutes for offline drivers
        }
        
        self.tracking_accuracy_threshold = 20  # meters
        self.movement_threshold = 5           # meters to detect movement
        
    def update_driver_location(self, driver_id: int, location_data: Dict) -> Dict:
        """
        Enhanced location update with intelligent tracking and optimization
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'success': False, 'error': 'Driver not found'}
            
            # Extract and validate location data
            latitude = float(location_data['latitude'])
            longitude = float(location_data['longitude'])
            accuracy = location_data.get('accuracy', 0)
            speed = location_data.get('speed', 0)
            heading = location_data.get('heading', 0)
            timestamp = datetime.utcnow()
            
            # Validate coordinates
            if not self._validate_coordinates(latitude, longitude):
                return {'success': False, 'error': 'Invalid coordinates'}
            
            # Check location accuracy
            if accuracy > self.tracking_accuracy_threshold:
                logger.warning(f"Low accuracy location update for driver {driver_id}: {accuracy}m")
            
            # Calculate movement since last update
            movement_distance = 0
            if driver.current_latitude and driver.current_longitude:
                movement_distance = self._calculate_distance(
                    driver.current_latitude, driver.current_longitude,
                    latitude, longitude
                ) * 1000  # Convert to meters
            
            # Determine if this is a significant location change
            is_significant_update = (
                movement_distance > self.movement_threshold or
                not driver.last_location_update or
                (timestamp - driver.last_location_update).total_seconds() > 300  # 5 minutes
            )
            
            # Update driver location
            previous_location = {
                'latitude': driver.current_latitude,
                'longitude': driver.current_longitude,
                'timestamp': driver.last_location_update
            }
            
            driver.current_latitude = latitude
            driver.current_longitude = longitude
            driver.last_location_update = timestamp
            
            # Store extended location data in Redis for real-time access
            location_record = {
                'driver_id': driver_id,
                'latitude': latitude,
                'longitude': longitude,
                'accuracy': accuracy,
                'speed': speed,
                'heading': heading,
                'timestamp': timestamp.isoformat(),
                'movement_distance': movement_distance
            }
            
            if self.redis_available:
                self.redis_client.setex(
                    f"driver_location:{driver_id}",
                    300,  # 5 minutes TTL
                    json.dumps(location_record)
                )
                
                # Store location history
                self.redis_client.lpush(
                    f"driver_location_history:{driver_id}",
                    json.dumps(location_record)
                )
                self.redis_client.ltrim(f"driver_location_history:{driver_id}", 0, 99)  # Keep last 100 updates
            
            # Cache for offline mode
            offline_mode_service.update_offline_location(driver_id, latitude, longitude)
            
            response_data = {
                'success': True,
                'location_updated': True,
                'movement_detected': movement_distance > self.movement_threshold,
                'movement_distance_meters': round(movement_distance, 2),
                'tracking_quality': self._assess_tracking_quality(accuracy, speed),
                'real_time_features': {}
            }
            
            # Enhanced features for significant updates
            if is_significant_update:
                # Update delivery tracking if driver has active delivery
                active_delivery = self._get_active_delivery(driver_id)
                if active_delivery:
                    delivery_updates = self._update_delivery_tracking(
                        driver, active_delivery, location_record, previous_location
                    )
                    response_data['delivery_tracking'] = delivery_updates
                
                # Intelligent assignment checking for available drivers
                if driver.status == DriverStatus.AVAILABLE and driver.intelligent_mode_enabled:
                    assignment_check = self._check_intelligent_assignments(driver, location_record)
                    response_data['real_time_features']['assignment_opportunities'] = assignment_check
                
                # Route optimization for drivers with multiple deliveries
                route_optimization = self._optimize_current_route(driver, location_record)
                if route_optimization:
                    response_data['real_time_features']['route_optimization'] = route_optimization
                
                # Predictive features
                predictions = self._generate_location_predictions(driver, location_record)
                response_data['real_time_features']['predictions'] = predictions
            
            db.session.commit()
            
            # Send real-time updates to relevant parties
            self._broadcast_location_update(driver, location_record, response_data)
            
            return response_data
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating driver location: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_active_delivery(self, driver_id: int) -> Optional[Delivery]:
        """Get driver's active delivery"""
        return Delivery.query.filter(
            Delivery.driver_id == driver_id,
            Delivery.status.in_([DeliveryStatus.ACCEPTED, DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT])
        ).first()
    
    def _update_delivery_tracking(self, driver: Driver, delivery: Delivery, 
                                location_record: Dict, previous_location: Dict) -> Dict:
        """Update delivery tracking with enhanced features"""
        try:
            tracking_updates = {
                'delivery_id': delivery.id,
                'status': delivery.status.value,
                'tracking_number': delivery.tracking_number,
                'location_updates': []
            }
            
            # Calculate progress based on delivery status
            if delivery.status == DeliveryStatus.ACCEPTED:
                # Calculate ETA to pickup
                pickup_distance = self._calculate_distance(
                    float(location_record['latitude']), float(location_record['longitude']),
                    delivery.pickup_latitude, delivery.pickup_longitude
                )
                eta_minutes = self._estimate_travel_time(pickup_distance, location_record.get('speed', 0))
                
                tracking_updates['eta_to_pickup'] = {
                    'distance_km': round(pickup_distance, 2),
                    'eta_minutes': eta_minutes,
                    'status': 'en_route_to_pickup'
                }
                
                # Check if driver is close to pickup location
                if pickup_distance < 0.1:  # Within 100 meters
                    tracking_updates['pickup_proximity_alert'] = True
                    # Suggest pickup action
                    enhanced_notification_service.send_real_time_update(
                        driver.id, 'pickup_proximity', 
                        {'distance': pickup_distance * 1000, 'delivery_id': delivery.id}
                    )
            
            elif delivery.status in [DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT]:
                # Calculate ETA to dropoff
                dropoff_distance = self._calculate_distance(
                    float(location_record['latitude']), float(location_record['longitude']),
                    delivery.dropoff_latitude, delivery.dropoff_longitude
                )
                eta_minutes = self._estimate_travel_time(dropoff_distance, location_record.get('speed', 0))
                
                tracking_updates['eta_to_dropoff'] = {
                    'distance_km': round(dropoff_distance, 2),
                    'eta_minutes': eta_minutes,
                    'status': 'en_route_to_dropoff'
                }
                
                # Check if driver is close to dropoff location
                if dropoff_distance < 0.1:  # Within 100 meters
                    tracking_updates['dropoff_proximity_alert'] = True
                    # Suggest delivery completion
                    enhanced_notification_service.send_real_time_update(
                        driver.id, 'dropoff_proximity',
                        {'distance': dropoff_distance * 1000, 'delivery_id': delivery.id}
                    )
                
                # Send ETA update to customer
                self._send_customer_eta_update(delivery, eta_minutes, location_record)
            
            # Store tracking update in Redis for real-time access
            if self.redis_available:
                self.redis_client.setex(
                    f"delivery_tracking:{delivery.id}",
                    1800,  # 30 minutes TTL
                    json.dumps(tracking_updates)
                )
            
            return tracking_updates
            
        except Exception as e:
            logger.error(f"Error updating delivery tracking: {str(e)}")
            return {'error': str(e)}
    
    def _check_intelligent_assignments(self, driver: Driver, location_record: Dict) -> Dict:
        """Check for intelligent assignment opportunities based on new location"""
        try:
            from services.driver_intelligence_service import driver_intelligence_service
            
            # Only check assignments if location change is significant
            assignments = driver_intelligence_service.intelligent_delivery_assignment(driver.id)
            
            if assignments['total'] > 0:
                # Calculate potential earnings and efficiency
                total_earnings = sum(
                    assignment.get('total_earnings', 0) 
                    for assignment in assignments['assignments']
                )
                
                return {
                    'opportunities_found': assignments['total'],
                    'potential_earnings': total_earnings,
                    'batch_available': assignments.get('batch_mode', False),
                    'auto_assignment_ready': driver.auto_accept_enabled,
                    'top_opportunity': assignments['assignments'][0] if assignments['assignments'] else None
                }
            
            return {'opportunities_found': 0}
            
        except Exception as e:
            logger.error(f"Error checking intelligent assignments: {str(e)}")
            return {'error': str(e)}
    
    def _optimize_current_route(self, driver: Driver, location_record: Dict) -> Optional[Dict]:
        """Optimize current route based on new location"""
        try:
            # Get all assigned/accepted deliveries for this driver
            pending_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver.id,
                Delivery.status.in_([DeliveryStatus.ASSIGNED, DeliveryStatus.ACCEPTED])
            ).all()
            
            if len(pending_deliveries) <= 1:
                return None
            
            # Calculate optimal sequence
            current_lat = float(location_record['latitude'])
            current_lng = float(location_record['longitude'])
            
            # Simple route optimization (in production, use advanced algorithms)
            delivery_points = []
            for delivery in pending_deliveries:
                delivery_points.append({
                    'delivery_id': delivery.id,
                    'pickup': {
                        'lat': delivery.pickup_latitude,
                        'lng': delivery.pickup_longitude,
                        'address': delivery.pickup_address
                    },
                    'dropoff': {
                        'lat': delivery.dropoff_latitude,
                        'lng': delivery.dropoff_longitude,
                        'address': delivery.dropoff_address
                    }
                })
            
            # Calculate optimized sequence
            optimized_sequence = self._calculate_optimal_delivery_sequence(
                current_lat, current_lng, delivery_points
            )
            
            if optimized_sequence:
                return {
                    'optimized_route_available': True,
                    'total_distance_km': optimized_sequence['total_distance'],
                    'estimated_duration_minutes': optimized_sequence['total_duration'],
                    'delivery_sequence': optimized_sequence['sequence'],
                    'efficiency_improvement': optimized_sequence.get('improvement_percentage', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error optimizing route: {str(e)}")
            return None
    
    def _generate_location_predictions(self, driver: Driver, location_record: Dict) -> Dict:
        """Generate predictive insights based on location patterns"""
        try:
            predictions = {}
            
            # Get location history for pattern analysis
            if self.redis_available:
                history_data = self.redis_client.lrange(f"driver_location_history:{driver.id}", 0, 19)
                
                if len(history_data) >= 5:
                    # Analyze movement patterns
                    speeds = []
                    directions = []
                    
                    for record_str in history_data:
                        record = json.loads(record_str)
                        if record.get('speed'):
                            speeds.append(record['speed'])
                        if record.get('heading'):
                            directions.append(record['heading'])
                    
                    if speeds:
                        avg_speed = sum(speeds) / len(speeds)
                        predictions['movement_pattern'] = {
                            'average_speed_kmh': round(avg_speed, 1),
                            'mobility_status': self._classify_mobility_status(avg_speed),
                            'traffic_condition': self._assess_traffic_condition(speeds)
                        }
                    
                    # Predict next optimal area
                    optimal_area = self._predict_optimal_area(driver, history_data)
                    if optimal_area:
                        predictions['optimal_area_suggestion'] = optimal_area
            
            # Earnings prediction based on current location and time
            earnings_prediction = self._predict_earnings_opportunity(driver, location_record)
            if earnings_prediction:
                predictions['earnings_forecast'] = earnings_prediction
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")
            return {}
    
    def _send_customer_eta_update(self, delivery: Delivery, eta_minutes: int, location_record: Dict):
        """Send ETA update to customer"""
        try:
            customer = Customer.query.get(delivery.customer_id)
            if not customer:
                return
            
            # Store ETA update for customer app
            if self.redis_available:
                eta_update = {
                    'delivery_id': delivery.id,
                    'tracking_number': delivery.tracking_number,
                    'driver_location': {
                        'latitude': location_record['latitude'],
                        'longitude': location_record['longitude']
                    },
                    'eta_minutes': eta_minutes,
                    'status': delivery.status.value,
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                self.redis_client.setex(
                    f"customer_delivery_update:{customer.id}:{delivery.id}",
                    3600,  # 1 hour TTL
                    json.dumps(eta_update)
                )
            
            # Send notification for significant ETA changes (could be implemented)
            # This would typically trigger a push notification to customer app
            
        except Exception as e:
            logger.error(f"Error sending customer ETA update: {str(e)}")
    
    def _broadcast_location_update(self, driver: Driver, location_record: Dict, response_data: Dict):
        """Broadcast location update to relevant systems"""
        try:
            # Store for admin dashboard real-time tracking
            if self.redis_available:
                admin_update = {
                    'driver_id': driver.id,
                    'driver_name': f"{driver.first_name} {driver.last_name}",
                    'status': driver.status.value,
                    'location': {
                        'latitude': location_record['latitude'],
                        'longitude': location_record['longitude']
                    },
                    'last_update': location_record['timestamp'],
                    'active_delivery': response_data.get('delivery_tracking', {}).get('delivery_id'),
                    'performance_metrics': response_data.get('real_time_features', {})
                }
                
                self.redis_client.setex(
                    f"admin_driver_tracking:{driver.id}",
                    600,  # 10 minutes TTL
                    json.dumps(admin_update)
                )
                
                # Add to real-time dashboard feed
                self.redis_client.lpush(
                    "real_time_driver_updates",
                    json.dumps(admin_update)
                )
                self.redis_client.ltrim("real_time_driver_updates", 0, 49)  # Keep last 50 updates
            
        except Exception as e:
            logger.error(f"Error broadcasting location update: {str(e)}")
    
    def get_driver_real_time_status(self, driver_id: int) -> Dict:
        """Get comprehensive real-time status for driver"""
        try:
            if self.redis_available:
                # Get current location from Redis
                location_data = self.redis_client.get(f"driver_location:{driver_id}")
                if location_data:
                    current_location = json.loads(location_data)
                else:
                    # Fallback to database
                    driver = Driver.query.get(driver_id)
                    if not driver:
                        return {'error': 'Driver not found'}
                    
                    current_location = {
                        'latitude': driver.current_latitude,
                        'longitude': driver.current_longitude,
                        'timestamp': driver.last_location_update.isoformat() if driver.last_location_update else None
                    }
                
                # Get delivery tracking if active
                active_delivery = self._get_active_delivery(driver_id)
                delivery_tracking = None
                if active_delivery:
                    tracking_data = self.redis_client.get(f"delivery_tracking:{active_delivery.id}")
                    if tracking_data:
                        delivery_tracking = json.loads(tracking_data)
                
                # Get location history
                history_data = self.redis_client.lrange(f"driver_location_history:{driver_id}", 0, 9)
                location_history = [json.loads(record) for record in history_data]
                
                return {
                    'driver_id': driver_id,
                    'current_location': current_location,
                    'location_history': location_history,
                    'delivery_tracking': delivery_tracking,
                    'real_time_features_active': True,
                    'last_update_age_seconds': (
                        (datetime.utcnow() - datetime.fromisoformat(current_location['timestamp'])).total_seconds()
                        if current_location.get('timestamp') else None
                    )
                }
            else:
                # Database fallback
                driver = Driver.query.get(driver_id)
                if not driver:
                    return {'error': 'Driver not found'}
                
                return {
                    'driver_id': driver_id,
                    'current_location': {
                        'latitude': driver.current_latitude,
                        'longitude': driver.current_longitude,
                        'timestamp': driver.last_location_update.isoformat() if driver.last_location_update else None
                    },
                    'real_time_features_active': False,
                    'message': 'Real-time features limited - Redis not available'
                }
                
        except Exception as e:
            logger.error(f"Error getting real-time status: {str(e)}")
            return {'error': str(e)}
    
    def _validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """Validate GPS coordinates"""
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance using Haversine formula (returns km)"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _estimate_travel_time(self, distance_km: float, current_speed_kmh: float) -> int:
        """Estimate travel time in minutes"""
        if current_speed_kmh > 5:  # Use current speed if moving
            time_hours = distance_km / current_speed_kmh
        else:  # Use average city speed
            time_hours = distance_km / 25  # 25 km/h average
        
        return max(1, int(time_hours * 60))  # At least 1 minute
    
    def _assess_tracking_quality(self, accuracy: float, speed: float) -> str:
        """Assess quality of GPS tracking"""
        if accuracy <= 5:
            return 'excellent'
        elif accuracy <= 15:
            return 'good'
        elif accuracy <= 50:
            return 'fair'
        else:
            return 'poor'
    
    def _classify_mobility_status(self, avg_speed: float) -> str:
        """Classify driver mobility status"""
        if avg_speed < 1:
            return 'stationary'
        elif avg_speed < 5:
            return 'slow_movement'
        elif avg_speed < 25:
            return 'city_driving'
        else:
            return 'highway_driving'
    
    def _assess_traffic_condition(self, speeds: List[float]) -> str:
        """Assess traffic conditions based on speed variations"""
        if not speeds:
            return 'unknown'
        
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = sum((s - avg_speed) ** 2 for s in speeds) / len(speeds)
        
        if speed_variance > 25:  # High variance
            return 'heavy_traffic'
        elif avg_speed < 15:
            return 'moderate_traffic'
        else:
            return 'light_traffic'
    
    def _calculate_optimal_delivery_sequence(self, current_lat: float, current_lng: float, 
                                           delivery_points: List[Dict]) -> Optional[Dict]:
        """Calculate optimal sequence for multiple deliveries"""
        try:
            # Simple nearest-neighbor algorithm (in production, use more sophisticated routing)
            sequence = []
            remaining_points = delivery_points.copy()
            current_location = (current_lat, current_lng)
            total_distance = 0
            
            while remaining_points:
                # Find nearest pickup
                nearest_delivery = None
                min_distance = float('inf')
                
                for delivery in remaining_points:
                    pickup_distance = self._calculate_distance(
                        current_location[0], current_location[1],
                        delivery['pickup']['lat'], delivery['pickup']['lng']
                    )
                    
                    if pickup_distance < min_distance:
                        min_distance = pickup_distance
                        nearest_delivery = delivery
                
                if nearest_delivery:
                    # Add to sequence
                    sequence.append({
                        'delivery_id': nearest_delivery['delivery_id'],
                        'step': 'pickup',
                        'address': nearest_delivery['pickup']['address'],
                        'distance_from_previous': min_distance
                    })
                    
                    # Add dropoff
                    dropoff_distance = self._calculate_distance(
                        nearest_delivery['pickup']['lat'], nearest_delivery['pickup']['lng'],
                        nearest_delivery['dropoff']['lat'], nearest_delivery['dropoff']['lng']
                    )
                    
                    sequence.append({
                        'delivery_id': nearest_delivery['delivery_id'],
                        'step': 'dropoff',
                        'address': nearest_delivery['dropoff']['address'],
                        'distance_from_previous': dropoff_distance
                    })
                    
                    total_distance += min_distance + dropoff_distance
                    current_location = (nearest_delivery['dropoff']['lat'], nearest_delivery['dropoff']['lng'])
                    remaining_points.remove(nearest_delivery)
            
            # Estimate total duration (average 25 km/h + 5 min per stop)
            total_duration = (total_distance / 25) * 60 + (len(sequence) * 5)
            
            return {
                'sequence': sequence,
                'total_distance': round(total_distance, 2),
                'total_duration': round(total_duration, 0),
                'improvement_percentage': 15  # Estimated improvement
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimal sequence: {str(e)}")
            return None
    
    def _predict_optimal_area(self, driver: Driver, history_data: List[str]) -> Optional[Dict]:
        """Predict optimal area for driver to maximize earnings"""
        # This would implement machine learning algorithms to predict optimal areas
        # For now, return a simple suggestion
        return {
            'suggested_area': 'Downtown Business District',
            'confidence': 0.75,
            'expected_earnings_increase': 25,
            'reasoning': 'High delivery demand during current time'
        }
    
    def _predict_earnings_opportunity(self, driver: Driver, location_record: Dict) -> Optional[Dict]:
        """Predict earnings opportunity based on location and time"""
        current_hour = datetime.utcnow().hour
        
        # Simple prediction based on time and historical patterns
        if 11 <= current_hour <= 14 or 17 <= current_hour <= 21:
            return {
                'peak_hours_active': True,
                'predicted_hourly_earnings': 25,
                'confidence': 0.8,
                'recommendation': 'Stay active - peak earning period'
            }
        else:
            return {
                'peak_hours_active': False,
                'predicted_hourly_earnings': 15,
                'confidence': 0.6,
                'recommendation': 'Consider moving to busier area'
            }

# Global real-time tracking service instance
realtime_tracking_service = RealTimeTrackingService()
