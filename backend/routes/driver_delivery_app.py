from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Namespace, Resource, fields
from extensions import db
from models.user import Customer, Driver, DriverStatus
from models.delivery import Delivery
from models.notification import Notification
from services.notification_service import notification_service
from services.messaging_service import messaging_service
from services.live_tracking_service import live_tracking_service
from datetime import datetime, timedelta
import math

# Create driver delivery app namespace
driver_delivery_api = Namespace('driver-delivery', description='DeliverMee Driver Delivery App Operations')

# API Models
delivery_request_model = driver_delivery_api.model('DeliveryRequest', {
    'delivery_id': fields.Integer(required=True),
    'pickup_address': fields.String(required=True),
    'dropoff_address': fields.String(required=True),
    'estimated_cost': fields.Float(required=True),
    'estimated_duration': fields.Integer(required=True),
    'customer_name': fields.String(required=True),
    'customer_phone': fields.String(required=True),
    'item_name': fields.String(required=True),
    'package_type': fields.String(required=True),
    'special_instructions': fields.String(),
    'requested_time': fields.DateTime(required=True)
})

active_delivery_model = driver_delivery_api.model('ActiveDelivery', {
    'delivery_id': fields.Integer(required=True),
    'status': fields.String(required=True),
    'pickup_address': fields.String(required=True),
    'dropoff_address': fields.String(required=True),
    'customer_name': fields.String(required=True),
    'customer_phone': fields.String(required=True),
    'estimated_cost': fields.Float(required=True),
    'estimated_duration': fields.Integer(required=True),
    'pickup_latitude': fields.Float(required=True),
    'pickup_longitude': fields.Float(required=True),
    'dropoff_latitude': fields.Float(required=True),
    'dropoff_longitude': fields.Float(required=True),
    'item_name': fields.String(required=True),
    'item_description': fields.String(),
    'item_photo_url': fields.String(),
    'package_type': fields.String(required=True),
    'width': fields.Float(),
    'height': fields.Float(),
    'length': fields.Float(),
    'weight': fields.Float(),
    'is_fragile': fields.Boolean(),
    'is_perishable': fields.Boolean(),
    'requires_signature': fields.Boolean(),
    'special_instructions': fields.String(),
    'tracking_number': fields.String(required=True),
    'assigned_time': fields.DateTime(required=True),
    'accepted_time': fields.DateTime(),
    'pickup_time': fields.DateTime(),
    'delivered_time': fields.DateTime()
})

delivery_earnings_model = driver_delivery_api.model('DeliveryEarnings', {
    'today_earnings': fields.Float(required=True),
    'week_earnings': fields.Float(required=True),
    'month_earnings': fields.Float(required=True),
    'total_earnings': fields.Float(required=True),
    'today_deliveries': fields.Integer(required=True),
    'week_deliveries': fields.Integer(required=True),
    'month_deliveries': fields.Integer(required=True),
    'total_deliveries': fields.Integer(required=True),
    'average_rating': fields.Float(required=True)
})

location_update_model = driver_delivery_api.model('LocationUpdate', {
    'latitude': fields.Float(required=True),
    'longitude': fields.Float(required=True),
    'accuracy': fields.Float(),
    'speed': fields.Float(),
    'heading': fields.Float()
})

message_model = driver_delivery_api.model('Message', {
    'content': fields.String(required=True, description='Message content'),
    'subject': fields.String(description='Message subject (optional)'),
    'is_urgent': fields.Boolean(description='Mark message as urgent')
})

notification_response_model = driver_delivery_api.model('NotificationResponse', {
    'action': fields.String(required=True, enum=['accept', 'reject'], description='Accept or reject the delivery')
})

