from flask import current_app
from datetime import datetime, timedelta
from extensions import db
from models.user import Customer, Driver, DriverStatus
from models.delivery import Delivery, DeliveryStatus
from services.notification_service import notification_service
from services.maps_service import maps_service
import math
import logging

logger = logging.getLogger(__name__)

class DriverIntelligenceService:
    """
    Intelligent service for seamless driver experience with predictive features,
    smart routing, auto-assignment, and optimized workflows
    """
    
    def __init__(self):
        self.auto_assignment_radius = 15.0  # 15km radius for auto-assignment
        self.batch_delivery_radius = 5.0    # 5km radius for batching deliveries
        self.max_batch_size = 3             # Maximum deliveries in one batch
        self.auto_accept_timeout = 30       # 30 seconds for auto-accept
        
    def enable_seamless_mode(self, driver_id: int, preferences: dict = None) -> dict:
        """
        Enable seamless mode for driver with intelligent auto-assignment
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'success': False, 'error': 'Driver not found'}
            
            # Update driver preferences for seamless mode
            driver.auto_accept_enabled = preferences.get('auto_accept', False) if preferences else False
            driver.max_delivery_radius = preferences.get('max_radius', 15.0) if preferences else 15.0
            driver.preferred_delivery_types = preferences.get('delivery_types', ['standard']) if preferences else ['standard']
            driver.batch_deliveries_enabled = preferences.get('batch_enabled', True) if preferences else True
            
            # Set driver to available and enable intelligent features
            driver.status = DriverStatus.AVAILABLE
            driver.intelligent_mode_enabled = True
            
            db.session.commit()
            
            # Start intelligent monitoring for this driver
            self._start_intelligent_monitoring(driver_id)
            
            return {
                'success': True,
                'message': 'Seamless mode enabled',
                'features_enabled': {
                    'auto_assignment': True,
                    'smart_routing': True,
                    'batch_deliveries': driver.batch_deliveries_enabled,
                    'auto_accept': driver.auto_accept_enabled,
                    'predictive_notifications': True
                }
            }
            
        except Exception as e:
            logger.error(f"Error enabling seamless mode for driver {driver_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def intelligent_delivery_assignment(self, driver_id: int) -> dict:
        """
        Intelligently find and assign optimal deliveries to driver
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver or driver.status != DriverStatus.AVAILABLE:
                return {'assignments': [], 'total': 0}
            
            # Get driver's current location
            if not driver.current_latitude or not driver.current_longitude:
                return {'assignments': [], 'total': 0, 'error': 'Driver location required'}
            
            # Find all available deliveries within radius
            available_deliveries = self._find_available_deliveries(
                driver.current_latitude,
                driver.current_longitude,
                driver.max_delivery_radius or self.auto_assignment_radius
            )
            
            if not available_deliveries:
                return {'assignments': [], 'total': 0}
            
            # Apply intelligent scoring and sorting
            scored_deliveries = self._score_deliveries_for_driver(driver, available_deliveries)
            
            # Create optimal delivery batches if enabled
            if driver.batch_deliveries_enabled:
                delivery_batches = self._create_optimal_batches(driver, scored_deliveries)
            else:
                delivery_batches = [scored_deliveries[:1]]  # Single delivery
            
            assignments = []
            for batch in delivery_batches[:1]:  # Take best batch
                batch_assignment = self._assign_delivery_batch(driver, batch)
                if batch_assignment:
                    assignments.append(batch_assignment)
            
            return {
                'assignments': assignments,
                'total': len(assignments),
                'batch_mode': driver.batch_deliveries_enabled
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent assignment for driver {driver_id}: {str(e)}")
            return {'assignments': [], 'total': 0, 'error': str(e)}
    
    def _find_available_deliveries(self, driver_lat: float, driver_lng: float, radius_km: float) -> list:
        """
        Find available deliveries within specified radius
        """
        try:
            # Get all unassigned standard deliveries
            available_deliveries = Delivery.query.filter(
                Delivery.status == DeliveryStatus.REQUESTED,
                Delivery.delivery_type == 'standard'
            ).all()
            
            # Filter by distance
            nearby_deliveries = []
            for delivery in available_deliveries:
                if delivery.pickup_latitude and delivery.pickup_longitude:
                    distance = self._calculate_distance(
                        driver_lat, driver_lng,
                        delivery.pickup_latitude, delivery.pickup_longitude
                    )
                    if distance <= radius_km:
                        delivery.distance_from_driver = distance
                        nearby_deliveries.append(delivery)
            
            return nearby_deliveries
            
        except Exception as e:
            logger.error(f"Error finding available deliveries: {str(e)}")
            return []
    
    def _score_deliveries_for_driver(self, driver: Driver, deliveries: list) -> list:
        """
        Score deliveries based on multiple factors for optimal assignment
        """
        scored_deliveries = []
        
        for delivery in deliveries:
            score = 0
            
            # Distance factor (closer is better)
            distance_score = max(0, 100 - (delivery.distance_from_driver * 5))
            score += distance_score * 0.3
            
            # Earnings factor
            if delivery.estimated_cost:
                earnings_score = min(100, float(delivery.estimated_cost) * 2)
                score += earnings_score * 0.25
            
            # Customer rating factor
            customer = Customer.query.get(delivery.customer_id)
            if customer and hasattr(customer, 'rating') and customer.rating:
                customer_score = customer.rating * 20  # Scale to 100
                score += customer_score * 0.15
            
            # Delivery urgency factor
            if delivery.requested_time:
                time_diff = (datetime.utcnow() - delivery.requested_time).total_seconds() / 3600
                urgency_score = min(100, time_diff * 10)  # More urgent = higher score
                score += urgency_score * 0.2
            
            # Route optimization factor (how well it fits with driver's direction)
            route_score = self._calculate_route_efficiency(driver, delivery)
            score += route_score * 0.1
            
            delivery.intelligence_score = score
            scored_deliveries.append(delivery)
        
        # Sort by score (highest first)
        return sorted(scored_deliveries, key=lambda d: d.intelligence_score, reverse=True)
    
    def _create_optimal_batches(self, driver: Driver, deliveries: list) -> list:
        """
        Create optimal delivery batches for efficient routing
        """
        if len(deliveries) <= 1:
            return [deliveries]
        
        batches = []
        remaining_deliveries = deliveries.copy()
        
        while remaining_deliveries and len(batches) < 3:  # Max 3 batches
            batch = [remaining_deliveries.pop(0)]  # Start with highest scored delivery
            
            # Find nearby deliveries to add to batch
            for i, delivery in enumerate(remaining_deliveries[:]):
                if len(batch) >= self.max_batch_size:
                    break
                
                # Check if delivery is within batch radius of any delivery in current batch
                is_nearby = False
                for batch_delivery in batch:
                    distance = self._calculate_distance(
                        delivery.pickup_latitude, delivery.pickup_longitude,
                        batch_delivery.pickup_latitude, batch_delivery.pickup_longitude
                    )
                    if distance <= self.batch_delivery_radius:
                        is_nearby = True
                        break
                
                if is_nearby:
                    batch.append(delivery)
                    remaining_deliveries.remove(delivery)
            
            batches.append(batch)
        
        return batches
    
    def _assign_delivery_batch(self, driver: Driver, deliveries: list) -> dict:
        """
        Assign a batch of deliveries to driver
        """
        try:
            assigned_deliveries = []
            total_earnings = 0
            
            for delivery in deliveries:
                # Assign delivery to driver
                delivery.driver_id = driver.id
                delivery.status = DeliveryStatus.ASSIGNED
                delivery.assigned_time = datetime.utcnow()
                
                # Auto-accept if enabled
                if driver.auto_accept_enabled:
                    delivery.status = DeliveryStatus.ACCEPTED
                    delivery.accepted_time = datetime.utcnow()
                    driver.status = DriverStatus.BUSY
                
                total_earnings += float(delivery.estimated_cost or 0)
                assigned_deliveries.append({
                    'delivery_id': delivery.id,
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'estimated_cost': delivery.estimated_cost,
                    'distance_from_driver': delivery.distance_from_driver,
                    'auto_accepted': driver.auto_accept_enabled
                })
            
            db.session.commit()
            
            # Send intelligent notification
            self._send_intelligent_notification(driver, assigned_deliveries, total_earnings)
            
            return {
                'deliveries': assigned_deliveries,
                'total_earnings': total_earnings,
                'batch_size': len(assigned_deliveries),
                'auto_accepted': driver.auto_accept_enabled
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning delivery batch: {str(e)}")
            return None
    
    def _send_intelligent_notification(self, driver: Driver, deliveries: list, total_earnings: float):
        """
        Send intelligent notification with optimized routing info
        """
        try:
            if len(deliveries) == 1:
                title = "Smart Delivery Match!"
                message = f"Perfect delivery nearby: ${total_earnings:.2f} - {deliveries[0]['distance_from_driver']:.1f}km away"
            else:
                title = f"Smart Batch Found! ({len(deliveries)} deliveries)"
                message = f"Optimized route: ${total_earnings:.2f} total - Efficient pickup sequence"
            
            # Add route optimization info if possible
            if len(deliveries) > 1:
                optimal_route = self._calculate_optimal_route(driver, deliveries)
                if optimal_route:
                    message += f" - Est. {optimal_route['total_duration']} mins"
            
            notification_service.create_notification(
                driver_id=driver.id,
                delivery_id=deliveries[0]['delivery_id'],
                notification_type='intelligent_assignment',
                title=title,
                message=message,
                metadata={
                    'batch_size': len(deliveries),
                    'total_earnings': total_earnings,
                    'auto_accepted': driver.auto_accept_enabled,
                    'delivery_ids': [d['delivery_id'] for d in deliveries]
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending intelligent notification: {str(e)}")
    
    def _calculate_route_efficiency(self, driver: Driver, delivery: Delivery) -> float:
        """
        Calculate how efficiently a delivery fits into driver's potential route
        """
        try:
            # Simple efficiency calculation based on distance from driver to pickup to dropoff
            pickup_distance = self._calculate_distance(
                driver.current_latitude, driver.current_longitude,
                delivery.pickup_latitude, delivery.pickup_longitude
            )
            
            delivery_distance = self._calculate_distance(
                delivery.pickup_latitude, delivery.pickup_longitude,
                delivery.dropoff_latitude, delivery.dropoff_longitude
            )
            
            # Efficiency score: shorter pickup distance + reasonable delivery distance = higher score
            efficiency = max(0, 100 - (pickup_distance * 3) - (delivery_distance * 0.5))
            return min(100, efficiency)
            
        except Exception:
            return 50  # Default neutral score
    
    def _calculate_optimal_route(self, driver: Driver, deliveries: list) -> dict:
        """
        Calculate optimal route for multiple deliveries
        """
        try:
            # Simple route optimization - in production, use advanced routing algorithms
            total_distance = 0
            total_duration = 0
            
            current_lat, current_lng = driver.current_latitude, driver.current_longitude
            
            # Sort deliveries by pickup distance for simple optimization
            sorted_deliveries = sorted(deliveries, 
                key=lambda d: self._calculate_distance(current_lat, current_lng, 
                    Delivery.query.get(d['delivery_id']).pickup_latitude,
                    Delivery.query.get(d['delivery_id']).pickup_longitude))
            
            for delivery_info in sorted_deliveries:
                delivery = Delivery.query.get(delivery_info['delivery_id'])
                
                # Distance to pickup
                pickup_distance = self._calculate_distance(
                    current_lat, current_lng,
                    delivery.pickup_latitude, delivery.pickup_longitude
                )
                
                # Distance from pickup to dropoff
                delivery_distance = self._calculate_distance(
                    delivery.pickup_latitude, delivery.pickup_longitude,
                    delivery.dropoff_latitude, delivery.dropoff_longitude
                )
                
                total_distance += pickup_distance + delivery_distance
                current_lat, current_lng = delivery.dropoff_latitude, delivery.dropoff_longitude
            
            # Estimate time (30 km/h average speed + 5 min per delivery)
            total_duration = (total_distance / 30) * 60 + (len(deliveries) * 5)
            
            return {
                'total_distance': round(total_distance, 2),
                'total_duration': round(total_duration, 0),
                'optimized_sequence': [d['delivery_id'] for d in sorted_deliveries]
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimal route: {str(e)}")
            return None
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _start_intelligent_monitoring(self, driver_id: int):
        """
        Start intelligent monitoring for driver (placeholder for background tasks)
        """
        # In production, this would start background tasks for:
        # - Real-time delivery monitoring
        # - Predictive assignment preparation
        # - Route optimization updates
        # - Performance analytics
        logger.info(f"Started intelligent monitoring for driver {driver_id}")
    
    def get_driver_analytics(self, driver_id: int) -> dict:
        """
        Get comprehensive analytics for driver performance and optimization
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}
            
            # Get recent performance data
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Calculate various metrics
            completed_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status == DeliveryStatus.DELIVERED
            ).all()
            
            recent_deliveries = [d for d in completed_deliveries 
                               if d.delivered_time and d.delivered_time.date() >= week_ago]
            
            # Calculate efficiency metrics
            avg_delivery_time = 0
            avg_earnings_per_hour = 0
            customer_satisfaction = 0
            
            if recent_deliveries:
                total_duration = sum(d.actual_duration or 0 for d in recent_deliveries)
                avg_delivery_time = total_duration / len(recent_deliveries)
                
                total_earnings = sum(float(d.actual_cost or 0) for d in recent_deliveries)
                total_hours = total_duration / 60  # Convert to hours
                if total_hours > 0:
                    avg_earnings_per_hour = total_earnings / total_hours
                
                rated_deliveries = [d for d in recent_deliveries if d.customer_rating]
                if rated_deliveries:
                    customer_satisfaction = sum(d.customer_rating for d in rated_deliveries) / len(rated_deliveries)
            
            return {
                'driver_id': driver_id,
                'performance_score': min(100, (customer_satisfaction * 20) + (avg_earnings_per_hour * 2)),
                'total_deliveries': len(completed_deliveries),
                'recent_deliveries': len(recent_deliveries),
                'avg_delivery_time_minutes': round(avg_delivery_time, 1),
                'avg_earnings_per_hour': round(avg_earnings_per_hour, 2),
                'customer_satisfaction': round(customer_satisfaction, 2),
                'recommendations': self._generate_performance_recommendations(
                    avg_delivery_time, avg_earnings_per_hour, customer_satisfaction
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting driver analytics: {str(e)}")
            return {'error': str(e)}
    
    def _generate_performance_recommendations(self, avg_time: float, earnings_per_hour: float, satisfaction: float) -> list:
        """
        Generate personalized recommendations for driver improvement
        """
        recommendations = []
        
        if avg_time > 45:  # Slow delivery times
            recommendations.append({
                'type': 'efficiency',
                'message': 'Consider enabling batch deliveries to optimize your routes',
                'action': 'enable_batch_mode'
            })
        
        if earnings_per_hour < 15:  # Low earnings
            recommendations.append({
                'type': 'earnings',
                'message': 'Work during peak hours (lunch/dinner) to increase earnings',
                'action': 'adjust_schedule'
            })
        
        if satisfaction < 4.0:  # Low customer satisfaction
            recommendations.append({
                'type': 'service',
                'message': 'Focus on communication and careful handling of packages',
                'action': 'improve_service'
            })
        
        if not recommendations:
            recommendations.append({
                'type': 'excellence',
                'message': 'Great performance! Keep up the excellent work!',
                'action': 'maintain_standards'
            })
        
        return recommendations

# Global service instance
driver_intelligence_service = DriverIntelligenceService()
