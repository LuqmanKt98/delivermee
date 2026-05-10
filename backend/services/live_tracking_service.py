#!/usr/bin/env python3
"""
Live Tracking Service - UBER Quality
Handles real-time location tracking for drivers and customers
"""

import asyncio
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from flask_socketio import SocketIO, emit, join_room, leave_room
from extensions import db
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LocationPoint:
    """Represents a location point with metadata"""
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    altitude: Optional[float] = None

@dataclass
class TrackingSession:
    """Represents an active tracking session"""
    session_id: str
    delivery_id: int
    driver_id: int
    customer_id: int
    start_time: datetime
    last_update: datetime
    is_active: bool = True
    location_history: List[LocationPoint] = None

class LiveTrackingService:
    """Main service for live tracking operations"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.active_sessions: Dict[str, TrackingSession] = {}
        self.driver_locations: Dict[int, LocationPoint] = {}
        self.customer_locations: Dict[int, LocationPoint] = {}
        self.location_cache: Dict[str, List[LocationPoint]] = {}
        
    def start_tracking_session(self, delivery_id: int, driver_id: int, customer_id: int) -> str:
        """Start a new tracking session for a delivery"""
        try:
            session_id = f"track_{delivery_id}_{int(time.time())}"
            
            session = TrackingSession(
                session_id=session_id,
                delivery_id=delivery_id,
                driver_id=driver_id,
                customer_id=customer_id,
                start_time=datetime.utcnow(),
                last_update=datetime.utcnow(),
                location_history=[]
            )
            
            self.active_sessions[session_id] = session
            
            # Join WebSocket rooms for real-time updates
            self.socketio.emit('tracking_started', {
                'session_id': session_id,
                'delivery_id': delivery_id,
                'timestamp': session.start_time.isoformat()
            }, room=f"delivery_{delivery_id}")
            
            logger.info(f"Started tracking session {session_id} for delivery {delivery_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start tracking session: {str(e)}")
            raise
    
    def update_driver_location(self, driver_id: int, latitude: float, longitude: float, 
                             accuracy: float = 10.0, speed: Optional[float] = None, 
                             heading: Optional[float] = None) -> bool:
        """Update driver's current location with real-time tracking"""
        try:
            # Create location point
            location = LocationPoint(
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.utcnow(),
                accuracy=accuracy,
                speed=speed,
                heading=heading
            )
            
            # Update in-memory cache
            self.driver_locations[driver_id] = location
            
            # Store in database for persistence
            self._store_location_history(driver_id, 'driver', location)
            
            # Find active tracking sessions for this driver
            active_sessions = self._get_driver_active_sessions(driver_id)
            
            # Emit real-time updates to all relevant clients
            for session in active_sessions:
                self._emit_location_update(session, 'driver', location)
                
                # Update ETA if delivery is in progress
                if session.is_active:
                    self._update_eta(session, location)
            
            logger.info(f"Updated driver {driver_id} location: {latitude}, {longitude}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update driver location: {str(e)}")
            return False
    
    def update_customer_location(self, customer_id: int, latitude: float, longitude: float,
                               accuracy: float = 10.0) -> bool:
        """Update customer's current location"""
        try:
            location = LocationPoint(
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.utcnow(),
                accuracy=accuracy
            )
            
            self.customer_locations[customer_id] = location
            self._store_location_history(customer_id, 'customer', location)
            
            # Find active sessions for this customer
            active_sessions = self._get_customer_active_sessions(customer_id)
            
            for session in active_sessions:
                self._emit_location_update(session, 'customer', location)
            
            logger.info(f"Updated customer {customer_id} location: {latitude}, {longitude}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update customer location: {str(e)}")
            return False
    
    def get_live_tracking_data(self, delivery_id: int) -> Dict:
        """Get comprehensive live tracking data for a delivery"""
        try:
            # Find active session
            session = self._get_session_by_delivery(delivery_id)
            if not session:
                return {'error': 'No active tracking session found'}
            
            # Get current locations
            driver_location = self.driver_locations.get(session.driver_id)
            customer_location = self.customer_locations.get(session.customer_id)
            
            # Calculate ETA and distance
            eta_data = self._calculate_eta_and_distance(session, driver_location, customer_location)
            
            tracking_data = {
                'session_id': session.session_id,
                'delivery_id': delivery_id,
                'driver_location': self._location_to_dict(driver_location) if driver_location else None,
                'customer_location': self._location_to_dict(customer_location) if customer_location else None,
                'eta': eta_data['eta'],
                'distance': eta_data['distance'],
                'status': 'active' if session.is_active else 'completed',
                'last_update': session.last_update.isoformat(),
                'tracking_duration': (datetime.utcnow() - session.start_time).total_seconds()
            }
            
            return tracking_data
            
        except Exception as e:
            logger.error(f"Failed to get live tracking data: {str(e)}")
            return {'error': 'Failed to retrieve tracking data'}
    
    def _store_location_history(self, user_id: int, user_type: str, location: LocationPoint):
        """Store location history in database for analytics"""
        try:
            # Use raw SQL to avoid ORM issues
            insert_sql = """
            INSERT INTO location_history (user_id, user_type, latitude, longitude, 
                                        accuracy, speed, heading, timestamp, created_at)
            VALUES (:user_id, :user_type, :latitude, :longitude, 
                    :accuracy, :speed, :heading, :timestamp, NOW())
            """
            
            db.session.execute(text(insert_sql), {
                'user_id': user_id,
                'user_type': user_type,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'accuracy': location.accuracy,
                'speed': location.speed,
                'heading': location.heading,
                'timestamp': location.timestamp
            })
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store location history: {str(e)}")
            db.session.rollback()
    
    def _emit_location_update(self, session: TrackingSession, user_type: str, location: LocationPoint):
        """Emit real-time location update via WebSocket"""
        try:
            update_data = {
                'session_id': session.session_id,
                'delivery_id': session.delivery_id,
                'user_type': user_type,
                'user_id': session.driver_id if user_type == 'driver' else session.customer_id,
                'location': self._location_to_dict(location),
                'timestamp': location.timestamp.isoformat()
            }
            
            # Emit to delivery-specific room
            self.socketio.emit('location_update', update_data, room=f"delivery_{session.delivery_id}")
            
            # Emit to user-specific room
            user_room = f"{user_type}_{update_data['user_id']}"
            self.socketio.emit('location_update', update_data, room=user_room)
            
        except Exception as e:
            logger.error(f"Failed to emit location update: {str(e)}")
    
    def _calculate_eta_and_distance(self, session: TrackingSession, driver_location: LocationPoint, 
                                   customer_location: LocationPoint) -> Dict:
        """Calculate ETA and distance between driver and customer"""
        try:
            if not driver_location or not customer_location:
                return {'eta': 'Unknown', 'distance': 'Unknown'}
            
            # Calculate distance using Haversine formula
            distance_km = self._calculate_distance(
                driver_location.latitude, driver_location.longitude,
                customer_location.latitude, customer_location.longitude
            )
            
            # Estimate ETA based on distance and average speed
            avg_speed_kmh = 30.0  # Default average speed in city
            if driver_location.speed:
                avg_speed_kmh = max(driver_location.speed * 3.6, 5.0)  # Convert m/s to km/h
            
            eta_minutes = max(int((distance_km / avg_speed_kmh) * 60), 1)
            
            return {
                'eta': f"{eta_minutes} minutes",
                'distance': f"{distance_km:.1f} km"
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate ETA: {str(e)}")
            return {'eta': 'Unknown', 'distance': 'Unknown'}
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        try:
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            a = (math.sin(dlat/2) ** 2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            
            distance = R * c
            return distance
            
        except Exception as e:
            logger.error(f"Failed to calculate distance: {str(e)}")
            return 0.0
    
    def _update_eta(self, session: TrackingSession, driver_location: LocationPoint):
        """Update ETA for active delivery"""
        try:
            # Get delivery details
            delivery_sql = """
            SELECT pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude
            FROM deliveries WHERE id = :delivery_id
            """
            result = db.session.execute(text(delivery_sql), {'delivery_id': session.delivery_id})
            delivery_data = result.fetchone()
            
            if delivery_data:
                pickup_lat, pickup_lon = delivery_data[0], delivery_data[1]
                dropoff_lat, dropoff_lon = delivery_data[2], delivery_data[3]
                
                # Calculate distance to pickup and dropoff
                distance_to_pickup = self._calculate_distance(
                    driver_location.latitude, driver_location.longitude,
                    pickup_lat, pickup_lon
                )
                
                distance_to_dropoff = self._calculate_distance(
                    driver_location.latitude, driver_location.longitude,
                    dropoff_lat, dropoff_lon
                )
                
                # Emit ETA update
                eta_data = {
                    'session_id': session.session_id,
                    'delivery_id': session.delivery_id,
                    'distance_to_pickup': f"{distance_to_pickup:.1f} km",
                    'distance_to_dropoff': f"{distance_to_dropoff:.1f} km",
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self.socketio.emit('eta_update', eta_data, room=f"delivery_{session.delivery_id}")
                
        except Exception as e:
            logger.error(f"Failed to update ETA: {str(e)}")
    
    def _get_driver_active_sessions(self, driver_id: int) -> List[TrackingSession]:
        """Get active tracking sessions for a driver"""
        return [session for session in self.active_sessions.values() 
                if session.driver_id == driver_id and session.is_active]
    
    def _get_customer_active_sessions(self, customer_id: int) -> List[TrackingSession]:
        """Get active tracking sessions for a customer"""
        return [session for session in self.active_sessions.values() 
                if session.customer_id == customer_id and session.is_active]
    
    def _get_session_by_delivery(self, delivery_id: int) -> Optional[TrackingSession]:
        """Get tracking session by delivery ID"""
        for session in self.active_sessions.values():
            if session.delivery_id == delivery_id:
                return session
        return None
    
    def _location_to_dict(self, location: LocationPoint) -> Dict:
        """Convert LocationPoint to dictionary"""
        if not location:
            return None
            
        return {
            'latitude': location.latitude,
            'longitude': location.longitude,
            'accuracy': location.accuracy,
            'speed': location.speed,
            'heading': location.heading,
            'timestamp': location.timestamp.isoformat()
        }
    
    def stop_tracking_session(self, session_id: str):
        """Stop an active tracking session"""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.is_active = False
                session.last_update = datetime.utcnow()
                
                # Emit session ended event
                self.socketio.emit('tracking_ended', {
                    'session_id': session_id,
                    'delivery_id': session.delivery_id,
                    'duration': (session.last_update - session.start_time).total_seconds()
                }, room=f"delivery_{session.delivery_id}")
                
                logger.info(f"Stopped tracking session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to stop tracking session: {str(e)}")
    
    def get_location_history(self, user_id: int, user_type: str, 
                           hours: int = 24) -> List[Dict]:
        """Get location history for analytics"""
        try:
            # Query location history from database
            history_sql = """
            SELECT latitude, longitude, accuracy, speed, heading, timestamp
            FROM location_history 
            WHERE user_id = :user_id AND user_type = :user_type
            AND timestamp >= NOW() - INTERVAL ':hours hours'
            ORDER BY timestamp DESC
            """
            
            result = db.session.execute(text(history_sql), {
                'user_id': user_id,
                'user_type': user_type,
                'hours': hours
            })
            
            history = []
            for row in result.fetchall():
                history.append({
                    'latitude': float(row[0]),
                    'longitude': float(row[1]),
                    'accuracy': float(row[2]),
                    'speed': float(row[3]) if row[3] else None,
                    'heading': float(row[4]) if row[4] else None,
                    'timestamp': row[5].isoformat()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get location history: {str(e)}")
            return []

# Global instance
live_tracking_service = None

def init_live_tracking_service(socketio: SocketIO):
    """Initialize the global live tracking service"""
    global live_tracking_service
    live_tracking_service = LiveTrackingService(socketio)
    return live_tracking_service