@driver_delivery_api.route('/status')
class DriverDeliveryStatus(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get driver's current delivery status and active delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            return {
                'driver_status': str(driver.status) if driver.status else None,
                'current_location': {
                    'latitude': driver.current_latitude,
                    'longitude': driver.current_longitude,
                    'last_update': driver.last_location_update.isoformat() if driver.last_location_update else None
                },
                'active_delivery': None,  # Simplified for now
                'online': str(driver.status) == 'available',
                'total_deliveries_today': 0,  # Simplified for now
                'pending_notifications': 0,  # Simplified for now
                'unread_messages': 0  # Simplified for now
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get status', 'details': str(e)}, 500

@driver_delivery_api.route('/go-online')
class GoOnline(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Driver is now online')
    @driver_delivery_api.response(400, 'Cannot go online')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Set driver status to available (online)"""
        driver_id = int(get_jwt_identity())
        
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            # Check if driver has valid location
            if not driver.current_latitude or not driver.current_longitude:
                return {'error': 'Location required to go online'}, 400
            
            # Check if driver has active delivery using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            active_delivery_sql = """
            SELECT id FROM deliveries 
            WHERE driver_id = :driver_id 
            AND status IN ('ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT')
            LIMIT 1
            """
            active_delivery_result = db.session.execute(text(active_delivery_sql), {'driver_id': driver_id})
            active_delivery = active_delivery_result.fetchone()
            
            if active_delivery:
                return {'error': 'Cannot go online while on active delivery'}, 400
            
            # Update driver status using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'available', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            db.session.commit()
            
            return {
                'message': 'Driver is now online',
                'status': 'available',
                'location': {
                    'latitude': driver.current_latitude,
                    'longitude': driver.current_longitude
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to go online', 'details': str(e)}, 500

@driver_delivery_api.route('/go-offline')
class GoOffline(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Driver is now offline')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Set driver status to offline"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            driver_check_sql = "SELECT id FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_check_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Update driver status using raw SQL
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'offline', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            db.session.commit()
            
            return {
                'message': 'Driver is now offline',
                'status': 'offline'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to go offline', 'details': str(e)}, 500

@driver_delivery_api.route('/location')
class UpdateLocation(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.expect(location_update_model)
    @driver_delivery_api.response(200, 'Location updated successfully')
    @driver_delivery_api.response(400, 'Invalid location data')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Update driver's current location"""
        driver_id = int(get_jwt_identity())
        data = request.get_json()
        
        try:
            # Check driver using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            driver_check_sql = "SELECT id, status FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_check_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Validate location data
            if 'latitude' not in data or 'longitude' not in data:
                return {'error': 'Latitude and longitude required'}, 400
            
            lat = float(data['latitude'])
            lng = float(data['longitude'])
            accuracy = float(data.get('accuracy', 10.0))  # Default accuracy if not provided
            
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return {'error': 'Invalid coordinates'}, 400
            
            # Update driver location using raw SQL
            location_update_sql = """
            UPDATE drivers 
            SET current_latitude = :latitude, current_longitude = :longitude, 
                last_location_update = NOW(), updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(location_update_sql), {
                'latitude': lat,
                'longitude': lng,
                'driver_id': driver_id
            })
            
            # Note: Removed auto-assignment logic to follow UBER policy
            # Drivers must explicitly accept deliveries, not auto-assigned
            
            # Start live tracking session if driver is online
            if live_tracking_service:
                try:
                    # Check if driver has active delivery
                    active_delivery_sql = """
                    SELECT id, customer_id FROM deliveries 
                    WHERE driver_id = :driver_id 
                    AND status IN ('ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT')
                    LIMIT 1
                    """
                    active_result = db.session.execute(text(active_delivery_sql), {'driver_id': driver_id})
                    active_delivery = active_result.fetchone()
                    
                    if active_delivery:
                        # Start or update tracking session
                        delivery_id = active_delivery[0]
                        customer_id = active_delivery[1]
                        
                        # Update live tracking service
                        live_tracking_service.update_driver_location(
                            driver_id=driver_id,
                            latitude=lat,
                            longitude=lng,
                            accuracy=accuracy,
                            speed=data.get('speed'),
                            heading=data.get('heading')
                        )
                        
                        # logger.info(f"Updated live tracking for driver {driver_id} on delivery {delivery_id}") # Original line commented out
                except Exception as e:
                    # logger.error(f"Live tracking update failed: {str(e)}") # Original line commented out
                    pass # Original line commented out
            
            db.session.commit()
            
            return {
                'message': 'Location updated successfully',
                'latitude': lat,
                'longitude': lng,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to update location', 'details': str(e)}, 500

@driver_delivery_api.route('/delivery/<int:delivery_id>/pickup')
class PickupDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery picked up successfully')
    @driver_delivery_api.response(400, 'Cannot pickup delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as picked up"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check if delivery exists and belongs to driver
            from sqlalchemy import text
            delivery_check_sql = """
            SELECT id, status, driver_id FROM deliveries 
            WHERE id = :delivery_id AND driver_id = :driver_id
            """
            delivery_result = db.session.execute(text(delivery_check_sql), {
                'delivery_id': delivery_id,
                'driver_id': driver_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not assigned to you'}, 404
            
            if delivery_data[1] != 'ACCEPTED':
                return {'error': 'Delivery must be accepted before pickup'}, 400
            
            # Update delivery status to picked up
            update_sql = """
            UPDATE deliveries 
            SET status = 'PICKED_UP', pickup_time = NOW(), updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            db.session.commit()
            
            return {
                'message': 'Delivery picked up successfully',
                'delivery_id': delivery_id,
                'status': 'PICKED_UP',
                'pickup_time': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to pickup delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/delivery/<int:delivery_id>/start-transit')
class StartTransit(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery started transit successfully')
    @driver_delivery_api.response(400, 'Cannot start transit')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as in transit"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check if delivery exists and belongs to driver
            from sqlalchemy import text
            delivery_check_sql = """
            SELECT id, status, driver_id FROM deliveries 
            WHERE id = :delivery_id AND driver_id = :driver_id
            """
            delivery_result = db.session.execute(text(delivery_check_sql), {
                'delivery_id': delivery_id,
                'driver_id': driver_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not assigned to you'}, 404
            
            if delivery_data[1] != 'PICKED_UP':
                return {'error': 'Delivery must be picked up before starting transit'}, 400
            
            # Update delivery status to in transit
            update_sql = """
            UPDATE deliveries 
            SET status = 'IN_TRANSIT', updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            db.session.commit()
            
            return {
                'message': 'Delivery started transit successfully',
                'delivery_id': delivery_id,
                'status': 'IN_TRANSIT',
                'transit_start_time': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to start transit', 'details': str(e)}, 500

@driver_delivery_api.route('/delivery/<int:delivery_id>/complete')
class CompleteDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery completed successfully')
    @driver_delivery_api.response(400, 'Cannot complete delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as completed"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check if delivery exists and belongs to driver
            from sqlalchemy import text
            delivery_check_sql = """
            SELECT id, status, driver_id FROM deliveries 
            WHERE id = :delivery_id AND driver_id = :driver_id
            """
            delivery_result = db.session.execute(text(delivery_check_sql), {
                'delivery_id': delivery_id,
                'driver_id': driver_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not assigned to you'}, 404
            
            if delivery_data[1] not in ['IN_TRANSIT', 'PICKED_UP']:
                return {'error': 'Delivery must be in transit or picked up before completion'}, 400
            
            # Update delivery status to completed
            update_sql = """
            UPDATE deliveries 
            SET status = 'DELIVERED', delivered_time = NOW(), updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            
            # Update driver status back to available
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'available', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            
            # Increment driver's completed deliveries count
            increment_sql = """
            UPDATE drivers 
            SET completed_deliveries = completed_deliveries + 1, updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(increment_sql), {'driver_id': driver_id})
            
            db.session.commit()
            
            return {
                'message': 'Delivery completed successfully',
                'delivery_id': delivery_id,
                'status': 'DELIVERED',
                'delivered_time': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to complete delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/delivery-requests')
class DeliveryRequests(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get available delivery requests for driver"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver eligibility using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver status and active deliveries
            driver_check_sql = """
            SELECT d.id, d.status, d.current_latitude, d.current_longitude,
                   (SELECT COUNT(*) FROM deliveries del 
                    WHERE del.driver_id = d.id 
                    AND del.status IN ('ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT')) as active_deliveries
            FROM drivers d 
            WHERE d.id = :driver_id
            """
            
            driver_result = db.session.execute(text(driver_check_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check if driver is available (not busy/offline)
            if driver_data[1] != 'available':
                return {'error': 'Driver must be online to receive delivery requests'}, 400
            
            # Check if driver has active deliveries (UBER policy: one delivery at a time)
            if driver_data[3] > 0:
                return {'error': 'Driver is busy with active delivery and cannot accept new requests'}, 400
            
            # Get unassigned standard deliveries using raw SQL to avoid enum validation issues
            sql_query = """
            SELECT id, customer_id, pickup_address, dropoff_address, estimated_cost, estimated_duration,
                   pickup_latitude, pickup_longitude, item_name, item_description, package_type,
                   is_fragile, is_perishable, requires_signature, special_instructions, tracking_number,
                   requested_time
            FROM deliveries 
            WHERE status = 'REQUESTED' AND delivery_type = 'standard'
            """
            
            result = db.session.execute(text(sql_query))
            delivery_rows = result.fetchall()
            
            requests_data = []
            for row in delivery_rows:
                customer = Customer.query.get(row[1])  # customer_id is at index 1
                distance = calculate_distance(
                    float(driver_data[2]) if driver_data[2] else 0,  # current_latitude
                    float(driver_data[3]) if driver_data[3] else 0,  # current_longitude
                    float(row[6]) if row[6] else 0,  # pickup_latitude
                    float(row[7]) if row[7] else 0   # pickup_longitude
                )
                
                requests_data.append({
                    'delivery_id': row[0],  # id
                    'pickup_address': row[2],  # pickup_address
                    'dropoff_address': row[3],  # dropoff_address
                    'estimated_cost': float(row[4]) if row[4] else 0,  # estimated_cost
                    'estimated_duration': row[5],  # estimated_duration
                    'distance_from_driver': round(distance, 2),
                    'customer_name': f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
                    'customer_rating': customer.rating if customer and hasattr(customer, 'rating') else 0.0,
                    'item_name': row[8],  # item_name
                    'item_description': row[9],  # item_description
                    'package_type': row[10],  # package_type (raw string)
                    'is_fragile': row[11],  # is_fragile
                    'is_perishable': row[12],  # is_perishable
                    'requires_signature': row[13],  # requires_signature
                    'special_instructions': row[14],  # special_instructions
                    'tracking_number': row[15],  # tracking_number
                    'requested_time': row[16].isoformat() if row[16] else None  # requested_time
                })
            
            # Sort by distance
            requests_data.sort(key=lambda x: x['distance_from_driver'])
            
            return {
                'delivery_requests': requests_data,
                'total_requests': len(requests_data)
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get delivery requests', 'details': str(e)}, 500

@driver_delivery_api.route('/notifications')
class DriverNotifications(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get driver's notifications"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Get query parameters
            limit = request.args.get('limit', 20, type=int)
            offset = request.args.get('offset', 0, type=int)
            unread_only = request.args.get('unread_only', 'false').lower() == 'true'
            
            notifications = notification_service.get_driver_notifications(
                driver_id=driver_id,
                limit=limit,
                offset=offset
            )
            
            if unread_only:
                notifications = [n for n in notifications if n['status'] in ['pending', 'sent']]
            
            return {
                'notifications': notifications,
                'total': len(notifications),
                'unread_count': len([n for n in notifications if n['status'] in ['pending', 'sent']])
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get notifications', 'details': str(e)}, 500

@driver_delivery_api.route('/notifications/<int:notification_id>/respond')
class RespondToNotification(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.expect(notification_response_model)
    @driver_delivery_api.response(200, 'Response processed successfully')
    @driver_delivery_api.response(400, 'Invalid response or notification expired')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Notification not found')
    @jwt_required()
    def post(self, notification_id):
        """Respond to a delivery assignment notification"""
        driver_id = int(get_jwt_identity())
        data = request.get_json()
        
        try:
            if 'action' not in data:
                return {'error': 'Action required (accept or reject)'}, 400
            
            action = data['action'].lower()
            if action not in ['accept', 'reject']:
                return {'error': 'Action must be either "accept" or "reject"'}, 400
            
            # Process the response
            success, message = notification_service.handle_delivery_response(
                notification_id=notification_id,
                driver_id=driver_id,
                response_action=action
            )
            
            if success:
                return {
                    'message': message,
                    'action': action,
                    'notification_id': notification_id
                }, 200
            else:
                return {'error': message}, 400
                
        except Exception as e:
            return {'error': 'Failed to process response', 'details': str(e)}, 500

@driver_delivery_api.route('/accept-delivery/<int:delivery_id>')
class AcceptDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery accepted successfully')
    @driver_delivery_api.response(400, 'Cannot accept delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Accept a delivery request"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver and delivery using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver
            driver_sql = "SELECT id, status FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check delivery
            delivery_sql = "SELECT id, status, driver_id, customer_id FROM deliveries WHERE id = :delivery_id"
            delivery_result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = delivery_result.fetchone()
            if not delivery_data:
                return {'error': 'Delivery not found'}, 404
            
            if delivery_data[1] != 'ASSIGNED' or delivery_data[2] != driver_id:
                return {'error': 'Cannot accept this delivery'}, 400
            
            # Update delivery status using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            update_sql = """
            UPDATE deliveries 
            SET status = 'ACCEPTED', accepted_time = NOW(), updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            
            # Update driver status using raw SQL
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'busy', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            
            # Mark notification as read
            notification = notification_service.get_notification_by_delivery(
                driver_id=driver_id,
                delivery_id=delivery_id,
                notification_type='delivery_assignment'
            )
            
            if notification:
                notification.status = 'read'
                notification.read_at = datetime.utcnow()
            
            # Send system message to customer - temporarily commented out for debugging
            # messaging_service.send_system_message(
            #     delivery_id=delivery_id,
            #     recipient_id=delivery_data[3],  # customer_id from raw SQL result
            #     content=f"Your delivery has been accepted by the driver. Estimated arrival: {delivery_data[7]} minutes.",
            #     subject="Delivery Accepted"
            # )
            
            db.session.commit()
            
            # Get customer info
            customer = Customer.query.get(delivery_data[3])  # customer_id from raw SQL result
            customer_info = {
                'name': f"{customer.first_name} {customer.last_name}",
                'phone': None,  # Phone number removed for privacy
                'rating': customer.rating if hasattr(customer, 'rating') else 0.0
            }
            
            # Get updated delivery data using raw SQL to avoid enum validation issues
            delivery_sql = """
            SELECT id, status, pickup_address, dropoff_address, item_name, package_type,
                   estimated_cost, estimated_duration, pickup_latitude, pickup_longitude,
                   dropoff_latitude, dropoff_longitude, is_fragile, is_perishable,
                   requires_signature, special_instructions, tracking_number,
                   assigned_time, accepted_time
            FROM deliveries 
            WHERE id = :delivery_id
            """
            result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = result.fetchone()
            
            return {
                'message': 'Delivery accepted successfully',
                'delivery': {
                    'delivery_id': delivery_data[0],
                    'status': delivery_data[1],
                    'pickup_address': delivery_data[2],
                    'dropoff_address': delivery_data[3],
                    'customer': customer_info,
                    'item_name': delivery_data[4],
                    'package_type': delivery_data[5],
                    'estimated_cost': float(delivery_data[6]) if delivery_data[6] else 0,
                    'estimated_duration': delivery_data[7],
                    'pickup_latitude': float(delivery_data[8]) if delivery_data[8] else None,
                    'pickup_longitude': float(delivery_data[9]) if delivery_data[9] else None,
                    'dropoff_latitude': float(delivery_data[10]) if delivery_data[10] else None,
                    'dropoff_longitude': float(delivery_data[11]) if delivery_data[11] else None,
                    'is_fragile': delivery_data[12],
                    'is_perishable': delivery_data[13],
                    'requires_signature': delivery_data[14],
                    'special_instructions': delivery_data[15],
                    'tracking_number': delivery_data[16],
                    'assigned_time': delivery_data[17].isoformat() if delivery_data[17] else None,
                    'accepted_time': delivery_data[18].isoformat() if delivery_data[18] else None
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to accept delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/reject-delivery/<int:delivery_id>')
class RejectDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery rejected successfully')
    @driver_delivery_api.response(400, 'Cannot reject delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Reject a delivery request"""
        driver_id = int(get_jwt_identity())
        
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            if delivery.status != DeliveryStatus.ASSIGNED or delivery.driver_id != driver_id:
                return {'error': 'Cannot reject this delivery'}, 400
            
            # Update delivery status back to requested
            delivery.status = DeliveryStatus.REQUESTED.value
            delivery.driver_id = None
            delivery.assigned_time = None
            
            # Mark notification as read
            notification = notification_service.get_notification_by_delivery(
                driver_id=driver_id,
                delivery_id=delivery_id,
                notification_type='delivery_assignment'
            )
            
            if notification:
                notification.status = 'read'
                notification.read_at = datetime.utcnow()
            
            # Send system message to customer
            messaging_service.send_system_message(
                delivery_id=delivery_id,
                recipient_id=delivery.customer_id,
                recipient_type='customer',
                content="Your delivery request has been rejected by the assigned driver. We are finding another driver for you.",
                subject="Delivery Rejected"
            )
            
            db.session.commit()
            
            return {
                'message': 'Delivery rejected successfully',
                'delivery_id': delivery_id,
                'status': 'rejected'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to reject delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/pickup-delivery/<int:delivery_id>')
class PickupDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery picked up successfully')
    @driver_delivery_api.response(400, 'Cannot pickup delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as picked up"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver and delivery using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver
            driver_sql = "SELECT id FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check delivery
            delivery_sql = "SELECT id, status, driver_id, customer_id FROM deliveries WHERE id = :delivery_id"
            delivery_result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = delivery_result.fetchone()
            if not delivery_data:
                return {'error': 'Delivery not found'}, 404
            
            if delivery_data[1] not in ['ASSIGNED', 'ACCEPTED'] or delivery_data[2] != driver_id:
                return {'error': 'Cannot pickup this delivery'}, 400
            
            # Update delivery status using raw SQL
            update_sql = """
            UPDATE deliveries 
            SET status = 'PICKED_UP', pickup_time = NOW(), updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            
            # Send system message to customer - temporarily commented out for debugging
            # messaging_service.send_system_message(
            #     delivery_id=delivery_id,
            #     recipient_id=delivery_data[3],  # customer_id from raw SQL result
            #     recipient_type='customer',
            #     content="Your delivery has been picked up and is on its way to you.",
            #     subject="Delivery Picked Up"
            # )
            
            db.session.commit()
            
            return {
                'message': 'Delivery picked up successfully',
                'delivery': {
                    'delivery_id': delivery_data[0],
                    'status': 'PICKED_UP',
                    'pickup_time': datetime.utcnow().isoformat()
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to pickup delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/start-transit/<int:delivery_id>')
class StartTransit(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery in transit')
    @driver_delivery_api.response(400, 'Cannot start transit')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as in transit"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver and delivery using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver
            driver_sql = "SELECT id FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check delivery
            delivery_sql = "SELECT id, status, driver_id FROM deliveries WHERE id = :delivery_id"
            delivery_result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = delivery_result.fetchone()
            if not delivery_data:
                return {'error': 'Delivery not found'}, 404
            
            if delivery_data[1] != 'PICKED_UP' or delivery_data[2] != driver_id:
                return {'error': 'Cannot start transit for this delivery'}, 400
            
            # Update delivery status using raw SQL to avoid enum validation issues
            update_sql = """
            UPDATE deliveries 
            SET status = 'IN_TRANSIT', updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            
            # Send system message to customer - temporarily commented out for debugging
            # messaging_service.send_system_message(
            #     delivery_id=delivery_id,
            #     recipient_id=delivery.customer_id,
            #     recipient_type='customer',
            #     content="Your delivery is now in transit and heading to your location.",
            #     subject="Delivery In Transit"
            # )
            
            db.session.commit()
            
            return {
                'message': 'Delivery in transit',
                'delivery': {
                    'delivery_id': delivery_data[0],  # id from raw SQL result
                    'status': 'IN_TRANSIT'
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to start transit', 'details': str(e)}, 500

@driver_delivery_api.route('/complete-delivery/<int:delivery_id>')
class CompleteDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery completed successfully')
    @driver_delivery_api.response(400, 'Cannot complete delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Complete a delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver and delivery using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver
            driver_sql = "SELECT id FROM drivers WHERE id = :driver_id"
            driver_result = db.session.execute(text(driver_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check delivery
            delivery_sql = "SELECT id, status, driver_id, customer_id, estimated_cost, accepted_time FROM deliveries WHERE id = :delivery_id"
            delivery_result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = delivery_result.fetchone()
            if not delivery_data:
                return {'error': 'Delivery not found'}, 404
            
            if delivery_data[1] not in ['PICKED_UP', 'IN_TRANSIT'] or delivery_data[2] != driver_id:
                return {'error': 'Cannot complete this delivery'}, 400
            
            # Update delivery status using raw SQL to avoid enum validation issues
            update_sql = """
            UPDATE deliveries 
            SET status = 'DELIVERED', updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(update_sql), {'delivery_id': delivery_id})
            
            # Update driver status back to available using raw SQL
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'available', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            
            db.session.commit()
            
            return {
                'message': 'Delivery completed successfully',
                'delivery': {
                    'delivery_id': delivery_data[0],  # id from raw SQL result
                    'status': 'DELIVERED'
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to complete delivery', 'details': str(e)}, 500

@driver_delivery_api.route('/earnings')
class DriverDeliveryEarnings(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success', delivery_earnings_model)
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get driver's delivery earnings"""
        driver_id = int(get_jwt_identity())
        
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            # Calculate earnings for different time periods
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Today's earnings
            today_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status == DeliveryStatus.DELIVERED,
                Delivery.delivered_time >= today
            ).all()
            today_earnings = sum(d.actual_cost for d in today_deliveries if d.actual_cost)
            
            # Week's earnings
            week_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status == DeliveryStatus.DELIVERED,
                Delivery.delivered_time >= week_ago
            ).all()
            week_earnings = sum(d.actual_cost for d in week_deliveries if d.actual_cost)
            
            # Month's earnings
            month_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status == DeliveryStatus.DELIVERED,
                Delivery.delivered_time >= month_ago
            ).all()
            month_earnings = sum(d.actual_cost for d in month_deliveries if d.actual_cost)
            
            # Total earnings
            total_deliveries = Delivery.query.filter(
                Delivery.driver_id == driver_id,
                Delivery.status == DeliveryStatus.DELIVERED
            ).all()
            total_earnings = sum(d.actual_cost for d in total_deliveries if d.actual_cost)
            
            # Calculate average rating
            rated_deliveries = [d for d in total_deliveries if d.customer_rating]
            average_rating = sum(d.customer_rating for d in rated_deliveries) / len(rated_deliveries) if rated_deliveries else 0.0
            
            return {
                'today_earnings': round(today_earnings, 2),
                'week_earnings': round(week_earnings, 2),
                'month_earnings': round(month_earnings, 2),
                'total_earnings': round(total_earnings, 2),
                'today_deliveries': len(today_deliveries),
                'week_deliveries': len(week_deliveries),
                'month_deliveries': len(month_deliveries),
                'total_deliveries': len(total_deliveries),
                'average_rating': round(average_rating, 2)
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get earnings', 'details': str(e)}, 500

@driver_delivery_api.route('/delivery-history')
class DeliveryHistory(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get driver's delivery history"""
        driver_id = int(get_jwt_identity())
        
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            # Get completed deliveries using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            delivery_sql = """
            SELECT id, pickup_address, dropoff_address, status, actual_cost, actual_duration,
                   customer_id, item_name, package_type, tracking_number, delivered_time,
                   customer_rating, customer_feedback
            FROM deliveries 
            WHERE driver_id = :driver_id AND status = 'DELIVERED'
            ORDER BY delivered_time DESC 
            LIMIT 50
            """
            result = db.session.execute(text(delivery_sql), {'driver_id': driver_id})
            delivery_rows = result.fetchall()
            
            delivery_history = []
            for row in delivery_rows:
                customer = Customer.query.get(row[6])  # customer_id is at index 6
                delivery_history.append({
                    'delivery_id': row[0],  # id
                    'pickup_address': row[1],  # pickup_address
                    'dropoff_address': row[2],  # dropoff_address
                    'status': row[3],  # status (raw string)
                    'earnings': float(row[4]) if row[4] else 0,  # actual_cost
                    'duration': row[5],  # actual_duration
                    'distance': 0,  # Would be calculated from coordinates
                    'customer_name': f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
                    'item_name': row[7],  # item_name
                    'package_type': row[8],  # package_type (raw string)
                    'tracking_number': row[9],  # tracking_number
                    'delivered_time': row[10].isoformat() if row[10] else None,  # delivered_time
                    'customer_rating': float(row[11]) if row[11] else None,  # customer_rating
                    'customer_feedback': row[12]  # customer_feedback
                })
            
            return {
                'deliveries': delivery_history,
                'total_deliveries': len(delivery_history),
                'total_earnings': sum(d['earnings'] for d in delivery_history if d['earnings'])
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get delivery history', 'details': str(e)}, 500

# Messaging endpoints
@driver_delivery_api.route('/deliveries/<int:delivery_id>/messages')
class DeliveryMessages(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get conversation messages for a delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            success, result = messaging_service.get_delivery_conversation(
                delivery_id=delivery_id,
                user_id=driver_id,
                user_type='driver',
                limit=limit,
                offset=offset
            )
            
            if not success:
                return {'error': result}, 400
            
            return result, 200
            
        except Exception as e:
            return {'error': 'Failed to get messages', 'details': str(e)}, 500

    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.expect(message_model)
    @driver_delivery_api.response(201, 'Message sent successfully')
    @driver_delivery_api.response(400, 'Invalid message data')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Send a message to customer for a delivery"""
        driver_id = int(get_jwt_identity())
        data = request.get_json()
        
        try:
            if 'content' not in data:
                return {'error': 'Message content required'}, 400
            
            # Get delivery to find customer
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            if delivery.driver_id != driver_id:
                return {'error': 'Driver not assigned to this delivery'}, 400
            
            # Send message
            success, message = messaging_service.send_driver_message(
                delivery_id=delivery_id,
                driver_id=driver_id,
                customer_id=delivery.customer_id,
                content=data['content'],
                subject=data.get('subject'),
                is_urgent=data.get('is_urgent', False)
            )
            
            if success:
                return {
                    'message': 'Message sent successfully',
                    'delivery_id': delivery_id,
                    'content': data['content']
                }, 201
            else:
                return {'error': message}, 400
                
        except Exception as e:
            return {'error': 'Failed to send message', 'details': str(e)}, 500

@driver_delivery_api.route('/messages/unread-count')
class UnreadMessageCount(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get count of unread messages"""
        driver_id = int(get_jwt_identity())
        
        try:
            unread_count = messaging_service.get_unread_message_count(driver_id, 'driver')
            
            return {
                'unread_count': unread_count,
                'driver_id': driver_id
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get unread count', 'details': str(e)}, 500

@driver_delivery_api.route('/deliveries/<int:delivery_id>/messages/mark-read')
class MarkMessagesAsRead(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Messages marked as read')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark all messages in a delivery as read"""
        driver_id = int(get_jwt_identity())
        
        try:
            success, message = messaging_service.mark_all_messages_as_read(
                delivery_id=delivery_id,
                user_id=driver_id
            )
            
            if not success:
                return {'error': message}, 400
            
            return {
                'message': message,
                'delivery_id': delivery_id
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to mark messages as read', 'details': str(e)}, 500

@driver_delivery_api.route('/start-tracking/<int:delivery_id>')
class StartLiveTracking(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Live tracking started successfully')
    @driver_delivery_api.response(400, 'Cannot start tracking')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Start live tracking for a delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            if not live_tracking_service:
                return {'error': 'Live tracking service not available'}, 500
            
            # Check if delivery exists and is assigned to this driver
            from sqlalchemy import text
            delivery_sql = """
            SELECT id, customer_id, status FROM deliveries 
            WHERE id = :delivery_id AND driver_id = :driver_id
            """
            delivery_result = db.session.execute(text(delivery_sql), {
                'delivery_id': delivery_id,
                'driver_id': driver_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not assigned to you'}, 404
            
            if delivery_data[2] not in ['ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT']:
                return {'error': 'Delivery is not in a trackable state'}, 400
            
            # Start live tracking session
            session_id = live_tracking_service.start_tracking_session(
                delivery_id=delivery_id,
                driver_id=driver_id,
                customer_id=delivery_data[1]
            )
            
            return {
                'message': 'Live tracking started successfully',
                'session_id': session_id,
                'delivery_id': delivery_id,
                'status': 'tracking_active'
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to start live tracking', 'details': str(e)}, 500

@driver_delivery_api.route('/stop-tracking/<int:delivery_id>')
class StopLiveTracking(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Live tracking stopped successfully')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Stop live tracking for a delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            if not live_tracking_service:
                return {'error': 'Live tracking service not available'}, 500
            
            # Find active tracking session
            session = live_tracking_service._get_session_by_delivery(delivery_id)
            if not session:
                return {'error': 'No active tracking session found'}, 404
            
            if session.driver_id != driver_id:
                return {'error': 'Not authorized to stop tracking for this delivery'}, 403
            
            # Stop tracking session
            live_tracking_service.stop_tracking_session(session.session_id)
            
            return {
                'message': 'Live tracking stopped successfully',
                'delivery_id': delivery_id,
                'status': 'tracking_stopped'
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to stop live tracking', 'details': str(e)}, 500

@driver_delivery_api.route('/tracking-status/<int:delivery_id>')
class GetTrackingStatus(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Success')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get live tracking status for a delivery"""
        driver_id = int(get_jwt_identity())
        
        try:
            if not live_tracking_service:
                return {'error': 'Live tracking service not available'}, 500
            
            # Check if delivery is assigned to this driver
            delivery_sql = """
            SELECT id, customer_id FROM deliveries 
            WHERE id = :delivery_id AND driver_id = :driver_id
            """
            delivery_result = db.session.execute(text(delivery_sql), {
                'delivery_id': delivery_id,
                'driver_id': driver_id
            })
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found or not assigned to you'}, 404
            
            # Get tracking data
            tracking_data = live_tracking_service.get_live_tracking_data(delivery_id)
            
            if 'error' in tracking_data:
                return tracking_data, 404
            
            return tracking_data, 200
            
        except Exception as e:
            return {'error': 'Failed to get tracking status', 'details': str(e)}, 500

@driver_delivery_api.route('/assign-delivery/<int:delivery_id>')
class AssignDelivery(Resource):
    @driver_delivery_api.doc(security='Bearer Auth')
    @driver_delivery_api.response(200, 'Delivery assigned successfully')
    @driver_delivery_api.response(400, 'Cannot assign delivery')
    @driver_delivery_api.response(401, 'Unauthorized')
    @driver_delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Assign a delivery to the current driver"""
        driver_id = int(get_jwt_identity())
        
        try:
            # Check driver status using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            
            # Check driver status and active deliveries using raw SQL to avoid enum validation issues
            driver_check_sql = """
            SELECT d.id, d.status,
                   (SELECT COUNT(*) FROM deliveries del 
                    WHERE del.driver_id = d.id 
                    AND del.status IN ('ASSIGNED', 'ACCEPTED', 'PICKED_UP', 'IN_TRANSIT')) as active_deliveries
            FROM drivers d 
            WHERE d.id = :driver_id
            """
            driver_result = db.session.execute(text(driver_check_sql), {'driver_id': driver_id})
            driver_data = driver_result.fetchone()
            if not driver_data:
                return {'error': 'Driver not found'}, 404
            
            # Check if driver is available (not busy/offline)
            if driver_data[1] != 'available':
                return {'error': 'Driver must be available to accept deliveries'}, 400
            
            # Check if driver has active deliveries (UBER policy: one delivery at a time)
            if driver_data[2] > 0:
                return {'error': 'Driver is busy with active delivery and cannot accept new deliveries'}, 400
            
            # Check delivery availability using raw SQL to avoid enum validation issues
            from sqlalchemy import text
            delivery_sql = """
            SELECT id, status, driver_id, customer_id, pickup_address, dropoff_address,
                   item_name, estimated_cost, estimated_duration, tracking_number
            FROM deliveries 
            WHERE id = :delivery_id
            """
            delivery_result = db.session.execute(text(delivery_sql), {'delivery_id': delivery_id})
            delivery_data = delivery_result.fetchone()
            
            if not delivery_data:
                return {'error': 'Delivery not found'}, 404
            
            if delivery_data[1] != 'REQUESTED':
                return {'error': 'Delivery is not available for assignment'}, 400
            
            if delivery_data[2] is not None:
                return {'error': 'Delivery already assigned to another driver'}, 400
            
            # Assign delivery to driver using raw SQL
            assign_sql = """
            UPDATE deliveries 
            SET driver_id = :driver_id, status = 'ASSIGNED', assigned_time = NOW(), updated_at = NOW()
            WHERE id = :delivery_id
            """
            db.session.execute(text(assign_sql), {
                'driver_id': driver_id,
                'delivery_id': delivery_id
            })
            
            # Update driver status to busy
            driver_update_sql = """
            UPDATE drivers 
            SET status = 'busy', updated_at = NOW()
            WHERE id = :driver_id
            """
            db.session.execute(text(driver_update_sql), {'driver_id': driver_id})
            
            # Commit the assignment
            db.session.commit()
            
            return {
                'message': 'Delivery assigned successfully',
                'delivery_id': delivery_id,
                'status': 'ASSIGNED'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to assign delivery', 'details': str(e)}, 500

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c 