#!/usr/bin/env python3
"""
Customer Tracking Routes - UBER Quality Live Tracking
Handles customer-side delivery tracking and live location updates
"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from services.live_tracking_service import live_tracking_service
from sqlalchemy import text
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create customer tracking namespace
customer_tracking_api = Namespace('customer-tracking', description='Customer Delivery Tracking Operations')

# API Models
location_update_model = customer_tracking_api.model('CustomerLocationUpdate', {
    'latitude': fields.Float(required=True, description='Customer latitude'),
    'longitude': fields.Float(required=True, description='Customer longitude'),
    'accuracy': fields.Float(description='Location accuracy in meters')
})

@customer_tracking_api.route('/update-location')
class UpdateCustomerLocation(Resource):
    @customer_tracking_api.doc(security='Bearer Auth')
    @customer_tracking_api.expect(location_update_model)
    @customer_tracking_api.response(200, 'Location updated successfully')
    @customer_tracking_api.response(400, 'Invalid location data')
    @customer_tracking_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Update customer's current location for delivery tracking"""
        customer_id = int(get_jwt_identity())
        data = request.get_json()
        
        try:
            # Validate location data
            if 'latitude' not in data or 'longitude' not in data:
                return {'error': 'Latitude and longitude required'}, 400
            
            lat = float(data['latitude'])
            lng = float(data['longitude'])
            accuracy = float(data.get('accuracy', 10.0))
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return {'error': 'Invalid coordinates'}, 400
            
            # Update live tracking service
            if live_tracking_service:
                success = live_tracking_service.update_customer_location(
                    customer_id=customer_id,
                    latitude=lat,
                    longitude=lng,
                    accuracy=accuracy
                )
                
                if success:
                    logger.info(f"Updated customer {customer_id} location: {lat}, {lng}")
                else:
                    logger.warning(f"Failed to update customer {customer_id} location in tracking service")
            
            # Update customer location in database
            location_update_sql = """
            UPDATE customers 
            SET current_latitude = :latitude, current_longitude = :longitude, 
                last_location_update = NOW(), updated_at = NOW()
            WHERE id = :customer_id
            """
            db.session.execute(text(location_update_sql), {
                'latitude': lat,
                'longitude': lng,
                'customer_id': customer_id
            })
            db.session.commit()
            
            return {
                'message': 'Customer location updated successfully',
                'latitude': lat,
                'longitude': lng,
                'accuracy': accuracy,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update customer location: {str(e)}")
            return {'error': 'Failed to update location', 'details': str(e)}, 500

@customer_tracking_api.route('/track-delivery/<int:delivery_id>')
class TrackDelivery(Resource):
    @customer_tracking_api.doc(security='Bearer Auth')
    @customer_tracking_api.response(200, 'Success')
    @customer_tracking_api.response(401, 'Unauthorized')
    @customer_tracking_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get live tracking information for a customer's delivery"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Verify delivery belongs to this customer
            delivery_sql = """
            SELECT id, status, driver_id, pickup_address, dropoff_address,
                   item_name, estimated_cost, estimated_duration, tracking_number,
                   pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
                   assigned_time, accepted_time, pickup_time, delivered_time
            FROM deliveries 
            WHERE id = :delivery_id AND customer_id = :customer_id
            """
            delivery_result = db.session.execute(text(delivery_sql), {
                'delivery_id': delivery_id,
                'customer_id': customer_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not authorized'}, 404
            
            # Get live tracking data if available
            tracking_data = None
            if live_tracking_service:
                tracking_data = live_tracking_service.get_live_tracking_data(delivery_id)
            
            # Get driver information if assigned
            driver_info = None
            if delivery_data[2]:  # driver_id
                driver_sql = """
                SELECT id, first_name, last_name, phone_number, vehicle_plate, vehicle_model
                FROM drivers WHERE id = :driver_id
                """
                driver_result = db.session.execute(text(driver_sql), {'driver_id': delivery_data[2]})
                driver_row = driver_result.fetchone()
                
                if driver_row:
                    driver_info = {
                        'id': driver_row[0],
                        'name': f"{driver_row[1]} {driver_row[2]}",
                        'phone': None,  # Phone number removed for privacy
                        'vehicle_plate': driver_row[4],
                        'vehicle_model': driver_row[5]
                    }
            
            # Build comprehensive tracking response
            tracking_response = {
                'delivery_id': delivery_id,
                'tracking_number': delivery_data[8],
                'status': delivery_data[1],
                'pickup_address': delivery_data[3],
                'dropoff_address': delivery_data[4],
                'item_name': delivery_data[5],
                'estimated_cost': float(delivery_data[6]) if delivery_data[6] else 0,
                'estimated_duration': delivery_data[7],
                'pickup_coordinates': {
                    'latitude': float(delivery_data[9]) if delivery_data[9] else None,
                    'longitude': float(delivery_data[10]) if delivery_data[10] else None
                },
                'dropoff_coordinates': {
                    'latitude': float(delivery_data[11]) if delivery_data[11] else None,
                    'longitude': float(delivery_data[12]) if delivery_data[12] else None
                },
                'timestamps': {
                    'assigned': delivery_data[13].isoformat() if delivery_data[13] else None,
                    'accepted': delivery_data[14].isoformat() if delivery_data[14] else None,
                    'pickup': delivery_data[15].isoformat() if delivery_data[15] else None,
                    'delivered': delivery_data[16].isoformat() if delivery_data[16] else None
                },
                'driver': driver_info,
                'live_tracking': tracking_data if tracking_data and 'error' not in tracking_data else None
            }
            
            return tracking_response, 200
            
        except Exception as e:
            logger.error(f"Failed to get delivery tracking: {str(e)}")
            return {'error': 'Failed to retrieve tracking information', 'details': str(e)}, 500

@customer_tracking_api.route('/active-deliveries')
class GetActiveDeliveries(Resource):
    @customer_tracking_api.doc(security='Bearer Auth')
    @customer_tracking_api.response(200, 'Success')
    @customer_tracking_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get all active deliveries for the customer with tracking info"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Get active deliveries
            active_deliveries_sql = """
            SELECT id, status, driver_id, pickup_address, dropoff_address,
                   item_name, estimated_cost, estimated_duration, tracking_number,
                   assigned_time, accepted_time, pickup_time
            FROM deliveries 
            WHERE customer_id = :customer_id 
            AND status IN ('ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT')
            ORDER BY assigned_time DESC
            """
            deliveries_result = db.session.execute(text(active_deliveries_sql), {
                'customer_id': customer_id
            })
            deliveries_data = deliveries_result.fetchall()
            
            active_deliveries = []
            for delivery_row in deliveries_data:
                delivery_id = delivery_row[0]
                
                # Get live tracking data if available
                tracking_data = None
                if live_tracking_service:
                    tracking_data = live_tracking_service.get_live_tracking_data(delivery_id)
                
                # Get driver info
                driver_info = None
                if delivery_row[2]:  # driver_id
                    driver_sql = """
                    SELECT first_name, last_name, phone_number, vehicle_plate
                    FROM drivers WHERE id = :driver_id
                    """
                    driver_result = db.session.execute(text(driver_sql), {'driver_id': delivery_row[2]})
                    driver_data = driver_result.fetchone()
                    
                    if driver_data:
                        driver_info = {
                            'name': f"{driver_data[0]} {driver_data[1]}",
                            'phone': None,  # Phone number removed for privacy
                            'vehicle_plate': driver_data[3]
                        }
                
                delivery_info = {
                    'delivery_id': delivery_id,
                    'tracking_number': delivery_row[7],
                    'status': delivery_row[1],
                    'pickup_address': delivery_row[3],
                    'dropoff_address': delivery_row[4],
                    'item_name': delivery_row[5],
                    'estimated_cost': float(delivery_row[6]) if delivery_row[6] else 0,
                    'estimated_duration': delivery_row[7],
                    'assigned_time': delivery_row[8].isoformat() if delivery_row[8] else None,
                    'accepted_time': delivery_row[9].isoformat() if delivery_row[9] else None,
                    'pickup_time': delivery_row[10].isoformat() if delivery_row[10] else None,
                    'driver': driver_info,
                    'live_tracking': tracking_data if tracking_data and 'error' not in tracking_data else None
                }
                
                active_deliveries.append(delivery_info)
            
            return {
                'active_deliveries': active_deliveries,
                'total_active': len(active_deliveries),
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to get active deliveries: {str(e)}")
            return {'error': 'Failed to retrieve active deliveries', 'details': str(e)}, 500

@customer_tracking_api.route('/delivery-history')
class GetDeliveryHistory(Resource):
    @customer_tracking_api.doc(security='Bearer Auth')
    @customer_tracking_api.response(200, 'Success')
    @customer_tracking_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get delivery history for the customer"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Get query parameters
            limit = request.args.get('limit', 20, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # Get completed deliveries
            history_sql = """
            SELECT id, status, driver_id, pickup_address, dropoff_address,
                   item_name, estimated_cost, actual_cost, estimated_duration,
                   tracking_number, assigned_time, delivered_time, rating
            FROM deliveries 
            WHERE customer_id = :customer_id 
            AND status = 'DELIVERED'
            ORDER BY delivered_time DESC
            LIMIT :limit OFFSET :offset
            """
            history_result = db.session.execute(text(history_sql), {
                'customer_id': customer_id,
                'limit': limit,
                'offset': offset
            })
            history_data = history_result.fetchall()
            
            delivery_history = []
            for history_row in history_data:
                delivery_id = history_row[0]
                
                # Get driver info
                driver_info = None
                if history_row[2]:  # driver_id
                    driver_sql = """
                    SELECT first_name, last_name, phone_number, vehicle_plate
                    FROM drivers WHERE id = :driver_id
                    """
                    driver_result = db.session.execute(text(driver_sql), {'driver_id': history_row[2]})
                    driver_data = driver_result.fetchone()
                    
                    if driver_data:
                        driver_info = {
                            'name': f"{driver_data[0]} {driver_data[1]}",
                            'phone': None,  # Phone number removed for privacy
                            'vehicle_plate': driver_data[3]
                        }
                
                history_info = {
                    'delivery_id': delivery_id,
                    'tracking_number': history_row[9],
                    'status': history_row[1],
                    'pickup_address': history_row[3],
                    'dropoff_address': history_row[4],
                    'item_name': history_row[5],
                    'estimated_cost': float(history_row[6]) if history_row[6] else 0,
                    'actual_cost': float(history_row[7]) if history_row[7] else 0,
                    'estimated_duration': history_row[8],
                    'assigned_time': history_row[10].isoformat() if history_row[10] else None,
                    'delivered_time': history_row[11].isoformat() if history_row[11] else None,
                    'rating': float(history_row[12]) if history_row[12] else None,
                    'driver': driver_info
                }
                
                delivery_history.append(history_info)
            
            return {
                'delivery_history': delivery_history,
                'total_returned': len(delivery_history),
                'limit': limit,
                'offset': offset,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to get delivery history: {str(e)}")
            return {'error': 'Failed to retrieve delivery history', 'details': str(e)}, 500

@customer_tracking_api.route('/start-tracking/<int:delivery_id>')
class StartCustomerTracking(Resource):
    @customer_tracking_api.doc(security='Bearer Auth')
    @customer_tracking_api.response(200, 'Tracking started successfully')
    @customer_tracking_api.response(400, 'Cannot start tracking')
    @customer_tracking_api.response(401, 'Unauthorized')
    @customer_tracking_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Start live tracking for a customer's delivery"""
        customer_id = int(get_jwt_identity())
        
        try:
            if not live_tracking_service:
                return {'error': 'Live tracking service not available'}, 500
            
            # Verify delivery belongs to this customer and has a driver
            delivery_sql = """
            SELECT id, driver_id, status FROM deliveries 
            WHERE id = :delivery_id AND customer_id = :customer_id
            """
            delivery_result = db.session.execute(text(delivery_sql), {
                'delivery_id': delivery_id,
                'customer_id': customer_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not authorized'}, 404
            
            if not delivery_data[1]:  # driver_id
                return {'error': 'Delivery not yet assigned to a driver'}, 400
            
            if delivery_data[2] not in ['ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT']:
                return {'error': 'Delivery is not in a trackable state'}, 400
            
            # Start live tracking session
            session_id = live_tracking_service.start_tracking_session(
                delivery_id=delivery_id,
                driver_id=delivery_data[1],
                customer_id=customer_id
            )
            
            return {
                'message': 'Live tracking started successfully',
                'session_id': session_id,
                'delivery_id': delivery_id,
                'status': 'tracking_active'
            }, 200
            
        except Exception as e:
            logger.error(f"Failed to start customer tracking: {str(e)}")
            return {'error': 'Failed to start live tracking', 'details': str(e)}, 500

