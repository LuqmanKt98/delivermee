import json
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from extensions import db
from models.user import Driver
from models.delivery import Delivery

logger = logging.getLogger(__name__)

class OfflineModeService:
    """
    Service for handling offline mode capabilities during poor network conditions.
    Provides data caching, offline operations, and seamless sync when connectivity returns.
    """
    
    def __init__(self):
        self.cache_dir = "cache"
        self.offline_db_path = os.path.join(self.cache_dir, "offline_cache.db")
        self.ensure_cache_directory()
        self.init_offline_database()
    
    def ensure_cache_directory(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def init_offline_database(self):
        """Initialize SQLite database for offline caching"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Create tables for offline caching
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cached_deliveries (
                    id INTEGER PRIMARY KEY,
                    delivery_id INTEGER,
                    driver_id INTEGER,
                    data TEXT,
                    last_updated TIMESTAMP,
                    sync_required BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    action_type TEXT,
                    action_data TEXT,
                    timestamp TIMESTAMP,
                    synced BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS driver_state (
                    driver_id INTEGER PRIMARY KEY,
                    status TEXT,
                    latitude REAL,
                    longitude REAL,
                    last_update TIMESTAMP,
                    sync_required BOOLEAN DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offline_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER,
                    route_data TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing offline database: {str(e)}")
    
    def cache_driver_data(self, driver_id: int) -> bool:
        """Cache essential driver data for offline access"""
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return False
            
            # Get active and assigned deliveries
            active_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status.in_(['assigned', 'accepted', 'picked_up', 'in_transit'])
            ).all()
            
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Cache driver state
            cursor.execute('''
                INSERT OR REPLACE INTO driver_state 
                (driver_id, status, latitude, longitude, last_update, sync_required)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (
                driver_id,
                driver.status.value,
                driver.current_latitude,
                driver.current_longitude,
                datetime.utcnow()
            ))
            
            # Cache active deliveries
            for delivery in active_deliveries:
                delivery_data = {
                    'id': delivery.id,
                    'status': delivery.status.value,
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'pickup_latitude': delivery.pickup_latitude,
                    'pickup_longitude': delivery.pickup_longitude,
                    'dropoff_latitude': delivery.dropoff_latitude,
                    'dropoff_longitude': delivery.dropoff_longitude,
                    'customer_id': delivery.customer_id,
                    'item_name': delivery.item_name,
                    'estimated_cost': float(delivery.estimated_cost) if delivery.estimated_cost else 0,
                    'tracking_number': delivery.tracking_number,
                    'special_instructions': delivery.special_instructions
                }
                
                cursor.execute('''
                    INSERT OR REPLACE INTO cached_deliveries 
                    (delivery_id, driver_id, data, last_updated, sync_required)
                    VALUES (?, ?, ?, ?, 0)
                ''', (
                    delivery.id,
                    driver_id,
                    json.dumps(delivery_data),
                    datetime.utcnow()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cached data for driver {driver_id}: {len(active_deliveries)} deliveries")
            return True
            
        except Exception as e:
            logger.error(f"Error caching driver data: {str(e)}")
            return False
    
    def get_cached_deliveries(self, driver_id: int) -> List[Dict]:
        """Get cached deliveries for offline access"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data FROM cached_deliveries 
                WHERE driver_id = ?
                ORDER BY last_updated DESC
            ''', (driver_id,))
            
            deliveries = []
            for row in cursor.fetchall():
                delivery_data = json.loads(row[0])
                deliveries.append(delivery_data)
            
            conn.close()
            return deliveries
            
        except Exception as e:
            logger.error(f"Error getting cached deliveries: {str(e)}")
            return []
    
    def record_offline_action(self, driver_id: int, action_type: str, action_data: Dict) -> bool:
        """Record action performed while offline for later sync"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pending_actions 
                (driver_id, action_type, action_data, timestamp, synced)
                VALUES (?, ?, ?, ?, 0)
            ''', (
                driver_id,
                action_type,
                json.dumps(action_data),
                datetime.utcnow()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded offline action: {action_type} for driver {driver_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording offline action: {str(e)}")
            return False
    
    def update_offline_delivery_status(self, driver_id: int, delivery_id: int, new_status: str, 
                                     timestamp: datetime = None) -> bool:
        """Update delivery status while offline"""
        try:
            if not timestamp:
                timestamp = datetime.utcnow()
            
            # Record the status change for sync
            action_data = {
                'delivery_id': delivery_id,
                'new_status': new_status,
                'timestamp': timestamp.isoformat()
            }
            
            success = self.record_offline_action(driver_id, 'update_delivery_status', action_data)
            
            if success:
                # Update cached delivery status
                conn = sqlite3.connect(self.offline_db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT data FROM cached_deliveries 
                    WHERE delivery_id = ? AND driver_id = ?
                ''', (delivery_id, driver_id))
                
                row = cursor.fetchone()
                if row:
                    delivery_data = json.loads(row[0])
                    delivery_data['status'] = new_status
                    delivery_data['last_offline_update'] = timestamp.isoformat()
                    
                    cursor.execute('''
                        UPDATE cached_deliveries 
                        SET data = ?, sync_required = 1, last_updated = ?
                        WHERE delivery_id = ? AND driver_id = ?
                    ''', (
                        json.dumps(delivery_data),
                        timestamp,
                        delivery_id,
                        driver_id
                    ))
                
                conn.commit()
                conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating offline delivery status: {str(e)}")
            return False
    
    def update_offline_location(self, driver_id: int, latitude: float, longitude: float) -> bool:
        """Update driver location while offline"""
        try:
            timestamp = datetime.utcnow()
            
            # Record location update for sync
            action_data = {
                'latitude': latitude,
                'longitude': longitude,
                'timestamp': timestamp.isoformat()
            }
            
            success = self.record_offline_action(driver_id, 'update_location', action_data)
            
            if success:
                # Update cached driver state
                conn = sqlite3.connect(self.offline_db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE driver_state 
                    SET latitude = ?, longitude = ?, last_update = ?, sync_required = 1
                    WHERE driver_id = ?
                ''', (latitude, longitude, timestamp, driver_id))
                
                conn.commit()
                conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating offline location: {str(e)}")
            return False
    
    def cache_route_data(self, driver_id: int, route_data: Dict) -> bool:
        """Cache route and navigation data for offline use"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO offline_routes 
                (driver_id, route_data, created_at)
                VALUES (?, ?, ?)
            ''', (
                driver_id,
                json.dumps(route_data),
                datetime.utcnow()
            ))
            
            # Keep only recent routes (last 10)
            cursor.execute('''
                DELETE FROM offline_routes 
                WHERE driver_id = ? AND id NOT IN (
                    SELECT id FROM offline_routes 
                    WHERE driver_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 10
                )
            ''', (driver_id, driver_id))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching route data: {str(e)}")
            return False
    
    def get_cached_routes(self, driver_id: int) -> List[Dict]:
        """Get cached route data for offline navigation"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT route_data FROM offline_routes 
                WHERE driver_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (driver_id,))
            
            routes = []
            for row in cursor.fetchall():
                route_data = json.loads(row[0])
                routes.append(route_data)
            
            conn.close()
            return routes
            
        except Exception as e:
            logger.error(f"Error getting cached routes: {str(e)}")
            return []
    
    def sync_offline_data(self, driver_id: int) -> Dict:
        """Sync all offline data when connectivity returns"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Get pending actions
            cursor.execute('''
                SELECT id, action_type, action_data, timestamp 
                FROM pending_actions 
                WHERE driver_id = ? AND synced = 0
                ORDER BY timestamp ASC
            ''', (driver_id,))
            
            pending_actions = cursor.fetchall()
            sync_results = {
                'total_actions': len(pending_actions),
                'successful_syncs': 0,
                'failed_syncs': 0,
                'errors': []
            }
            
            for action_id, action_type, action_data_str, timestamp in pending_actions:
                try:
                    action_data = json.loads(action_data_str)
                    success = self._sync_single_action(driver_id, action_type, action_data, timestamp)
                    
                    if success:
                        # Mark as synced
                        cursor.execute('''
                            UPDATE pending_actions 
                            SET synced = 1 
                            WHERE id = ?
                        ''', (action_id,))
                        sync_results['successful_syncs'] += 1
                    else:
                        sync_results['failed_syncs'] += 1
                        sync_results['errors'].append(f"Failed to sync {action_type}")
                        
                except Exception as e:
                    sync_results['failed_syncs'] += 1
                    sync_results['errors'].append(f"Error syncing action {action_id}: {str(e)}")
                    logger.error(f"Error syncing action {action_id}: {str(e)}")
            
            # Reset sync requirements for successfully synced data
            if sync_results['successful_syncs'] > 0:
                cursor.execute('''
                    UPDATE cached_deliveries 
                    SET sync_required = 0 
                    WHERE driver_id = ?
                ''', (driver_id,))
                
                cursor.execute('''
                    UPDATE driver_state 
                    SET sync_required = 0 
                    WHERE driver_id = ?
                ''', (driver_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Sync completed for driver {driver_id}: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Error syncing offline data: {str(e)}")
            return {'error': str(e)}
    
    def _sync_single_action(self, driver_id: int, action_type: str, action_data: Dict, timestamp: str) -> bool:
        """Sync a single offline action"""
        try:
            if action_type == 'update_delivery_status':
                delivery_id = action_data['delivery_id']
                new_status = action_data['new_status']
                action_timestamp = datetime.fromisoformat(action_data['timestamp'])
                
                # Update delivery in main database
                delivery = Delivery.query.get(delivery_id)
                if delivery and delivery.driver_id == driver_id:
                    # Map string status to enum
                    from models.delivery import DeliveryStatus
                    status_mapping = {
                        'accepted': DeliveryStatus.ACCEPTED,
                        'picked_up': DeliveryStatus.PICKED_UP,
                        'in_transit': DeliveryStatus.IN_TRANSIT,
                        'delivered': DeliveryStatus.DELIVERED
                    }
                    
                    if new_status in status_mapping:
                        delivery.status = status_mapping[new_status]
                        
                        # Set appropriate timestamp
                        if new_status == 'accepted':
                            delivery.accepted_time = action_timestamp
                        elif new_status == 'picked_up':
                            delivery.pickup_time = action_timestamp
                        elif new_status == 'delivered':
                            delivery.delivered_time = action_timestamp
                        
                        db.session.commit()
                        return True
                
            elif action_type == 'update_location':
                latitude = action_data['latitude']
                longitude = action_data['longitude']
                action_timestamp = datetime.fromisoformat(action_data['timestamp'])
                
                # Update driver location in main database
                driver = Driver.query.get(driver_id)
                if driver:
                    driver.current_latitude = latitude
                    driver.current_longitude = longitude
                    driver.last_location_update = action_timestamp
                    db.session.commit()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing single action: {str(e)}")
            return False
    
    def get_offline_capability_status(self, driver_id: int) -> Dict:
        """Get status of offline capabilities for driver"""
        try:
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Count cached deliveries
            cursor.execute('''
                SELECT COUNT(*) FROM cached_deliveries 
                WHERE driver_id = ?
            ''', (driver_id,))
            cached_deliveries = cursor.fetchone()[0]
            
            # Count pending actions
            cursor.execute('''
                SELECT COUNT(*) FROM pending_actions 
                WHERE driver_id = ? AND synced = 0
            ''', (driver_id,))
            pending_actions = cursor.fetchone()[0]
            
            # Get last cache update
            cursor.execute('''
                SELECT MAX(last_updated) FROM cached_deliveries 
                WHERE driver_id = ?
            ''', (driver_id,))
            last_cache_update = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'offline_ready': cached_deliveries > 0,
                'cached_deliveries': cached_deliveries,
                'pending_sync_actions': pending_actions,
                'last_cache_update': last_cache_update,
                'cache_age_hours': (
                    (datetime.utcnow() - datetime.fromisoformat(last_cache_update)).total_seconds() / 3600
                    if last_cache_update else None
                ),
                'recommendations': self._get_offline_recommendations(cached_deliveries, pending_actions)
            }
            
        except Exception as e:
            logger.error(f"Error getting offline status: {str(e)}")
            return {'error': str(e)}
    
    def _get_offline_recommendations(self, cached_deliveries: int, pending_actions: int) -> List[str]:
        """Get recommendations for offline mode optimization"""
        recommendations = []
        
        if cached_deliveries == 0:
            recommendations.append("Go online to cache delivery data for offline access")
        elif cached_deliveries < 3:
            recommendations.append("Accept more deliveries to improve offline capabilities")
        
        if pending_actions > 10:
            recommendations.append("Connect to internet to sync pending actions")
        elif pending_actions > 5:
            recommendations.append("Sync recommended - some actions are pending")
        
        if not recommendations:
            recommendations.append("Offline mode fully ready!")
        
        return recommendations
    
    def clear_old_cache(self, days_old: int = 7) -> bool:
        """Clear cache data older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            conn = sqlite3.connect(self.offline_db_path)
            cursor = conn.cursor()
            
            # Clear old cached deliveries
            cursor.execute('''
                DELETE FROM cached_deliveries 
                WHERE last_updated < ?
            ''', (cutoff_date,))
            
            # Clear old synced actions
            cursor.execute('''
                DELETE FROM pending_actions 
                WHERE timestamp < ? AND synced = 1
            ''', (cutoff_date,))
            
            # Clear old routes
            cursor.execute('''
                DELETE FROM offline_routes 
                WHERE created_at < ?
            ''', (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleared cache data older than {days_old} days")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing old cache: {str(e)}")
            return False

# Global offline mode service instance
offline_mode_service = OfflineModeService()
