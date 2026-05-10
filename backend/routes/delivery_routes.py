from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask_restx import Namespace, Resource, fields
from models.delivery import Delivery, DeliveryStatus, DeliveryPriority
from models.user import Customer, Driver, DriverStatus
from services.notification_service import notification_service
from services.pricing_service import PricingService, VehicleType as PricingVehicleType
from services.maps_service import maps_service
from services.storage_service import get_storage_service
from extensions import db, api
from datetime import datetime
import re
import math
import logging

logger = logging.getLogger(__name__)

def safe_enum_to_string(value):
    """Safely convert enum values to strings for JSON serialization"""
    if hasattr(value, 'value'):
        return value.value
    return str(value) if value is not None else None

def normalize_vehicle_type(value: str):
    """
    Normalize vehicle type strings to the canonical DB format used by deliveries (e.g. PICKUP_TRUCK).
    Accepts common variants like 'pickup truck', 'pickup-truck', 'pickup_truck', 'truck', etc.
    """
    if value is None:
        return None
    try:
        v = str(value).strip()
    except Exception:
        return None
    if not v:
        return None

    key = v.lower().replace(' ', '_').replace('-', '_')
    mapping = {
        'car': 'CAR',
        'sedan': 'CAR',
        'suv': 'SUV',
        'pickup_truck': 'PICKUP_TRUCK',
        'pickup': 'PICKUP_TRUCK',
        'cargo_van': 'CARGO_VAN',
        'cargo': 'CARGO_VAN',
        'van': 'CARGO_VAN',
        'box_truck': 'BOX_TRUCK',
        'box': 'BOX_TRUCK',
        'truck': 'BOX_TRUCK',
    }
    return mapping.get(key, key.upper())

# Create namespace for Swagger
delivery_api = Namespace('deliveries', description='DeliverMee delivery operations')

# Define models for Swagger documentation
delivery_model = delivery_api.model('Delivery', {
    'id': fields.Integer(readonly=True),
    'customer_id': fields.Integer(required=True),
    'driver_id': fields.Integer(),
    'pickup_address': fields.String(required=True),
    'dropoff_address': fields.String(required=True),
    'pickup_latitude': fields.Float(),
    'pickup_longitude': fields.Float(),
    'dropoff_latitude': fields.Float(),
    'dropoff_longitude': fields.Float(),
    'item_name': fields.String(required=True),
    'item_description': fields.String(),
    'item_photo_url': fields.String(),
    'vehicle_type': fields.String(enum=['car', 'suv', 'pickup_truck', 'cargo_van', 'box_truck', 'pickup', 'cargo', 'van', 'box', 'truck', 'sedan'], description='Vehicle type for delivery'),
    'package_size': fields.String(enum=['small', 'medium', 'large', 'extra_large', 'huge']),
    'package_type': fields.String(enum=['small', 'medium', 'large', 'extra_large', 'fragile', 'perishable', 'electronics']),
    'width': fields.Float(description='Width in cm'),
    'height': fields.Float(description='Height in cm'),
    'length': fields.Float(description='Length in cm'),
    'weight': fields.Float(description='Weight in lbs'),
    'item_count': fields.Integer(description='Number of items'),
    'estimated_distance_km': fields.Float(description='Estimated distance in km'),
    'actual_distance_km': fields.Float(description='Actual distance in km'),
    'is_fragile': fields.Boolean(),
    'is_perishable': fields.Boolean(),
    'requires_signature': fields.Boolean(),
    'special_instructions': fields.String(),
    'delivery_type': fields.String(enum=['standard', 'express', 'same_day']),
    'schedule_type': fields.String(enum=['immediate', 'scheduled']),
    'scheduled_date': fields.Date(description='Date for scheduled delivery'),
    'time_slot': fields.String(enum=['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00', '18:00-20:00']),
    'delivery_preference': fields.String(enum=['attended', 'unattended'], description='Delivery preference: attended (someone present) or unattended (leave at destination)'),
    'status': fields.String(enum=['requested', 'assigned', 'accepted', 'picked_up', 'in_transit', 'delivered', 'cancelled', 'failed']),
    'estimated_cost': fields.Float(),
    'actual_cost': fields.Float(),
    'insurance_amount': fields.Float(),
    'tracking_number': fields.String(),
    'estimated_duration': fields.Integer(),
    'actual_duration': fields.Integer(),
    'customer_rating': fields.Float(),
    'customer_feedback': fields.String(),
    'created_at': fields.DateTime(readonly=True),
    'updated_at': fields.DateTime(readonly=True)
})

create_delivery_model = delivery_api.model('CreateDelivery', {
    'pickup_address': fields.String(required=True, description='Pickup address'),
    'dropoff_address': fields.String(required=True, description='Delivery address'),
    'pickup_latitude': fields.Float(description='Pickup latitude (optional - will be geocoded from address)'),
    'pickup_longitude': fields.Float(description='Pickup longitude (optional - will be geocoded from address)'),
    'dropoff_latitude': fields.Float(description='Delivery latitude (optional - will be geocoded from address)'),
    'dropoff_longitude': fields.Float(description='Delivery longitude (optional - will be geocoded from address)'),
    'item_name': fields.String(required=True, description='Item name'),
    'item_description': fields.String(description='Item description'),
    'item_photo_url': fields.String(description='URL to item photo'),
    'vehicle_type': fields.String(enum=['car', 'suv', 'pickup_truck', 'cargo_van', 'box_truck', 'pickup', 'cargo', 'van', 'box', 'truck', 'sedan'], description='Required vehicle type', required=True),
    'package_size': fields.String(enum=['small', 'medium', 'large', 'extra_large', 'huge'], description='Package size (S-10", M-40", L-48", XL-60", Huge-84")'),
    'package_type': fields.String(enum=['small', 'medium', 'large', 'extra_large', 'fragile', 'perishable', 'electronics'], description='Package type'),
    'width': fields.Float(description='Width in cm'),
    'height': fields.Float(description='Height in cm'),
    'length': fields.Float(description='Length in cm'),
    'weight': fields.Float(description='Weight in lbs', required=True),
    'item_count': fields.Integer(description='Number of items', default=1),
    'is_fragile': fields.Boolean(description='Is item fragile'),
    'is_perishable': fields.Boolean(description='Is item perishable'),
    'requires_signature': fields.Boolean(description='Requires signature'),
    'special_instructions': fields.String(description='Special delivery instructions'),
    'delivery_type': fields.String(enum=['standard', 'express', 'same_day'], description='Delivery type'),
    'schedule_type': fields.String(enum=['immediate', 'scheduled'], description='Scheduling type', required=True),
    'scheduled_date': fields.Date(description='Date for scheduled delivery (required if schedule_type is scheduled)'),
    'time_slot': fields.String(enum=['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00', '18:00-20:00'], description='Time slot for scheduled delivery (required if schedule_type is scheduled)'),
    'delivery_preference': fields.String(enum=['attended', 'unattended'], description='Delivery preference: attended (someone will be present) or unattended (leave at destination)', default='attended'),
    'scheduled_time': fields.DateTime(description='[DEPRECATED] Use scheduled_date and time_slot instead')
})

# Item photo upload models
item_photo_upload_model = delivery_api.model('ItemPhotoUpload', {
    'delivery_id': fields.Integer(required=True, description='Delivery ID'),
    'filename': fields.String(required=True, description='Original filename'),
    'content_type': fields.String(required=True, description='MIME type of the file')
})

item_photo_upload_response_model = delivery_api.model('ItemPhotoUploadResponse', {
    'upload_url': fields.String(description='Signed URL for uploading the photo'),
    'object_key': fields.String(description='Object key for the uploaded file'),
    'expires_in': fields.Integer(description='URL expiration time in seconds'),
    'message': fields.String(description='Success message')
})

item_photo_confirm_model = delivery_api.model('ItemPhotoConfirm', {
    'delivery_id': fields.Integer(required=True, description='Delivery ID'),
    'object_key': fields.String(required=True, description='Object key from upload URL response')
})

update_delivery_model = delivery_api.model('UpdateDelivery', {
    'pickup_address': fields.String(description='Pickup address'),
    'dropoff_address': fields.String(description='Delivery address'),
    'pickup_latitude': fields.Float(description='Pickup latitude'),
    'pickup_longitude': fields.Float(description='Pickup longitude'),
    'dropoff_latitude': fields.Float(description='Delivery latitude'),
    'dropoff_longitude': fields.Float(description='Delivery longitude'),
    'item_name': fields.String(description='Item name'),
    'item_description': fields.String(description='Item description'),
    'item_photo_url': fields.String(description='URL to item photo'),
    'width': fields.Float(description='Width in cm'),
    'height': fields.Float(description='Height in cm'),
    'length': fields.Float(description='Length in cm'),
    'weight': fields.Float(description='Weight in kg'),
    'is_fragile': fields.Boolean(description='Is item fragile'),
    'is_perishable': fields.Boolean(description='Is item perishable'),
    'requires_signature': fields.Boolean(description='Requires signature'),
    'special_instructions': fields.String(description='Special delivery instructions'),
    'scheduled_time': fields.DateTime(description='Scheduled delivery time')
})

def validate_address(address):
    """Validate address format"""
    if not address or len(address.strip()) < 10:
        return False
    return True

def validate_dimensions(width, height, length, weight):
    """Validate package dimensions and weight"""
    if width and (width <= 0 or width > 500):  # Max 5m width
        return False
    if height and (height <= 0 or height > 500):  # Max 5m height
        return False
    if length and (length <= 0 or length > 500):  # Max 5m length
        return False
    if weight and (weight <= 0 or weight > 2200):  # Max 2200lbs (1000kg)
        return False
    return True

def validate_package_size_dimensions(package_size, width, height, length):
    """Validate that dimensions match the specified package size"""
    if not package_size or not any([width, height, length]):
        return True  # If no size specified or no dimensions, skip validation
    
    # Convert cm to inches for validation
    dimensions_inches = []
    for dim in [width, height, length]:
        if dim:
            dimensions_inches.append(dim / 2.54)  # Convert cm to inches
    
    if not dimensions_inches:
        return True
    
    max_dimension = max(dimensions_inches)
    
    size_limits = {
        'small': 10,      # S - up to 10"
        'medium': 40,     # M - up to 40"
        'large': 48,      # L - up to 48"
        'extra_large': 60, # XL - up to 60"
        'huge': 84        # Huge - up to 84"
    }
    
    limit = size_limits.get(package_size)
    if limit and max_dimension > limit:
        return False
    
    return True

def determine_package_size_from_dimensions(width, height, length):
    """Auto-determine package size based on dimensions"""
    if not any([width, height, length]):
        return 'medium'  # Default
    
    # Convert cm to inches and find largest dimension
    dimensions_inches = []
    for dim in [width, height, length]:
        if dim:
            dimensions_inches.append(dim / 2.54)
    
    if not dimensions_inches:
        return 'medium'
    
    max_dimension = max(dimensions_inches)
    
    if max_dimension <= 10:
        return 'small'
    elif max_dimension <= 40:
        return 'medium'
    elif max_dimension <= 48:
        return 'large'
    elif max_dimension <= 60:
        return 'extra_large'
    else:
        return 'huge'

def validate_delivery_preference(delivery_preference):
    """Validate delivery preference"""
    if not delivery_preference:
        return True, None  # Optional field, defaults to 'attended'
    
    valid_preferences = ['attended', 'unattended']
    if delivery_preference.lower() not in valid_preferences:
        return False, f"delivery_preference must be one of: {', '.join(valid_preferences)}"
    
    return True, None

def validate_schedule_data(schedule_type, scheduled_date, time_slot):
    """Validate scheduling data"""
    from datetime import date, datetime, timedelta
    
    if schedule_type == 'immediate':
        # For immediate deliveries, scheduled_date and time_slot should not be provided
        if scheduled_date or time_slot:
            return False, "scheduled_date and time_slot should not be provided for immediate deliveries"
        return True, None
    
    elif schedule_type == 'scheduled':
        # For scheduled deliveries, both scheduled_date and time_slot are required
        if not scheduled_date:
            return False, "scheduled_date is required for scheduled deliveries"
        
        if not time_slot:
            return False, "time_slot is required for scheduled deliveries"
        
        # Parse date
        try:
            if isinstance(scheduled_date, str):
                schedule_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            else:
                schedule_date = scheduled_date
        except ValueError:
            return False, "scheduled_date must be in YYYY-MM-DD format"
        
        # Validate date is not in the past
        today = date.today()
        if schedule_date < today:
            return False, "scheduled_date cannot be in the past"
        
        # Validate date is not more than 30 days in the future
        max_future_date = today + timedelta(days=30)
        if schedule_date > max_future_date:
            return False, "scheduled_date cannot be more than 30 days in the future"
        
        # Validate time slot
        valid_time_slots = ['08:00-10:00', '10:00-12:00', '12:00-14:00', '14:00-16:00', '16:00-18:00', '18:00-20:00']
        if time_slot not in valid_time_slots:
            return False, f"time_slot must be one of: {', '.join(valid_time_slots)}"
        
        return True, None
    
    else:
        return False, "schedule_type must be either 'immediate' or 'scheduled'"

def get_available_time_slots(delivery_date):
    """Get available time slots for a given date"""
    # This is a simplified implementation
    # In a real system, you'd check driver availability, existing bookings, etc.
    all_slots = [
        {'slot': '08:00-10:00', 'label': '8:00 AM - 10:00 AM'},
        {'slot': '10:00-12:00', 'label': '10:00 AM - 12:00 PM'},
        {'slot': '12:00-14:00', 'label': '12:00 PM - 2:00 PM'},
        {'slot': '14:00-16:00', 'label': '2:00 PM - 4:00 PM'},
        {'slot': '16:00-18:00', 'label': '4:00 PM - 6:00 PM'},
        {'slot': '18:00-20:00', 'label': '6:00 PM - 8:00 PM'}
    ]
    
    # For now, return all slots as available
    # TODO: Implement actual availability checking
    return all_slots

def calculate_estimated_cost(distance_km, package_type, delivery_type, vehicle_type_str='CAR', is_fragile=False, is_perishable=False, requires_signature=False, special_instructions=None):
    """Calculate estimated delivery cost using new pricing model"""
    try:
        # Convert string to VehicleType enum
        vehicle_type = PricingVehicleType(vehicle_type_str.upper())
        
        # Calculate cost using pricing service
        cost_breakdown = PricingService.calculate_delivery_cost(
            distance_km=distance_km,
            vehicle_type=vehicle_type,
            package_type=package_type,
            delivery_type=delivery_type,
            is_fragile=is_fragile,
            is_perishable=is_perishable,
            requires_signature=requires_signature,
            special_instructions=special_instructions
        )
        
        return float(cost_breakdown['total_cost'])
    except ValueError:
        # Fallback to default pricing if vehicle type is invalid
        vehicle_type = PricingVehicleType.CAR
        cost_breakdown = PricingService.calculate_delivery_cost(
            distance_km=distance_km,
            vehicle_type=vehicle_type,
            package_type=package_type,
            delivery_type=delivery_type,
            is_fragile=is_fragile,
            is_perishable=is_perishable,
            requires_signature=requires_signature,
            special_instructions=special_instructions
        )
        return float(cost_breakdown['total_cost'])

def assign_driver_to_delivery(delivery, vehicle_type=None):
    """Assign the best available driver to a delivery"""
    try:
        # Find available drivers
        available_drivers = Driver.query.filter(
            Driver.status == DriverStatus.AVAILABLE.value,
            Driver.is_active == True
        ).all()
        
        if not available_drivers:
            return None
        
        # Calculate distances and find closest driver
        closest_driver = None
        min_distance = float('inf')
        
        for driver in available_drivers:
            if not driver.current_latitude or not driver.current_longitude:
                continue
            
            # Calculate distance from driver to pickup location
            distance = calculate_distance(
                driver.current_latitude, driver.current_longitude,
                delivery.pickup_latitude, delivery.pickup_longitude
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_driver = driver
        
        if closest_driver and min_distance <= 50:  # Within 50km
            delivery.driver_id = closest_driver.id
            delivery.status = DeliveryStatus.ASSIGNED.value
            delivery.assigned_time = datetime.utcnow()
            
            # Create notification for driver with response tracking
            notification_sent = notification_service.notify_delivery_assignment(
                delivery_id=delivery.id,
                driver_id=closest_driver.id,
                response_deadline_minutes=15
            )
            
            if notification_sent:
                print(f"[SUCCESS] Delivery assignment notification sent to driver {closest_driver.id}")
            else:
                print(f"[WARNING] Failed to send notification to driver {closest_driver.id}")
            
            return closest_driver
        
        return None
        
    except Exception as e:
        print(f"Error assigning driver: {str(e)}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

@delivery_api.route('/create')
class CreateDelivery(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.expect(create_delivery_model)
    @delivery_api.response(201, 'Delivery created successfully', delivery_model)
    @delivery_api.response(400, 'Validation Error')
    @delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Create a new delivery request with Google Maps integration"""
        customer_id = int(get_jwt_identity())
        data = delivery_api.payload
        
        # Validate required fields
        required_fields = ['pickup_address', 'dropoff_address', 'item_name', 'vehicle_type', 'weight', 'schedule_type']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            return {'error': f'Missing required fields: {", ".join(missing_fields)}'}, 400
        
        # Validate addresses
        if not validate_address(data['pickup_address']):
            return {'error': 'Invalid pickup address - must be at least 10 characters'}, 400
        
        if not validate_address(data['dropoff_address']):
            return {'error': 'Invalid dropoff address - must be at least 10 characters'}, 400
        
        # Validate and convert vehicle type - Enhanced to handle various formats
        vehicle_type_input = data['vehicle_type'].lower().replace(' ', '_').replace('-', '_')
        vehicle_type_mapping = {
            'car': 'CAR',
            'suv': 'SUV', 
            'pickup_truck': 'PICKUP_TRUCK',
            'pickup': 'PICKUP_TRUCK',  # Alternative for pickup_truck
            'cargo_van': 'CARGO_VAN',
            'cargo': 'CARGO_VAN',  # Alternative for cargo_van
            'van': 'CARGO_VAN',  # Alternative for cargo_van
            'box_truck': 'BOX_TRUCK',
            'box': 'BOX_TRUCK',  # Alternative for box_truck
            'truck': 'BOX_TRUCK',  # Alternative for box_truck
            'sedan': 'CAR'
        }
        
        vehicle_type_db = vehicle_type_mapping.get(vehicle_type_input)
        if not vehicle_type_db:
            return {'error': f'Invalid vehicle type. Must be one of: {list(vehicle_type_mapping.keys())}. Received: {data["vehicle_type"]}'}, 400
        
        # Validate weight
        weight = data.get('weight')
        if not weight or weight <= 0:
            return {'error': 'Weight must be greater than 0 lbs'}, 400
        
        # Validate item count
        item_count = data.get('item_count', 1)
        if item_count <= 0:
            return {'error': 'Item count must be greater than 0'}, 400
        
        # Validate dimensions if provided
        width = data.get('width')
        height = data.get('height')
        length = data.get('length')
        
        if any([width, height, length]):
            if not validate_dimensions(width, height, length, weight):
                return {'error': 'Invalid package dimensions - check size and weight limits'}, 400
        
        # Validate package size vs dimensions if both provided
        package_size = data.get('package_size')
        if package_size and any([width, height, length]):
            if not validate_package_size_dimensions(package_size, width, height, length):
                return {'error': f'Package dimensions exceed {package_size} size limits'}, 400
        
        # Validate scheduling data
        schedule_type = data.get('schedule_type')
        scheduled_date = data.get('scheduled_date')
        time_slot = data.get('time_slot')
        
        is_valid_schedule, schedule_error = validate_schedule_data(schedule_type, scheduled_date, time_slot)
        if not is_valid_schedule:
            return {'error': schedule_error}, 400
        
        # Validate delivery preference
        delivery_preference = data.get('delivery_preference', 'attended')
        is_valid_preference, preference_error = validate_delivery_preference(delivery_preference)
        if not is_valid_preference:
            return {'error': preference_error}, 400
        
        try:
            # Step 1: Get coordinates for pickup and dropoff locations
            pickup_coords = None
            dropoff_coords = None
            
            # Always geocode addresses for accurate distance calculation
            # (don't trust coordinates from frontend as they might be incorrect)
            pickup_coords = maps_service.geocode_address(data['pickup_address'])
            if not pickup_coords:
                return {'error': 'Could not geocode pickup address'}, 400

            dropoff_coords = maps_service.geocode_address(data['dropoff_address'])
            if not dropoff_coords:
                return {'error': 'Could not geocode dropoff address'}, 400
            
            # Step 2: Calculate distance and duration using Google Maps
            # Check if frontend sent estimated distance directly
            frontend_estimated_distance = data.get('estimated_distance_km')
            if frontend_estimated_distance:
                print(f"[DISTANCE] Frontend sent estimated distance: {frontend_estimated_distance} km")
            
            route_info = maps_service.calculate_distance_and_duration(
                origin_address=data['pickup_address'],
                destination_address=data['dropoff_address'],
                origin_coords=pickup_coords,
                destination_coords=dropoff_coords
            )
            
            estimated_distance_km = route_info['distance_km']
            estimated_duration_minutes = route_info['duration_minutes']
            
            print(f"[MAPS] Google Maps calculated distance: {estimated_distance_km} km")
            print(f"[TIME] Google Maps calculated duration: {estimated_duration_minutes} minutes")
            
            # Step 3: Determine package size if not provided
            if not package_size:
                package_size = determine_package_size_from_dimensions(width, height, length)
            
            # Convert package size to database format (ensure lowercase)
            package_size_db = package_size.lower() if package_size else 'medium'
            
            # Step 4: Auto-calculate package type based on characteristics  
            package_type = data.get('package_type')
            if not package_type:
                if data.get('is_fragile'):
                    package_type = 'FRAGILE'
                elif data.get('is_perishable'):
                    package_type = 'PERISHABLE'
                elif any([width, height, length]) or weight:
                    # Calculate based on dimensions and weight
                    if weight > 33:  # > 33lbs (15kg)
                        package_type = 'EXTRA_LARGE'
                    elif weight > 11:  # > 11lbs (5kg)
                        package_type = 'LARGE'
                    elif weight > 2.2:  # > 2.2lbs (1kg)
                        package_type = 'MEDIUM'
                    else:
                        package_type = 'SMALL'
                else:
                    package_type = 'MEDIUM'  # Default
            
            # Convert package_type to database format (uppercase)
            package_type_mapping = {
                'small': 'SMALL', 'medium': 'MEDIUM', 'large': 'LARGE', 
                'extra_large': 'EXTRA_LARGE', 'fragile': 'FRAGILE', 
                'perishable': 'PERISHABLE', 'electronics': 'ELECTRONICS'
            }
            package_type_db = package_type_mapping.get(package_type.lower(), 'MEDIUM')
            
            # Step 5: Calculate estimated cost using pricing service
            # Convert to pricing service vehicle type
            pricing_mapping = {
                'CAR': 'CAR',
                'SUV': 'SUV',
                'PICKUP_TRUCK': 'PICKUP_TRUCK', 
                'cargo_van': 'CARGO_VAN',
                'BOX_TRUCK': 'BOX_TRUCK',
                'SEDAN': 'CAR'
            }
            pricing_vehicle_type = PricingVehicleType(pricing_mapping.get(vehicle_type_db, 'CAR'))
            
            # Use the integrated pricing service to calculate accurate costs
            try:
                from services.payment_service import payment_service
                
                cost_breakdown = payment_service.calculate_delivery_cost_with_pricing(
                    distance_km=estimated_distance_km,
                    vehicle_type=vehicle_type_db.lower()
                )
                
                estimated_cost = cost_breakdown['total_cost']
                logger.info(f"Delivery cost calculated using pricing service: ${estimated_cost}")
                print(f"[COST] Final estimated cost: ${estimated_cost} (based on {estimated_distance_km} km)")
                
            except Exception as e:
                logger.warning(f"Failed to use pricing service, falling back to simple calculation: {str(e)}")
                # Fallback to simple calculation if pricing service fails
                base_cost = 15.0  # Base delivery cost
                distance_cost = estimated_distance_km * 2.5  # $2.5 per km
                vehicle_multiplier = {'CAR': 1.0, 'SUV': 1.2, 'PICKUP_TRUCK': 1.5, 'VAN': 1.3, 'BOX_TRUCK': 2.0}
                estimated_cost = base_cost + distance_cost * vehicle_multiplier.get(vehicle_type_db, 1.0)
                print(f"[COST] Fallback estimated cost: ${estimated_cost} (based on {estimated_distance_km} km)")
            
            # Step 6: Create delivery object
            delivery_data = {
                'customer_id': customer_id,
                'pickup_address': data['pickup_address'],
                'dropoff_address': data['dropoff_address'],
                'pickup_latitude': pickup_coords[0],
                'pickup_longitude': pickup_coords[1],
                'dropoff_latitude': dropoff_coords[0],
                'dropoff_longitude': dropoff_coords[1],
                'item_name': data['item_name'],
                'item_count': item_count,
                'weight': weight,
                'vehicle_type': vehicle_type_db,
                'package_size': package_size_db,
                'package_type': package_type_db,
                'delivery_type': data.get('delivery_type', 'standard'),
                'schedule_type': schedule_type.lower(),
                'delivery_preference': delivery_preference.lower(),
                'estimated_distance_km': estimated_distance_km,
                'estimated_cost': estimated_cost,
                'estimated_duration': estimated_duration_minutes
            }
            
            print(f"[DELIVERY] Final delivery data - Distance: {estimated_distance_km} km, Cost: ${estimated_cost}, Duration: {estimated_duration_minutes} min")
            
            # Add scheduling fields if scheduled delivery
            if schedule_type == 'scheduled':
                from datetime import datetime
                if isinstance(scheduled_date, str):
                    delivery_data['scheduled_date'] = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                else:
                    delivery_data['scheduled_date'] = scheduled_date
                delivery_data['time_slot'] = time_slot
            
            # Add optional fields
            optional_fields = [
                'item_description', 'item_photo_url', 'width', 'height', 'length',
                'is_fragile', 'is_perishable', 'requires_signature', 'special_instructions'
            ]
            
            for field in optional_fields:
                if field in data and data[field] is not None:
                    delivery_data[field] = data[field]
            
            # Handle scheduled time
            if 'scheduled_time' in data and data['scheduled_time']:
                delivery_data['scheduled_time'] = datetime.fromisoformat(
                    data['scheduled_time'].replace('Z', '+00:00')
                )
            
            # Create delivery using raw insert to bypass enum validation issues
            from sqlalchemy import text
            
            # Generate tracking number
            import uuid
            from datetime import datetime as dt
            tracking_number = f"DM{dt.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
            
            # Insert delivery directly with raw SQL to bypass enum issues
            insert_query = text("""
                INSERT INTO deliveries (
                    customer_id, pickup_address, dropoff_address, pickup_latitude, pickup_longitude,
                    dropoff_latitude, dropoff_longitude, item_name, item_description, item_photo_url,
                    package_type, package_size, width, height, length, weight, item_count,
                    vehicle_type, is_fragile, is_perishable, requires_signature, special_instructions,
                    delivery_type, status, schedule_type, scheduled_date, time_slot, delivery_preference,
                    estimated_distance_km, estimated_cost, estimated_duration, tracking_number,
                    created_at, updated_at, requested_time, insurance_amount
                ) VALUES (
                    :customer_id, :pickup_address, :dropoff_address, :pickup_latitude, :pickup_longitude,
                    :dropoff_latitude, :dropoff_longitude, :item_name, :item_description, :item_photo_url,
                    :package_type, :package_size, :width, :height, :length, :weight, :item_count,
                    :vehicle_type, :is_fragile, :is_perishable, :requires_signature, :special_instructions,
                    :delivery_type, 'REQUESTED', :schedule_type, :scheduled_date, :time_slot, :delivery_preference,
                    :estimated_distance_km, :estimated_cost, :estimated_duration, :tracking_number,
                    NOW(), NOW(), NOW(), 0.0
                ) RETURNING id
            """)
            
            # Prepare data for insert
            insert_data = {
                'customer_id': customer_id,
                'pickup_address': delivery_data['pickup_address'],
                'dropoff_address': delivery_data['dropoff_address'],
                'pickup_latitude': delivery_data['pickup_latitude'],
                'pickup_longitude': delivery_data['pickup_longitude'],
                'dropoff_latitude': delivery_data['dropoff_latitude'],
                'dropoff_longitude': delivery_data['dropoff_longitude'],
                'item_name': delivery_data['item_name'],
                'item_description': delivery_data.get('item_description'),
                'item_photo_url': delivery_data.get('item_photo_url'),
                'package_type': delivery_data['package_type'],
                'package_size': delivery_data['package_size'],
                'width': delivery_data.get('width'),
                'height': delivery_data.get('height'),
                'length': delivery_data.get('length'),
                'weight': delivery_data['weight'],
                'item_count': delivery_data['item_count'],
                'vehicle_type': delivery_data['vehicle_type'],
                'is_fragile': delivery_data.get('is_fragile', False),
                'is_perishable': delivery_data.get('is_perishable', False),
                'requires_signature': delivery_data.get('requires_signature', False),
                'special_instructions': delivery_data.get('special_instructions'),
                'delivery_type': delivery_data['delivery_type'],
                'schedule_type': delivery_data['schedule_type'],
                'scheduled_date': delivery_data.get('scheduled_date'),
                'time_slot': delivery_data.get('time_slot'),
                'delivery_preference': delivery_data['delivery_preference'],
                'estimated_distance_km': delivery_data['estimated_distance_km'],
                'estimated_cost': delivery_data['estimated_cost'],
                'estimated_duration': delivery_data['estimated_duration'],
                'tracking_number': tracking_number
            }
            
            result = db.session.execute(insert_query, insert_data)
            delivery_id = result.fetchone()[0]
            
            # Create delivery response data directly (bypass model loading)
            delivery_response = {
                'id': delivery_id,
                'customer_id': customer_id,
                'pickup_address': insert_data['pickup_address'],
                'dropoff_address': insert_data['dropoff_address'],
                'pickup_latitude': float(insert_data['pickup_latitude']),
                'pickup_longitude': float(insert_data['pickup_longitude']),
                'dropoff_latitude': float(insert_data['dropoff_latitude']),
                'dropoff_longitude': float(insert_data['dropoff_longitude']),
                'item_name': insert_data['item_name'],
                'item_description': insert_data['item_description'],
                'item_photo_url': insert_data['item_photo_url'],
                'package_type': insert_data['package_type'],
                'package_size': insert_data['package_size'],
                'width': float(insert_data['width']) if insert_data['width'] else None,
                'height': float(insert_data['height']) if insert_data['height'] else None,
                'length': float(insert_data['length']) if insert_data['length'] else None,
                'weight': float(insert_data['weight']),
                'item_count': insert_data['item_count'],
                'vehicle_type': insert_data['vehicle_type'],
                'is_fragile': insert_data['is_fragile'],
                'is_perishable': insert_data['is_perishable'],
                'requires_signature': insert_data['requires_signature'],
                'special_instructions': insert_data['special_instructions'],
                'delivery_type': insert_data['delivery_type'],
                'status': 'REQUESTED',
                'schedule_type': insert_data['schedule_type'],
                'scheduled_date': str(insert_data['scheduled_date']) if insert_data['scheduled_date'] else None,
                'time_slot': insert_data['time_slot'],
                'delivery_preference': insert_data['delivery_preference'],
                'estimated_distance_km': float(insert_data['estimated_distance_km']),
                'estimated_cost': float(insert_data['estimated_cost']),
                'estimated_duration': insert_data['estimated_duration'],
                'tracking_number': insert_data['tracking_number']
            }
            
            # For testing purposes, don't automatically assign driver
            # This allows us to test the complete driver flow
            driver_info = None
            print(f"[INFO] Delivery {delivery_id} created, waiting for driver to go online and accept")
            
            # Step 7: Set ETA for delivery
            if schedule_type == 'immediate':
                eta = f"{estimated_duration_minutes + 15}-{estimated_duration_minutes + 30} minutes"
            else:
                eta = f"Scheduled for {scheduled_date} between {time_slot}"
                print(f"[SCHEDULE] Scheduled delivery {delivery_id} created for {scheduled_date} at {time_slot}")
            
            # Commit all changes
            db.session.commit()
            
            return {
                'message': 'Delivery created successfully',
                'delivery': delivery_response,
                'driver': driver_info,
                'eta': eta,
                'tracking_number': tracking_number,
                'route_info': {
                    'distance': route_info['distance_text'],
                    'duration': route_info['duration_text'],
                    'status': route_info['status']
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating delivery: {str(e)}")
            return {'error': 'Failed to create delivery', 'details': str(e)}, 500

@delivery_api.route('/')
class DeliveryList(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get all deliveries for the authenticated customer"""
        customer_id = int(get_jwt_identity())
        
        # Get query parameters
        status = request.args.get('status')
        delivery_type = request.args.get('delivery_type')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Use raw SQL to avoid enum issues
        from sqlalchemy import text
        
        sql_query = """
        SELECT id, customer_id, driver_id, pickup_address, dropoff_address, 
               pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
               item_name, item_description, item_photo_url, package_type, package_size,
               width, height, length, weight, item_count, vehicle_type, is_fragile,
               is_perishable, requires_signature, special_instructions, delivery_type,
               status, schedule_type, scheduled_date, time_slot, delivery_preference,
               estimated_distance_km, estimated_cost, tracking_number, created_at, updated_at
        FROM deliveries 
        WHERE customer_id = :customer_id
        """
        
        params = {'customer_id': customer_id}
        
        if status:
            sql_query += " AND status = :status"
            params['status'] = status.upper()
        
        if delivery_type:
            sql_query += " AND delivery_type = :delivery_type"
            params['delivery_type'] = delivery_type
        
        sql_query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        result = db.session.execute(text(sql_query), params)
        rows = result.fetchall()
        
        delivery_list = []
        for row in rows:
            delivery_data = {
                'id': row[0],
                'customer_id': row[1],
                'driver_id': row[2],
                'pickup_address': row[3],
                'dropoff_address': row[4],
                'pickup_latitude': float(row[5]) if row[5] else None,
                'pickup_longitude': float(row[6]) if row[6] else None,
                'dropoff_latitude': float(row[7]) if row[7] else None,
                'dropoff_longitude': float(row[8]) if row[8] else None,
                'item_name': row[9],
                'item_description': row[10],
                'item_photo_url': row[11],
                'package_type': str(row[12]) if row[12] else None,
                'package_size': row[13],
                'width': float(row[14]) if row[14] else None,
                'height': float(row[15]) if row[15] else None,
                'length': float(row[16]) if row[16] else None,
                'weight': float(row[17]) if row[17] else None,
                'item_count': row[18],
                'vehicle_type': str(row[19]) if row[19] else None,
                'is_fragile': row[20],
                'is_perishable': row[21],
                'requires_signature': row[22],
                'special_instructions': row[23],
                'delivery_type': row[24],
                'status': str(row[25]) if row[25] else None,
                'schedule_type': row[26],
                'scheduled_date': str(row[27]) if row[27] else None,
                'time_slot': row[28],
                'delivery_preference': row[29],
                'estimated_distance_km': float(row[30]) if row[30] else None,
                'estimated_cost': float(row[31]) if row[31] else None,
                'tracking_number': row[32],
                'created_at': row[33].isoformat() if row[33] else None,
                'updated_at': row[34].isoformat() if row[34] else None
            }
            delivery_list.append(delivery_data)
        
        return {
            'deliveries': delivery_list,
            'total': len(delivery_list),
            'limit': limit,
            'offset': offset
        }, 200

@delivery_api.route('/<int:delivery_id>')
class DeliveryDetail(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success', delivery_model)
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get specific delivery details"""
        customer_id = int(get_jwt_identity())
        
        # Use raw SQL to avoid enum issues
        from sqlalchemy import text
        
        sql_query = text("""
        SELECT id, customer_id, driver_id, pickup_address, dropoff_address, 
               pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
               item_name, item_description, item_photo_url, package_type, package_size,
               width, height, length, weight, item_count, vehicle_type, is_fragile,
               is_perishable, requires_signature, special_instructions, delivery_type,
               status, schedule_type, scheduled_date, time_slot, delivery_preference,
               estimated_distance_km, estimated_cost, tracking_number, created_at, updated_at
        FROM deliveries 
        WHERE id = :delivery_id AND customer_id = :customer_id
        """)
        
        result = db.session.execute(sql_query, {'delivery_id': delivery_id, 'customer_id': customer_id})
        row = result.fetchone()
        
        if not row:
            return {'error': 'Delivery not found'}, 404
        
        delivery_data = {
            'id': row[0],
            'customer_id': row[1],
            'driver_id': row[2],
            'pickup_address': row[3],
            'dropoff_address': row[4],
            'pickup_latitude': float(row[5]) if row[5] else None,
            'pickup_longitude': float(row[6]) if row[6] else None,
            'dropoff_latitude': float(row[7]) if row[7] else None,
            'dropoff_longitude': float(row[8]) if row[8] else None,
            'item_name': row[9],
            'item_description': row[10],
            'item_photo_url': row[11],
            'package_type': row[12],
            'package_size': row[13],
            'width': float(row[14]) if row[14] else None,
            'height': float(row[15]) if row[15] else None,
            'length': float(row[16]) if row[16] else None,
            'weight': float(row[17]) if row[17] else None,
            'item_count': row[18],
            'vehicle_type': row[19],
            'is_fragile': row[20],
            'is_perishable': row[21],
            'requires_signature': row[22],
            'special_instructions': row[23],
            'delivery_type': row[24],
            'status': row[25],
            'schedule_type': row[26],
            'scheduled_date': str(row[27]) if row[27] else None,
            'time_slot': row[28],
            'delivery_preference': row[29],
            'estimated_distance_km': float(row[30]) if row[30] else None,
            'estimated_cost': float(row[31]) if row[31] else None,
            'tracking_number': row[32],
            'created_at': row[33].isoformat() if row[33] else None,
            'updated_at': row[34].isoformat() if row[34] else None
        }
        
        driver_info = None
        eta = None
        
        if row[2]:  # driver_id
            # Could fetch driver info here if needed
            status = row[25]  # status
            if status == 'ASSIGNED':
                eta = "15-30 minutes"
            elif status == 'ACCEPTED':
                eta = "10-20 minutes"
            elif status == 'PICKED_UP':
                eta = "En route"
        
        return {
            'delivery': delivery_data,
            'driver': driver_info,
            'eta': eta
        }, 200

@delivery_api.route('/<int:delivery_id>')
class UpdateDelivery(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.expect(update_delivery_model)
    @delivery_api.response(200, 'Delivery updated successfully', delivery_model)
    @delivery_api.response(400, 'Validation Error')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def put(self, delivery_id):
        """Update delivery details"""
        customer_id = int(get_jwt_identity())
        data = delivery_api.payload
        
        delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
        
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        if not delivery.can_be_updated():
            return {'error': 'Delivery cannot be updated in its current status'}, 400
        
        # Validate addresses if provided
        if 'pickup_address' in data and not validate_address(data['pickup_address']):
            return {'error': 'Invalid pickup address'}, 400
        
        if 'dropoff_address' in data and not validate_address(data['dropoff_address']):
            return {'error': 'Invalid dropoff address'}, 400
        
        # Validate dimensions if provided
        if any(field in data for field in ['width', 'height', 'length', 'weight']):
            if not validate_dimensions(
                data.get('width'), data.get('height'), 
                data.get('length'), data.get('weight')
            ):
                return {'error': 'Invalid package dimensions'}, 400
        
        try:
            # Update fields
            updatable_fields = [
                'pickup_address', 'dropoff_address', 'pickup_latitude', 'pickup_longitude',
                'dropoff_latitude', 'dropoff_longitude', 'item_name', 'item_description',
                'item_photo_url', 'width', 'height', 'length', 'weight', 'is_fragile',
                'is_perishable', 'requires_signature', 'special_instructions'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(delivery, field, data[field])
            
            # Handle scheduled time
            if 'scheduled_time' in data and data['scheduled_time']:
                delivery.scheduled_time = datetime.fromisoformat(
                    data['scheduled_time'].replace('Z', '+00:00')
                )
            
            # Recalculate estimates if addresses changed
            if 'pickup_address' in data or 'dropoff_address' in data:
                # Recalculate distance and cost (simplified)
                estimated_distance = 10.0  # Placeholder
                estimated_duration = 30  # Placeholder
                estimated_cost = calculate_estimated_cost(
                    estimated_distance,
                    delivery.package_type.value,
                    delivery.delivery_type,
                    'CAR',  # Default vehicle type for deliveries
                    delivery.is_fragile,
                    delivery.is_perishable,
                    delivery.requires_signature,
                    delivery.special_instructions
                )
                
                delivery.estimated_duration = estimated_duration
                delivery.estimated_cost = estimated_cost
            
            db.session.commit()
            
            return {
                'message': 'Delivery updated successfully',
                'delivery': delivery.to_dict()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to update delivery', 'details': str(e)}, 500

@delivery_api.route('/<int:delivery_id>/cancel')
class CancelDelivery(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery cancelled successfully')
    @delivery_api.response(400, 'Cannot cancel delivery')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Cancel a delivery"""
        customer_id = int(get_jwt_identity())
        
        delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
        
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        if not delivery.can_be_cancelled():
            return {'error': 'Delivery cannot be cancelled in its current status'}, 400
        
        try:
            # If delivery has an assigned driver, notify them about cancellation
            if delivery.driver_id:
                notification_service.create_notification(
                    driver_id=delivery.driver_id,
                    delivery_id=delivery.id,
                    notification_type='delivery_cancellation',
                    title='Delivery Cancelled',
                    message=f'Delivery {delivery.tracking_number} has been cancelled by the customer.'
                )
                
                # Update driver status back to available
                driver = Driver.query.get(delivery.driver_id)
                if driver:
                    driver.status = DriverStatus.AVAILABLE.value
            
            delivery.status = DeliveryStatus.CANCELLED.value
            delivery.cancelled_time = datetime.utcnow()
            db.session.commit()
            
            return {
                'message': 'Delivery cancelled successfully',
                'delivery': delivery.to_dict()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to cancel delivery', 'details': str(e)}, 500

@delivery_api.route('/available-slots/<date>')
class AvailableTimeSlots(Resource):
    @delivery_api.doc('get_available_time_slots')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(400, 'Invalid date format')
    def get(self, date):
        """Get available time slots for a specific date"""
        from datetime import datetime, date as dt_date
        
        # Validate date format
        try:
            delivery_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return {'error': 'Invalid date format. Use YYYY-MM-DD'}, 400
        
        # Validate date is not in the past
        today = dt_date.today()
        if delivery_date < today:
            return {'error': 'Date cannot be in the past'}, 400
        
        # Get available slots
        available_slots = get_available_time_slots(delivery_date)
        
        return {
            'date': date,
            'available_slots': available_slots
        }, 200

@delivery_api.route('/track/<tracking_number>')
class TrackDelivery(Resource):
    @delivery_api.response(200, 'Success')
    @delivery_api.response(404, 'Delivery not found')
    def get(self, tracking_number):
        """Track a delivery by tracking number (public endpoint)"""
        
        delivery = Delivery.query.filter_by(tracking_number=tracking_number).first()
        
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        delivery_data = delivery.to_dict()
        
        # Include minimal driver info for public tracking
        if delivery.driver_id:
            driver = Driver.query.get(delivery.driver_id)
            if driver:
                delivery_data['driver'] = {
                    'first_name': driver.first_name,
                    'last_name': driver.last_name,
                    'vehicle_model': driver.vehicle_model,
                    'vehicle_color': driver.vehicle_color
                }
        
        return {
            'delivery': delivery_data,
            'tracking_number': tracking_number
        }, 200 

@delivery_api.route('/<int:delivery_id>/messages')
class DeliveryCustomerMessages(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get conversation messages for a delivery (customer view)"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Get query parameters
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            from services.messaging_service import messaging_service
            
            success, result = messaging_service.get_delivery_conversation(
                delivery_id=delivery_id,
                user_id=customer_id,
                user_type='customer',
                limit=limit,
                offset=offset
            )
            
            if not success:
                return {'error': result}, 400
            
            return result, 200
            
        except Exception as e:
            return {'error': 'Failed to get messages', 'details': str(e)}, 500

    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.expect(create_delivery_model)  # Reuse for message content
    @delivery_api.response(201, 'Message sent successfully')
    @delivery_api.response(400, 'Invalid message data')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Send a message to driver for a delivery"""
        customer_id = int(get_jwt_identity())
        data = request.get_json()
        
        try:
            if 'item_name' not in data:  # Using item_name field for message content
                return {'error': 'Message content required'}, 400
            
            # Get delivery to find driver
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            if delivery.customer_id != customer_id:
                return {'error': 'Customer not authorized for this delivery'}, 400
            
            if not delivery.driver_id:
                return {'error': 'No driver assigned to this delivery yet'}, 400
            
            from services.messaging_service import messaging_service
            
            # Send message (using item_name field as content)
            success, message = messaging_service.send_customer_message(
                delivery_id=delivery_id,
                customer_id=customer_id,
                driver_id=delivery.driver_id,
                content=data['item_name'],  # Using item_name as message content
                subject=data.get('pickup_address'),  # Using pickup_address as subject
                is_urgent=data.get('is_fragile', False)  # Using is_fragile as urgent flag
            )
            
            if success:
                return {
                    'message': 'Message sent successfully',
                    'delivery_id': delivery_id,
                    'content': data['item_name']
                }, 201
            else:
                return {'error': message}, 400
                
        except Exception as e:
            return {'error': 'Failed to send message', 'details': str(e)}, 500

@delivery_api.route('/<int:delivery_id>/messages/mark-read')
class MarkCustomerMessagesAsRead(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Messages marked as read')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark all messages in a delivery as read (customer)"""
        customer_id = int(get_jwt_identity())
        
        try:
            from services.messaging_service import messaging_service
            
            success, message = messaging_service.mark_all_messages_as_read(
                delivery_id=delivery_id,
                user_id=customer_id
            )
            
            if not success:
                return {'error': message}, 400
            
            return {
                'message': message,
                'delivery_id': delivery_id
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to mark messages as read', 'details': str(e)}, 500

@delivery_api.route('/<int:delivery_id>/messages/unread-count')
class CustomerUnreadMessageCount(Resource):
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get count of unread messages for a delivery (customer)"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Validate delivery ownership
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            from services.messaging_service import messaging_service
            
            unread_count = messaging_service.get_unread_message_count(customer_id, 'customer')
            
            return {
                'unread_count': unread_count,
                'delivery_id': delivery_id,
                'customer_id': customer_id
            }, 200
            
        except Exception as e:
            return {'error': 'Failed to get unread count', 'details': str(e)}, 500

@delivery_api.route('/<int:delivery_id>/status')
class DeliveryStatusUpdate(Resource):
    """Update delivery status - CRITICAL FOR PAYMENT FLOW - SIMPLIFIED"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Status updated successfully')
    @delivery_api.response(400, 'Invalid status update')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def put(self, delivery_id):
        """Update delivery status - used for payment confirmation - SIMPLIFIED"""
        try:
            user_id = get_jwt_identity()
            # jwt identity can be str/int depending on issuer; normalize for comparisons
            try:
                user_id = int(user_id) if user_id is not None else None
            except Exception:
                pass
            data = request.get_json()
            
            # Debug: Log the incoming request
            logger.info(f"=== DELIVERY STATUS UPDATE REQUEST ===")
            logger.info(f"Delivery ID: {delivery_id}")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Request data: {data}")
            logger.info(f"JWT token present: {user_id is not None}")
            
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                logger.error(f"Delivery {delivery_id} not found")
                return {
                    'success': False,
                    'error': 'Delivery not found',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Get status update data first to check if this is a payment confirmation
            raw_status = data.get('status')
            if isinstance(raw_status, str):
                raw_status = raw_status.strip()

            # Accept both snake_case and camelCase from mobile clients
            payment_intent_id = data.get('payment_intent_id') or data.get('paymentIntentId')
            amount = data.get('amount')
            currency = (data.get('currency') or 'USD')
            updated_at = data.get('updated_at') or data.get('updatedAt')

            # Normalize status to lowercase for internal mapping/validation
            new_status = raw_status
            if isinstance(new_status, str):
                new_status = new_status.strip().lower()
            
            # Convert 'paid' to 'assigned' since 'paid' doesn't exist in database enum
            original_status = new_status
            if new_status == 'paid':
                new_status = 'assigned'  # Use 'assigned' which maps to DeliveryStatus.ASSIGNED
            
            # Special handling for payment confirmation updates
            is_payment_confirmation = (
                original_status == 'paid' and 
                payment_intent_id and 
                amount is not None
            )
            
            # Debug logging
            logger.info(f"=== PAYMENT CONFIRMATION ANALYSIS ===")
            logger.info(f"Original status: '{original_status}' (type: {type(original_status)})")
            logger.info(f"Payment intent ID: '{payment_intent_id}' (type: {type(payment_intent_id)})")
            logger.info(f"Amount: {amount} (type: {type(amount)})")
            logger.info(f"Currency: {currency}")
            logger.info(f"Delivery customer_id: {delivery.customer_id}")
            logger.info(f"User ID: {user_id}")
            logger.info(f"Is payment confirmation: {is_payment_confirmation}")
            logger.info(f"=== END ANALYSIS ===")
            
            # Check if this is a payment-related update (more flexible detection)
            is_payment_related = (
                bool(payment_intent_id) and
                amount is not None and
                (original_status in ['paid', 'assigned', 'confirmed', 'pending'])
            )
            
            logger.info(f"Is payment related: {is_payment_related}")
            
            # For payment-related updates, verify the payment exists first
            if is_payment_related:
                from models.payment import Payment
                logger.info(f"Processing payment-related update for delivery {delivery_id} with payment intent {payment_intent_id}")
                
                payment = Payment.query.filter_by(
                    stripe_payment_intent_id=payment_intent_id,
                    delivery_id=delivery_id
                ).first()
                
                if not payment:
                    logger.error(f"Payment verification failed for delivery {delivery_id} with payment intent {payment_intent_id}")
                    return {
                        'success': False,
                        'error': 'Payment verification failed - payment not found',
                        'error_code': 'PAYMENT_VERIFICATION_FAILED'
                    }, 400

                # Ensure the caller is the payer for this payment intent
                # (prevents other authenticated users from updating someone else's delivery via payment metadata)
                try:
                    if user_id is None or int(payment.payer_id) != int(user_id):
                        return {
                            'success': False,
                            'error': 'Access denied - not your payment',
                            'error_code': 'PAYMENT_ACCESS_DENIED'
                        }, 403
                except Exception:
                    return {
                        'success': False,
                        'error': 'Access denied - invalid user/payment identity',
                        'error_code': 'PAYMENT_ACCESS_DENIED'
                    }, 403
                
                # Verify payment amount matches.
                # Backend stores Payment.amount in dollars; mobile clients often send amount in cents.
                expected_amount = float(payment.amount or 0.0)
                try:
                    received_amount_raw = float(amount)
                except Exception:
                    return {
                        'success': False,
                        'error': f'Invalid amount: {amount}',
                        'error_code': 'INVALID_AMOUNT'
                    }, 400

                amount_tolerance = 0.01  # $0.01 tolerance
                received_amount = received_amount_raw

                # If amount looks like cents, convert to dollars when it matches expected.
                if abs(expected_amount - received_amount) > amount_tolerance:
                    received_amount_as_dollars = received_amount_raw / 100.0
                    if abs(expected_amount - received_amount_as_dollars) <= amount_tolerance:
                        received_amount = received_amount_as_dollars

                if abs(expected_amount - received_amount) > amount_tolerance:
                    # Don't block the delivery flow due to client-side amount differences.
                    # Trust the server-side Payment record and continue, but log for visibility.
                    logger.warning(
                        f"Payment amount mismatch for delivery {delivery_id}: expected {expected_amount}, "
                        f"received {received_amount_raw} (raw). Proceeding with expected amount."
                    )
                    received_amount = expected_amount
                
                # Payment verification successful - allow the update
                logger.info(f"Payment verification successful for delivery {delivery_id}")
            else:
                # Regular access check for non-payment updates
                if user_id is None:
                    logger.warning(f"No JWT token provided for non-payment update")
                    return {
                        'success': False,
                        'error': 'Authentication required for non-payment updates',
                        'error_code': 'AUTH_REQUIRED'
                    }, 401
                elif delivery.customer_id != user_id and delivery.driver_id != user_id:
                    logger.warning(f"Access denied - delivery {delivery_id} customer_id: {delivery.customer_id}, user_id: {user_id}, is_payment_related: {is_payment_related}")
                    return {
                        'success': False,
                        'error': 'Access denied - not your delivery',
                        'error_code': 'ACCESS_DENIED'
                    }, 403
            
            # Validate status
            valid_statuses = ['pending', 'assigned', 'accepted', 'confirmed', 'picked_up', 'in_transit', 'in_progress', 'completed', 'delivered', 'cancelled']
            if new_status and new_status not in valid_statuses:
                return {
                    'success': False,
                    'error': f'Invalid status: {new_status}',
                    'error_code': 'INVALID_STATUS',
                    'valid_statuses': valid_statuses
                }, 400
            
            # Update delivery status
            if new_status:
                # Convert string status to enum value
                from models.delivery import DeliveryStatus
                status_mapping = {
                    'pending': DeliveryStatus.PENDING,
                    'assigned': DeliveryStatus.ASSIGNED,
                    'accepted': DeliveryStatus.ACCEPTED,
                    'confirmed': DeliveryStatus.ASSIGNED,  # Map confirmed to ASSIGNED
                    'picked_up': DeliveryStatus.PICKED_UP,
                    'in_transit': DeliveryStatus.IN_TRANSIT,
                    'in_progress': DeliveryStatus.IN_PROGRESS,
                    'completed': DeliveryStatus.COMPLETED,
                    'delivered': DeliveryStatus.DELIVERED,
                    'cancelled': DeliveryStatus.CANCELLED
                }
                
                if new_status in status_mapping:
                    # `Delivery.status` is an Enum column; always assign the Enum value.
                    delivery.status = status_mapping[new_status]
                else:
                    return {
                        'success': False,
                        'error': f'Invalid status: {new_status}',
                        'error_code': 'INVALID_STATUS',
                        'valid_statuses': list(status_mapping.keys())
                    }, 400
            
            # Update payment information if provided
            if payment_intent_id:
                delivery.payment_intent_id = payment_intent_id
                # Only mark completed when this is a payment-related success update
                if is_payment_related:
                    delivery.payment_status = 'completed'
                    delivery.payment_completed_at = datetime.utcnow()
            
            if amount is not None:
                try:
                    # If we already normalized cents->dollars above, keep dollars.
                    delivery.actual_cost = float(locals().get('received_amount', amount))
                except Exception:
                    pass
            
            if currency:
                delivery.currency = currency.upper()
            
            if updated_at:
                try:
                    delivery.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except:
                    delivery.updated_at = datetime.utcnow()
            else:
                delivery.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Log the update
            if is_payment_related:
                logger.info(f"Payment-related update successful for delivery {delivery_id} - status updated to {new_status} with payment intent {payment_intent_id}")
            else:
                logger.info(f"Delivery {delivery_id} status updated to {new_status} by user {user_id}")
            
            # Return success response
            # For payment-related updates, we still persist ASSIGNED, and we also return the persisted status
            # so the client can reliably transition UI/state.
            response_status = safe_enum_to_string(delivery.status)
            
            return {
                'success': True,
                'data': {
                    'id': str(delivery_id),
                    'status': response_status,
                    'payment_status': delivery.payment_status,
                    'updated_at': delivery.updated_at.isoformat(),
                    'payment_intent_id': delivery.payment_intent_id,
                    'amount': float(delivery.actual_cost) if delivery.actual_cost else None,
                    'currency': delivery.currency
                },
                'message': 'Delivery status updated successfully'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating delivery status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to update delivery status',
                'error_code': 'UPDATE_ERROR',
                'details': str(e)
            }, 500

@delivery_api.route('/<int:delivery_id>/status/test')
class DeliveryStatusUpdateTest(Resource):
    """Update delivery status - TEST ENDPOINT (NO AUTH REQUIRED)"""
    @delivery_api.response(200, 'Status updated successfully')
    @delivery_api.response(400, 'Invalid status update')
    @delivery_api.response(404, 'Delivery not found')
    def put(self, delivery_id):
        """Update delivery status - TEST VERSION (NO AUTH)"""
        try:
            data = request.get_json()
            
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {
                    'success': False,
                    'error': 'Delivery not found',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Get status update data
            raw_status = data.get('status')
            if isinstance(raw_status, str):
                raw_status = raw_status.strip()
            new_status = raw_status.strip().lower() if isinstance(raw_status, str) else raw_status

            payment_intent_id = data.get('payment_intent_id') or data.get('paymentIntentId')
            amount = data.get('amount')
            currency = (data.get('currency') or 'USD')
            updated_at = data.get('updated_at') or data.get('updatedAt')
            
            # Validate status
            valid_statuses = ['pending', 'assigned', 'accepted', 'confirmed', 'picked_up', 'in_transit', 'in_progress', 'completed', 'delivered', 'cancelled']
            if new_status and new_status not in valid_statuses:
                return {
                    'success': False,
                    'error': f'Invalid status: {new_status}',
                    'error_code': 'INVALID_STATUS',
                    'valid_statuses': valid_statuses
                }, 400
            
            # Update delivery status
            if new_status:
                # Convert string status to enum value
                from models.delivery import DeliveryStatus
                status_mapping = {
                    'pending': DeliveryStatus.PENDING,
                    'assigned': DeliveryStatus.ASSIGNED,
                    'accepted': DeliveryStatus.ACCEPTED,
                    'confirmed': DeliveryStatus.ASSIGNED,  # Map confirmed to ASSIGNED
                    'picked_up': DeliveryStatus.PICKED_UP,
                    'in_transit': DeliveryStatus.IN_TRANSIT,
                    'in_progress': DeliveryStatus.IN_PROGRESS,
                    'completed': DeliveryStatus.COMPLETED,
                    'delivered': DeliveryStatus.DELIVERED,
                    'cancelled': DeliveryStatus.CANCELLED
                }
                
                if new_status in status_mapping:
                    # `Delivery.status` is an Enum column; always assign the Enum value.
                    delivery.status = status_mapping[new_status]
                else:
                    return {
                        'success': False,
                        'error': f'Invalid status: {new_status}',
                        'error_code': 'INVALID_STATUS',
                        'valid_statuses': list(status_mapping.keys())
                    }, 400
            
            # Update payment information if provided
            if payment_intent_id:
                delivery.payment_intent_id = payment_intent_id
                delivery.payment_status = 'completed'
                delivery.payment_completed_at = datetime.utcnow()
            
            if amount is not None:
                try:
                    delivery.actual_cost = float(amount)
                except Exception:
                    pass
            
            if currency:
                delivery.currency = currency.upper()
            
            if updated_at:
                try:
                    delivery.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except:
                    delivery.updated_at = datetime.utcnow()
            else:
                delivery.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Log the update
            logger.info(f"Delivery {delivery_id} status updated to {new_status} (TEST MODE)")
            
            # Return success response
            return {
                'success': True,
                'data': {
                    'id': str(delivery_id),
                    'status': safe_enum_to_string(delivery.status),
                    'payment_status': delivery.payment_status,
                    'updated_at': delivery.updated_at.isoformat(),
                    'payment_intent_id': delivery.payment_intent_id,
                    'amount': float(delivery.actual_cost) if delivery.actual_cost else None,
                    'currency': delivery.currency
                },
                'message': 'Delivery status updated successfully (TEST MODE)'
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating delivery status (TEST): {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to update delivery status',
                'error_code': 'UPDATE_ERROR',
                'details': str(e)
            }, 500

@delivery_api.route('/<int:delivery_id>/assign-driver/<int:driver_id>')
class AssignDriverTest(Resource):
    """Assign driver to delivery - TEST ENDPOINT (NO AUTH REQUIRED)"""
    @delivery_api.response(200, 'Driver assigned successfully')
    @delivery_api.response(404, 'Delivery or driver not found')
    def post(self, delivery_id, driver_id):
        """Assign a driver to a delivery - TEST VERSION (NO AUTH)"""
        try:
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            driver = Driver.query.get(driver_id)
            if not driver:
                return {'error': 'Driver not found'}, 404
            
            # Assign driver to delivery
            delivery.driver_id = driver_id
            delivery.status = DeliveryStatus.ASSIGNED
            delivery.assigned_time = datetime.utcnow()
            delivery.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'message': 'Driver assigned successfully',
                'delivery_id': delivery_id,
                'driver_id': driver_id,
                'status': 'ASSIGNED',
                'assigned_time': delivery.assigned_time.isoformat()
            }, 200
            
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to assign driver', 'details': str(e)}, 500

@delivery_api.route('/test-vehicle-type')
class TestVehicleType(Resource):
    """Test vehicle type validation - NO AUTH REQUIRED"""
    @delivery_api.response(200, 'Vehicle type validation result')
    def post(self):
        """Test what vehicle type the Flutter app is sending"""
        try:
            data = request.get_json() or {}
            vehicle_type_input = data.get('vehicle_type', 'No vehicle type provided')
            
            # Process the input the same way as the main endpoint
            processed_input = vehicle_type_input.lower().replace(' ', '_').replace('-', '_')
            
            vehicle_type_mapping = {
                'car': 'CAR',
                'suv': 'SUV', 
                'pickup_truck': 'PICKUP_TRUCK',
                'pickup': 'PICKUP_TRUCK',
                'cargo_van': 'CARGO_VAN',
                'cargo': 'CARGO_VAN',
                'van': 'CARGO_VAN',
                'box_truck': 'BOX_TRUCK',
                'box': 'BOX_TRUCK',
                'truck': 'BOX_TRUCK',
                'sedan': 'CAR'
            }
            
            result = vehicle_type_mapping.get(processed_input)
            
            return {
                'success': True,
                'original_input': vehicle_type_input,
                'processed_input': processed_input,
                'mapped_result': result,
                'is_valid': result is not None,
                'valid_types': list(vehicle_type_mapping.keys())
            }, 200
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }, 500

@delivery_api.route('/assigned')
@delivery_api.route('/driver/assigned')
class DriverAssignedDeliveries(Resource):
    """Get assigned deliveries for drivers from the last 2 days"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get all assigned deliveries from the last 2 days for the authenticated driver"""
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Calculate date 2 days ago
        from datetime import datetime, timedelta
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        
        # Use raw SQL to avoid enum issues and get assigned deliveries from last 2 days
        # Filter by driver's vehicle type to show only compatible deliveries
        from sqlalchemy import text, bindparam

        # Normalize driver vehicle type to match delivery.vehicle_type (stored as DB canonical like 'PICKUP_TRUCK')
        driver_vehicle_type_raw = (driver.vehicle_type or '').strip()
        driver_vehicle_type_key = driver_vehicle_type_raw.lower().replace(' ', '_').replace('-', '_')
        vehicle_type_mapping = {
            'car': 'CAR',
            'suv': 'SUV',
            'pickup_truck': 'PICKUP_TRUCK',
            'pickup': 'PICKUP_TRUCK',
            'cargo_van': 'CARGO_VAN',
            'cargo': 'CARGO_VAN',
            'van': 'CARGO_VAN',
            'box_truck': 'BOX_TRUCK',
            'box': 'BOX_TRUCK',
            'truck': 'BOX_TRUCK',
            'sedan': 'CAR'
        }

        canonical_vehicle_type = vehicle_type_mapping.get(driver_vehicle_type_key)
        if not canonical_vehicle_type:
            # Best-effort normalization for already-canonical values (e.g. "PICKUP_TRUCK")
            canonical_vehicle_type = driver_vehicle_type_raw.upper().replace(' ', '_').replace('-', '_')

        # Allow a small set of equivalent representations (covers legacy lowercased DB rows too)
        acceptable_vehicle_types_upper = sorted(set([
            canonical_vehicle_type.upper(),
            driver_vehicle_type_raw.upper().replace(' ', '_').replace('-', '_'),
        ]))
        
        sql_query = """
        SELECT id, customer_id, driver_id, pickup_address, dropoff_address, 
               pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
               item_name, item_description, item_photo_url, package_type, package_size,
               width, height, length, weight, item_count, vehicle_type, is_fragile,
               is_perishable, requires_signature, special_instructions, delivery_type,
               status, schedule_type, scheduled_date, time_slot, delivery_preference,
               estimated_distance_km, estimated_cost, estimated_duration, tracking_number,
               created_at, updated_at, assigned_time, requested_time
        FROM deliveries 
        WHERE status IN ('ASSIGNED', 'REQUESTED')
        AND created_at >= :two_days_ago
        AND REPLACE(REPLACE(UPPER(vehicle_type), ' ', '_'), '-', '_') IN :vehicle_types
        ORDER BY created_at DESC 
        LIMIT :limit OFFSET :offset
        """
        
        params = {
            'two_days_ago': two_days_ago,
            'vehicle_types': acceptable_vehicle_types_upper,
            'limit': limit,
            'offset': offset
        }
        
        result = db.session.execute(
            text(sql_query).bindparams(bindparam('vehicle_types', expanding=True)),
            params
        )
        rows = result.fetchall()
        
        delivery_list = []
        for row in rows:
            delivery_data = {
                'id': row[0],
                'customer_id': row[1],
                'driver_id': row[2],
                'pickup_address': row[3],
                'dropoff_address': row[4],
                'pickup_latitude': float(row[5]) if row[5] else None,
                'pickup_longitude': float(row[6]) if row[6] else None,
                'dropoff_latitude': float(row[7]) if row[7] else None,
                'dropoff_longitude': float(row[8]) if row[8] else None,
                'item_name': row[9],
                'item_description': row[10],
                'item_photo_url': row[11],
                'package_type': str(row[12]) if row[12] else None,
                'package_size': row[13],
                'width': float(row[14]) if row[14] else None,
                'height': float(row[15]) if row[15] else None,
                'length': float(row[16]) if row[16] else None,
                'weight': float(row[17]) if row[17] else None,
                'item_count': row[18],
                'vehicle_type': str(row[19]) if row[19] else None,
                'is_fragile': row[20],
                'is_perishable': row[21],
                'requires_signature': row[22],
                'special_instructions': row[23],
                'delivery_type': row[24],
                'status': str(row[25]) if row[25] else None,
                'schedule_type': row[26],
                'scheduled_date': str(row[27]) if row[27] else None,
                'time_slot': row[28],
                'delivery_preference': row[29],
                'estimated_distance_km': float(row[30]) if row[30] else None,
                'estimated_cost': (0.84) * float(row[31]) if row[31] else None,
                'estimated_duration': row[32],
                'tracking_number': row[33],
                'created_at': row[34].isoformat() if row[34] else None,
                'updated_at': row[35].isoformat() if row[35] else None,
                'assigned_time': row[36].isoformat() if row[36] else None,
                'requested_time': row[37].isoformat() if row[37] else None
            }
            
            # Add customer information
            customer = Customer.query.get(row[1])
            if customer:
                delivery_data['customer'] = {
                    'id': customer.id,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone': None,  # Phone number removed for privacy
                    'email': customer.email
                }
            
            delivery_list.append(delivery_data)
        
        # Get total count for pagination
        count_query = text("""
        SELECT COUNT(*) 
        FROM deliveries 
        WHERE status IN ('ASSIGNED', 'REQUESTED')
        AND created_at >= :two_days_ago
        AND REPLACE(REPLACE(UPPER(vehicle_type), ' ', '_'), '-', '_') IN :vehicle_types
        """)
        
        count_result = db.session.execute(count_query.bindparams(bindparam('vehicle_types', expanding=True)), {
            'two_days_ago': two_days_ago,
            'vehicle_types': acceptable_vehicle_types_upper
        })
        total_count = count_result.fetchone()[0]
        
        return {
            'deliveries': delivery_list,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'date_range': {
                'from': two_days_ago.isoformat(),
                'to': datetime.utcnow().isoformat()
            },
            'status_filter': ['ASSIGNED', 'REQUESTED'],
            'vehicle_type_filter': acceptable_vehicle_types_upper,
            'driver_info': {
                'id': driver.id,
                'name': driver.get_full_name(),
                'vehicle_type': driver.vehicle_type,
                'vehicle_make': driver.vehicle_make,
                'vehicle_model': driver.vehicle_model,
                'vehicle_year': driver.vehicle_year
            }
        }, 200

@delivery_api.route('/driver/accepted')
class DriverAcceptedDeliveries(Resource):
    """Get ACCEPTED deliveries for the authenticated driver"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Success')
    @delivery_api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Get deliveries in ACCEPTED status for the authenticated driver"""
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Pagination
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Optional time window (defaults to 7 days)
        from datetime import datetime, timedelta
        days = request.args.get('days', 7, type=int)
        days = max(1, min(days, 30))
        since = datetime.utcnow() - timedelta(days=days)
        
        from sqlalchemy import text
        
        sql_query = """
        SELECT id, customer_id, driver_id, pickup_address, dropoff_address, 
               pickup_latitude, pickup_longitude, dropoff_latitude, dropoff_longitude,
               item_name, item_description, item_photo_url, package_type, package_size,
               width, height, length, weight, item_count, vehicle_type, is_fragile,
               is_perishable, requires_signature, special_instructions, delivery_type,
               status, schedule_type, scheduled_date, time_slot, delivery_preference,
               estimated_distance_km, estimated_cost, estimated_duration, tracking_number,
               created_at, updated_at, accepted_time, requested_time
        FROM deliveries
        WHERE driver_id = :driver_id
          AND status = 'ACCEPTED'
          AND created_at >= :since
        ORDER BY accepted_time DESC NULLS LAST, created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        params = {
            'driver_id': driver_id,
            'since': since,
            'limit': limit,
            'offset': offset
        }
        
        rows = db.session.execute(text(sql_query), params).fetchall()
        
        deliveries = []
        for row in rows:
            delivery_data = {
                'id': row[0],
                'customer_id': row[1],
                'driver_id': row[2],
                'pickup_address': row[3],
                'dropoff_address': row[4],
                'pickup_latitude': float(row[5]) if row[5] else None,
                'pickup_longitude': float(row[6]) if row[6] else None,
                'dropoff_latitude': float(row[7]) if row[7] else None,
                'dropoff_longitude': float(row[8]) if row[8] else None,
                'item_name': row[9],
                'item_description': row[10],
                'item_photo_url': row[11],
                'package_type': str(row[12]) if row[12] else None,
                'package_size': row[13],
                'width': float(row[14]) if row[14] else None,
                'height': float(row[15]) if row[15] else None,
                'length': float(row[16]) if row[16] else None,
                'weight': float(row[17]) if row[17] else None,
                'item_count': row[18],
                'vehicle_type': str(row[19]) if row[19] else None,
                'is_fragile': row[20],
                'is_perishable': row[21],
                'requires_signature': row[22],
                'special_instructions': row[23],
                'delivery_type': row[24],
                'status': str(row[25]) if row[25] else None,
                'schedule_type': row[26],
                'scheduled_date': str(row[27]) if row[27] else None,
                'time_slot': row[28],
                'delivery_preference': row[29],
                'estimated_distance_km': float(row[30]) if row[30] else None,
                'estimated_cost': float(row[31]) if row[31] else None,
                'estimated_duration': row[32],
                'tracking_number': row[33],
                'created_at': row[34].isoformat() if row[34] else None,
                'updated_at': row[35].isoformat() if row[35] else None,
                'accepted_time': row[36].isoformat() if row[36] else None,
                'requested_time': row[37].isoformat() if row[37] else None
            }
            
            customer = Customer.query.get(row[1])
            if customer:
                delivery_data['customer'] = {
                    'id': customer.id,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone': None,
                    'email': customer.email
                }
            
            deliveries.append(delivery_data)
        
        count_query = text("""
        SELECT COUNT(*)
        FROM deliveries
        WHERE driver_id = :driver_id
          AND status = 'ACCEPTED'
          AND created_at >= :since
        """)
        total = db.session.execute(count_query, {'driver_id': driver_id, 'since': since}).fetchone()[0]
        
        return {
            'deliveries': deliveries,
            'total': total,
            'limit': limit,
            'offset': offset,
            'days': days,
            'status_filter': ['ACCEPTED'],
            'driver_info': {
                'id': driver.id,
                'name': driver.get_full_name(),
                'vehicle_type': driver.vehicle_type,
                'vehicle_make': driver.vehicle_make,
                'vehicle_model': driver.vehicle_model,
                'vehicle_year': driver.vehicle_year
            }
        }, 200

@delivery_api.route('/<int:delivery_id>/accept')
class AcceptDelivery(Resource):
    """Accept a delivery assignment by driver"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery accepted successfully')
    @delivery_api.response(400, 'Cannot accept delivery')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Accept a delivery assignment"""
        from models.delivery import DeliveryStatus
        
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Get the delivery
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Check if delivery is in ASSIGNED status
        if delivery.status != DeliveryStatus.ASSIGNED:
            return {
                'error': 'Delivery cannot be accepted',
                'current_status': safe_enum_to_string(delivery.status),
                'required_status': 'ASSIGNED'
            }, 400
        
        # Check if delivery is assigned to this driver
        if delivery.driver_id and delivery.driver_id != driver_id:
            return {'error': 'This delivery is not assigned to you'}, 403
        
        # Check if driver's vehicle type matches delivery requirements
        delivery_vehicle = normalize_vehicle_type(delivery.vehicle_type)
        driver_vehicle = normalize_vehicle_type(driver.vehicle_type)
        if delivery_vehicle and driver_vehicle and delivery_vehicle != driver_vehicle:
            return {
                'error': 'Vehicle type mismatch',
                'delivery_requires': delivery_vehicle,
                'driver_has': driver_vehicle
            }, 400
        
        try:
            # Update delivery status to ACCEPTED
            # Delivery.status is an Enum column; assign the Enum value
            delivery.status = DeliveryStatus.ACCEPTED
            delivery.accepted_time = datetime.utcnow()
            delivery.driver_id = driver_id  # Ensure driver is assigned
            delivery.updated_at = datetime.utcnow()
            
            # Update driver status to BUSY
            # Driver.status is an Enum column; assign the Enum value
            driver.status = DriverStatus.BUSY
            driver.is_available = False
            driver.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Create notification for customer about driver acceptance
            try:
                notification_service.create_notification(
                    user_id=delivery.customer_id,
                    user_type='customer',
                    delivery_id=delivery.id,
                    notification_type='delivery_accepted',
                    title='Driver Assigned',
                    message=f'Driver {driver.get_full_name()} has accepted your delivery request.'
                )
            except Exception as e:
                logger.warning(f"Failed to send customer notification: {str(e)}")
            
            # Get customer information
            customer = Customer.query.get(delivery.customer_id)
            customer_info = None
            if customer:
                customer_info = {
                    'id': customer.id,
                    'first_name': customer.first_name,
                    'last_name': customer.last_name,
                    'phone': None,  # Phone number removed for privacy
                    'email': customer.email
                }
            
            # Return accepted delivery information
            return {
                'success': True,
                'message': 'Delivery accepted successfully',
                'delivery': {
                    'id': delivery.id,
                    'tracking_number': delivery.tracking_number,
                    'status': safe_enum_to_string(delivery.status),  # Ensure string conversion
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'pickup_latitude': float(delivery.pickup_latitude) if delivery.pickup_latitude else None,
                    'pickup_longitude': float(delivery.pickup_longitude) if delivery.pickup_longitude else None,
                    'dropoff_latitude': float(delivery.dropoff_latitude) if delivery.dropoff_latitude else None,
                    'dropoff_longitude': float(delivery.dropoff_longitude) if delivery.dropoff_longitude else None,
                    'item_name': delivery.item_name,
                    'item_description': delivery.item_description,
                    'item_count': delivery.item_count,
                    'weight': float(delivery.weight) if delivery.weight else None,
                    'package_type': safe_enum_to_string(delivery.package_type),
                    'package_size': delivery.package_size,
                    'is_fragile': delivery.is_fragile,
                    'is_perishable': delivery.is_perishable,
                    'requires_signature': delivery.requires_signature,
                    'special_instructions': delivery.special_instructions,
                    'delivery_type': safe_enum_to_string(delivery.delivery_type),
                    'estimated_distance_km': float(delivery.estimated_distance_km) if delivery.estimated_distance_km else None,
                    'estimated_cost': (0.84) * float(delivery.estimated_cost) if delivery.estimated_cost else None,
                    'estimated_duration': delivery.estimated_duration,
                    'accepted_time': delivery.accepted_time.isoformat() if delivery.accepted_time else None,
                    'created_at': delivery.created_at.isoformat() if delivery.created_at else None
                },
                'customer': customer_info,
                'driver': {
                    'id': driver.id,
                    'name': driver.get_full_name(),
                    'phone': None,  # Phone number removed for privacy
                    'vehicle_type': safe_enum_to_string(driver.vehicle_type),
                    'vehicle_make': driver.vehicle_make,
                    'vehicle_model': driver.vehicle_model,
                    'vehicle_year': driver.vehicle_year,
                    'rating': float(driver.rating) if driver.rating else 5.0
                },
                'next_steps': {
                    'pickup_location': {
                        'address': delivery.pickup_address,
                        'latitude': float(delivery.pickup_latitude) if delivery.pickup_latitude else None,
                        'longitude': float(delivery.pickup_longitude) if delivery.pickup_longitude else None
                    },
                    'dropoff_location': {
                        'address': delivery.dropoff_address,
                        'latitude': float(delivery.dropoff_latitude) if delivery.dropoff_latitude else None,
                        'longitude': float(delivery.dropoff_longitude) if delivery.dropoff_longitude else None
                    },
                    'estimated_pickup_time': f"{delivery.estimated_duration + 10}-{delivery.estimated_duration + 20} minutes",
                    'update_status_endpoint': f'/api/deliveries/{delivery.id}/status'
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error accepting delivery: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to accept delivery',
                'details': str(e)
            }, 500

@delivery_api.route('/test-delivery')
class TestDelivery(Resource):
    """Create a test delivery with CARGO_VAN - NO AUTH REQUIRED"""
    @delivery_api.response(201, 'Test delivery created successfully')
    @delivery_api.response(400, 'Invalid delivery data')
    def post(self):
        """Create a test delivery for testing purposes"""
        try:
            data = request.get_json() or {}
            
            # Default test delivery data
            test_delivery_data = {
                'customer_id': data.get('customer_id', 1),  # Default customer ID
                'pickup_address': data.get('pickup_address', '123 Main St, New York, NY 10001'),
                'dropoff_address': data.get('dropoff_address', '456 Oak Ave, Brooklyn, NY 11201'),
                'item_name': data.get('item_name', 'Test Package'),
                'item_description': data.get('item_description', 'A test package for delivery'),
                'weight': data.get('weight', 5.0),
                'vehicle_type': 'CARGO_VAN',  # Use CARGO_VAN (uppercase for database)
                'package_type': 'MEDIUM',  # Required field
                'estimated_distance_km': data.get('estimated_distance_km', 8.5),
                'special_instructions': data.get('special_instructions', 'Test delivery - please handle with care'),
                'is_fragile': data.get('is_fragile', False),
                'is_perishable': data.get('is_perishable', False),
                'requires_signature': data.get('requires_signature', True)
            }
            
            print(f"[TEST] Test delivery data - Distance: {test_delivery_data['estimated_distance_km']} km")
            
            # Create delivery
            delivery = Delivery(**test_delivery_data)
            delivery.status = 'REQUESTED'
            delivery.payment_status = 'pending'
            
            db.session.add(delivery)
            db.session.commit()
            
            # Calculate pricing for CARGO_VAN
            pricing_service = PricingService()
            cost_breakdown = pricing_service.calculate_delivery_cost_with_pricing(
                distance_km=float(delivery.estimated_distance_km),
                vehicle_type='cargo_van'
            )
            
            # Update delivery with calculated cost
            delivery.estimated_cost = cost_breakdown['total_cost']
            delivery.currency = 'USD'
            db.session.commit()
            
            logger.info(f"Test delivery created: {delivery.id} with CARGO_VAN")
            
            return {
                'success': True,
                'message': 'Test delivery created successfully',
                'delivery': {
                    'id': delivery.id,
                    'customer_id': delivery.customer_id,
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'item_name': delivery.item_name,
                    'vehicle_type': safe_enum_to_string(delivery.vehicle_type),
                    'status': safe_enum_to_string(delivery.status),
                    'payment_status': delivery.payment_status,
                    'estimated_distance_km': delivery.estimated_distance_km,
                    'estimated_cost': float(delivery.estimated_cost) if delivery.estimated_cost else None,
                    'currency': delivery.currency,
                    'created_at': delivery.created_at.isoformat()
                },
                'pricing_breakdown': cost_breakdown,
                'next_steps': {
                    'create_payment_intent': f'/api/mobile-payments/create-payment-intent',
                    'update_status': f'/api/deliveries/{delivery.id}/status/test'
                }
            }, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating test delivery: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to create test delivery',
                'error_code': 'CREATE_ERROR',
                'details': str(e)
            }, 500

@delivery_api.route('/<int:delivery_id>/pickup')
class PickupDelivery(Resource):
    """Mark delivery as picked up by driver"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery picked up successfully')
    @delivery_api.response(400, 'Cannot pickup delivery')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as picked up"""
        from models.delivery import DeliveryStatus
        
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Get the delivery
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Check if delivery is assigned to this driver
        if delivery.driver_id != driver_id:
            return {'error': 'This delivery is not assigned to you'}, 403
        
        # Check if delivery is in ACCEPTED or ASSIGNED status
        if delivery.status not in [DeliveryStatus.ACCEPTED, DeliveryStatus.ASSIGNED]:
            return {
                'error': 'Delivery cannot be picked up',
                'current_status': safe_enum_to_string(delivery.status),
                'required_status': 'ACCEPTED or ASSIGNED'
            }, 400
        
        try:
            # Update delivery status to PICKED_UP
            delivery.status = DeliveryStatus.PICKED_UP.value
            delivery.pickup_time = datetime.utcnow()
            delivery.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Create notification for customer
            try:
                notification_service.create_notification(
                    user_id=delivery.customer_id,
                    user_type='customer',
                    delivery_id=delivery.id,
                    notification_type='delivery_picked_up',
                    title='Package Picked Up',
                    message=f'Your package has been picked up by {driver.get_full_name()}.'
                )
            except Exception as e:
                logger.warning(f"Failed to send customer notification: {str(e)}")
            
            return {
                'success': True,
                'message': 'Delivery picked up successfully',
                'delivery': {
                    'id': delivery.id,
                    'status': safe_enum_to_string(delivery.status),
                    'pickup_time': delivery.pickup_time.isoformat(),
                    'driver': {
                        'id': driver.id,
                        'name': driver.get_full_name(),
                        'phone': driver.phone_number
                    }
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error picking up delivery: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to pickup delivery',
                'details': str(e)
            }, 500

@delivery_api.route('/<int:delivery_id>/start-transit')
class StartTransit(Resource):
    """Mark delivery as in transit"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery started transit successfully')
    @delivery_api.response(400, 'Cannot start transit')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as in transit"""
        from models.delivery import DeliveryStatus
        
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Get the delivery
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Check if delivery is assigned to this driver
        if delivery.driver_id != driver_id:
            return {'error': 'This delivery is not assigned to you'}, 403
        
        # Check if delivery is in PICKED_UP status
        if delivery.status != DeliveryStatus.PICKED_UP:
            return {
                'error': 'Delivery cannot start transit',
                'current_status': safe_enum_to_string(delivery.status),
                'required_status': 'PICKED_UP'
            }, 400
        
        try:
            # Update delivery status to IN_TRANSIT
            delivery.status = DeliveryStatus.IN_TRANSIT.value
            delivery.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Create notification for customer
            try:
                notification_service.create_notification(
                    user_id=delivery.customer_id,
                    user_type='customer',
                    delivery_id=delivery.id,
                    notification_type='delivery_in_transit',
                    title='Package In Transit',
                    message=f'Your package is now in transit with {driver.get_full_name()}.'
                )
            except Exception as e:
                logger.warning(f"Failed to send customer notification: {str(e)}")
            
            return {
                'success': True,
                'message': 'Delivery started transit successfully',
                'delivery': {
                    'id': delivery.id,
                    'status': safe_enum_to_string(delivery.status),
                    'updated_at': delivery.updated_at.isoformat(),
                    'driver': {
                        'id': driver.id,
                        'name': driver.get_full_name(),
                        'phone': driver.phone_number
                    }
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting transit: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to start transit',
                'details': str(e)
            }, 500

@delivery_api.route('/<int:delivery_id>/complete')
class CompleteDelivery(Resource):
    """Mark delivery as completed"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery completed successfully')
    @delivery_api.response(400, 'Cannot complete delivery')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self, delivery_id):
        """Mark delivery as completed"""
        from models.delivery import DeliveryStatus
        
        driver_id = int(get_jwt_identity())
        
        # Verify the user is a driver
        driver = Driver.query.get(driver_id)
        if not driver:
            return {'error': 'Driver not found'}, 404
        
        # Get the delivery
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            return {'error': 'Delivery not found'}, 404
        
        # Check if delivery is assigned to this driver
        if delivery.driver_id != driver_id:
            return {'error': 'This delivery is not assigned to you'}, 403
        
        # Check if delivery is in IN_TRANSIT or PICKED_UP status
        if delivery.status not in [DeliveryStatus.IN_TRANSIT, DeliveryStatus.PICKED_UP]:
            return {
                'error': 'Delivery cannot be completed',
                'current_status': safe_enum_to_string(delivery.status),
                'required_status': 'IN_TRANSIT or PICKED_UP'
            }, 400
        
        try:
            # Update delivery status to DELIVERED
            delivery.status = DeliveryStatus.DELIVERED.value
            delivery.delivered_time = datetime.utcnow()
            delivery.updated_at = datetime.utcnow()
            
            # Update driver status back to available
            driver.status = DriverStatus.AVAILABLE.value
            driver.is_available = True
            driver.updated_at = datetime.utcnow()
            
            # Commit changes
            db.session.commit()
            
            # Create notification for customer
            try:
                notification_service.create_notification(
                    user_id=delivery.customer_id,
                    user_type='customer',
                    delivery_id=delivery.id,
                    notification_type='delivery_completed',
                    title='Package Delivered',
                    message=f'Your package has been delivered by {driver.get_full_name()}.'
                )
            except Exception as e:
                logger.warning(f"Failed to send customer notification: {str(e)}")
            
            return {
                'success': True,
                'message': 'Delivery completed successfully',
                'delivery': {
                    'id': delivery.id,
                    'status': safe_enum_to_string(delivery.status),
                    'delivered_time': delivery.delivered_time.isoformat(),
                    'driver': {
                        'id': driver.id,
                        'name': driver.get_full_name(),
                        'phone': driver.phone_number
                    }
                }
            }, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error completing delivery: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to complete delivery',
                'details': str(e)
            }, 500

@delivery_api.route('/item-photo/upload-url')
class GetItemPhotoUploadUrl(Resource):
    """Get signed URL for uploading delivery item photo"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.expect(item_photo_upload_model)
    @delivery_api.response(200, 'Upload URL generated successfully', item_photo_upload_response_model)
    @delivery_api.response(400, 'Validation Error')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self):
        """Get signed URL for uploading delivery item photo"""
        customer_id = int(get_jwt_identity())
        data = delivery_api.payload
        
        # Validate required fields
        required_fields = ['delivery_id', 'filename', 'content_type']
        if not all(k in data for k in required_fields):
            return {'error': f'Missing required fields: {", ".join([f for f in required_fields if f not in data])}'}, 400
        
        # Validate content type (only allow images)
        allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if data['content_type'] not in allowed_content_types:
            return {'error': f'Invalid content type. Must be one of: {", ".join(allowed_content_types)}'}, 400
        
        try:
            delivery_id = int(data['delivery_id'])
            
            # Verify delivery exists and belongs to the customer
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                return {'error': 'Delivery not found or access denied'}, 404
            
            # Check if delivery can be updated (not completed or cancelled)
            if delivery.status in ['DELIVERED', 'CANCELLED', 'FAILED']:
                return {'error': 'Cannot upload photo for completed or cancelled delivery'}, 400
            
            # Get signed upload URL using storage service
            upload_url, object_key = get_storage_service().get_item_photo_upload_url(
                delivery_id=delivery_id,
                filename=data['filename'],
                content_type=data['content_type']
            )
            
            # Clean up old photo if exists
            old_object_key = delivery.item_photo_url
            if old_object_key:
                get_storage_service().cleanup_old_item_photo(delivery_id, old_object_key)
            
            # Update delivery with new photo URL immediately
            delivery.item_photo_url = object_key
            delivery.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'upload_url': upload_url,
                'object_key': object_key,
                'expires_in': 600,  # 10 minutes
                'item_photo_url': object_key,  # The GCP object key/URL
                'delivery_id': delivery_id,
                'message': f'Upload URL generated and delivery updated. Upload file using upload_url.'
            }, 200
            
        except ValueError:
            return {'error': 'delivery_id must be a valid integer'}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to generate upload URL', 'details': str(e)}, 500

@delivery_api.route('/item-photo/upload-url/public')
class GetPublicItemPhotoUploadUrl(Resource):
    """Get signed URL for uploading delivery item photo (public endpoint - no auth required)"""
    @delivery_api.expect(delivery_api.model('PublicItemPhotoUpload', {
        'delivery_id': fields.Integer(required=True, description='Delivery ID'),
        'filename': fields.String(required=True, description='Original filename'),
        'content_type': fields.String(required=True, description='MIME type of the file')
    }))
    @delivery_api.response(200, 'Upload URL generated successfully', item_photo_upload_response_model)
    @delivery_api.response(400, 'Validation Error')
    @delivery_api.response(404, 'Delivery not found')
    def post(self):
        """Get signed URL for uploading delivery item photo (public endpoint - no auth required)"""
        data = delivery_api.payload
        
        # Validate required fields
        required_fields = ['delivery_id', 'filename', 'content_type']
        if not all(k in data for k in required_fields):
            return {'error': f'Missing required fields: {", ".join([f for f in required_fields if f not in data])}'}, 400
        
        # Validate content type (only allow images)
        allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if data['content_type'] not in allowed_content_types:
            return {'error': f'Invalid content type. Must be one of: {", ".join(allowed_content_types)}'}, 400
        
        try:
            delivery_id = int(data['delivery_id'])
            
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            # Check if delivery can be updated (not completed or cancelled)
            if delivery.status in ['DELIVERED', 'CANCELLED', 'FAILED']:
                return {'error': 'Cannot upload photo for completed or cancelled delivery'}, 400
            
            # Get signed upload URL using storage service
            upload_url, object_key = get_storage_service().get_item_photo_upload_url(
                delivery_id=delivery_id,
                filename=data['filename'],
                content_type=data['content_type']
            )
            
            # Clean up old photo if exists
            old_object_key = delivery.item_photo_url
            if old_object_key:
                get_storage_service().cleanup_old_item_photo(delivery_id, old_object_key)
            
            # Update delivery with new photo URL immediately
            delivery.item_photo_url = object_key
            delivery.updated_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'upload_url': upload_url,
                'object_key': object_key,
                'expires_in': 600,  # 10 minutes
                'item_photo_url': object_key,  # The GCP object key/URL
                'delivery_id': delivery_id,
                'message': f'Upload URL generated and delivery updated. Upload file using upload_url.'
            }, 200
            
        except ValueError:
            return {'error': 'delivery_id must be a valid integer'}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to generate upload URL', 'details': str(e)}, 500

@delivery_api.route('/item-photo/confirm-upload')
class ConfirmItemPhotoUpload(Resource):
    """Confirm item photo upload and update delivery record"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.expect(item_photo_confirm_model)
    @delivery_api.response(200, 'Item photo upload confirmed successfully')
    @delivery_api.response(400, 'Validation Error')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def post(self):
        """Confirm item photo upload and update delivery record"""
        customer_id = int(get_jwt_identity())
        data = delivery_api.payload
        
        # Validate required fields
        required_fields = ['delivery_id', 'object_key']
        if not all(k in data for k in required_fields):
            return {'error': f'Missing required fields: {", ".join([f for f in required_fields if f not in data])}'}, 400
        
        try:
            delivery_id = int(data['delivery_id'])
            
            # Verify delivery exists and belongs to the customer
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                return {'error': 'Delivery not found or access denied'}, 404
            
            # Check if delivery can be updated (not completed or cancelled)
            if delivery.status in ['DELIVERED', 'CANCELLED', 'FAILED']:
                return {'error': 'Cannot update photo for completed or cancelled delivery'}, 400
            
            # Verify object exists in storage
            if not get_storage_service().object_exists(get_storage_service().bucket_name, data['object_key']):
                return {'error': 'Item photo not found in storage'}, 400
            
            # Clean up old photo if exists
            old_object_key = delivery.item_photo_url
            if old_object_key:
                get_storage_service().cleanup_old_item_photo(delivery_id, old_object_key)
            
            # Update delivery with new photo URL
            delivery.item_photo_url = data['object_key']
            delivery.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'message': 'Item photo upload confirmed successfully',
                'delivery_id': delivery_id,
                'object_key': data['object_key'],
                'photo_url': delivery.item_photo_url
            }, 200
            
        except ValueError:
            return {'error': 'delivery_id must be a valid integer'}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': 'Failed to confirm item photo upload', 'details': str(e)}, 500

@delivery_api.route('/item-photo/test-upload')
class TestItemPhotoUpload(Resource):
    """Test item photo upload functionality - NO AUTH REQUIRED"""
    @delivery_api.response(200, 'Test upload URL generated successfully')
    @delivery_api.response(400, 'Invalid test data')
    def post(self):
        """Test item photo upload functionality"""
        try:
            data = request.get_json() or {}
            
            # Default test data
            test_data = {
                'delivery_id': data.get('delivery_id', 1),  # Default delivery ID
                'filename': data.get('filename', 'test_item_photo.jpg'),
                'content_type': data.get('content_type', 'image/jpeg')
            }
            
            # Validate content type
            allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if test_data['content_type'] not in allowed_content_types:
                return {'error': f'Invalid content type. Must be one of: {", ".join(allowed_content_types)}'}, 400
            
            # Get signed upload URL using storage service
            upload_url, object_key = get_storage_service().get_item_photo_upload_url(
                delivery_id=test_data['delivery_id'],
                filename=test_data['filename'],
                content_type=test_data['content_type']
            )
            
            logger.info(f"Test item photo upload URL generated for delivery {test_data['delivery_id']}")
            
            return {
                'success': True,
                'message': 'Test item photo upload URL generated successfully',
                'test_data': test_data,
                'upload_url': upload_url,
                'object_key': object_key,
                'item_photo_url': object_key,  # The GCP object key/URL
                'expires_in': 600,
                'next_steps': {
                    'upload_file': 'Use the upload_url to PUT the file',
                    'note': 'This is a test endpoint - no authentication required. item_photo_url contains the GCP object key.'
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error generating test item photo upload URL: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to generate test upload URL',
                'error_code': 'TEST_ERROR',
                'details': str(e)
            }, 500

@delivery_api.route('/item-photo/<int:delivery_id>')
class GetItemPhotoUrl(Resource):
    """Get signed download URL for delivery item photo"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Item photo URL generated successfully')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found or no photo available')
    @jwt_required()
    def get(self, delivery_id):
        """Get signed download URL for delivery item photo"""
        customer_id = int(get_jwt_identity())
        
        try:
            # Verify delivery exists and belongs to the customer
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                return {'error': 'Delivery not found or access denied'}, 404
            
            # Check if delivery has an item photo
            if not delivery.item_photo_url:
                return {'error': 'No item photo available for this delivery'}, 404
            
            # Get signed download URL
            download_url = get_storage_service().get_download_url(
                object_key=delivery.item_photo_url,
                expires_seconds=3600  # 1 hour
            )
            
            return {
                'delivery_id': delivery_id,
                'item_photo_url': delivery.item_photo_url,
                'download_url': download_url,
                'expires_in': 3600,
                'message': 'Item photo download URL generated successfully'
            }, 200
            
        except Exception as e:
            logger.error(f"Error generating item photo download URL: {str(e)}", exc_info=True)
            return {'error': 'Failed to generate item photo URL', 'details': str(e)}, 500

@delivery_api.route('/item-photo/<int:delivery_id>/public')
class GetPublicItemPhotoUrl(Resource):
    """Get signed download URL for delivery item photo (public endpoint - no auth required)"""
    @delivery_api.response(200, 'Item photo URL generated successfully')
    @delivery_api.response(404, 'Delivery not found or no photo available')
    def get(self, delivery_id):
        """Get signed download URL for delivery item photo (public endpoint)"""
        try:
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            # Check if delivery has an item photo
            if not delivery.item_photo_url:
                return {'error': 'No item photo available for this delivery'}, 404
            
            # Get signed download URL
            download_url = get_storage_service().get_download_url(
                object_key=delivery.item_photo_url,
                expires_seconds=3600  # 1 hour
            )
            
            return {
                'delivery_id': delivery_id,
                'item_photo_url': delivery.item_photo_url,
                'download_url': download_url,
                'expires_in': 3600,
                'message': 'Item photo download URL generated successfully'
            }, 200
            
        except Exception as e:
            logger.error(f"Error generating public item photo download URL: {str(e)}", exc_info=True)
            return {'error': 'Failed to generate item photo URL', 'details': str(e)}, 500

@delivery_api.route('/item-photo/<int:delivery_id>/view')
class ViewItemPhoto(Resource):
    """Direct redirect to item photo (public endpoint - no auth required)"""
    @delivery_api.response(302, 'Redirect to item photo')
    @delivery_api.response(404, 'Delivery not found or no photo available')
    def get(self, delivery_id):
        """Direct redirect to item photo for easy viewing"""
        try:
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {'error': 'Delivery not found'}, 404
            
            # Check if delivery has an item photo
            if not delivery.item_photo_url:
                return {'error': 'No item photo available for this delivery'}, 404
            
            # Get signed download URL
            download_url = get_storage_service().get_download_url(
                object_key=delivery.item_photo_url,
                expires_seconds=3600  # 1 hour
            )
            
            # Redirect directly to the image
            from flask import redirect
            return redirect(download_url)
            
        except Exception as e:
            logger.error(f"Error redirecting to item photo: {str(e)}", exc_info=True)
            return {'error': 'Failed to access item photo', 'details': str(e)}, 500

@delivery_api.route('/<int:delivery_id>/status')
class DeliveryStatusPolling(Resource):
    """Poll delivery status with comprehensive information including driver details"""
    @delivery_api.doc(security='Bearer Auth')
    @delivery_api.response(200, 'Delivery status retrieved successfully')
    @delivery_api.response(401, 'Unauthorized')
    @delivery_api.response(404, 'Delivery not found')
    @jwt_required()
    def get(self, delivery_id):
        """Get current delivery status with driver information for polling"""
        try:
            user_id = int(get_jwt_identity())
            
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {
                    'success': False,
                    'error': 'Delivery not found',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Check access permissions (customer or driver)
            if delivery.customer_id != user_id and delivery.driver_id != user_id:
                return {
                    'success': False,
                    'error': 'Access denied - not your delivery',
                    'error_code': 'ACCESS_DENIED'
                }, 403
            
            # Get driver information if assigned
            driver_info = None
            if delivery.driver_id:
                driver = Driver.query.get(delivery.driver_id)
                if driver:
                    driver_info = {
                        'id': driver.id,
                        'first_name': driver.first_name,
                        'last_name': driver.last_name,
                        'full_name': driver.get_full_name(),
                        'phone_number': None,  # Phone number removed for privacy
                        'email': driver.email,
                        'vehicle_type': safe_enum_to_string(driver.vehicle_type),
                        'vehicle_make': driver.vehicle_make,
                        'vehicle_model': driver.vehicle_model,
                        'vehicle_year': driver.vehicle_year,
                        'vehicle_plate_number': driver.vehicle_plate_number,
                        'license_number': driver.license_number,
                        'rating': float(driver.rating) if driver.rating else 5.0,
                        'total_deliveries': driver.total_deliveries or 0,
                        'status': safe_enum_to_string(driver.status),
                        'is_available': driver.is_available,
                        'verification_status': driver.verification_status,
                        'is_verified': driver.is_verified,
                        'intelligent_mode_enabled': driver.intelligent_mode_enabled,
                        'completed_deliveries': driver.completed_deliveries or 0,
                        'cancelled_deliveries': driver.cancelled_deliveries or 0,
                        'last_active_at': driver.last_active_at.isoformat() if driver.last_active_at else None
                    }
            
            # Calculate ETA based on status
            eta_info = self._calculate_eta(delivery)
            
            # Get status history
            status_history = self._get_status_history(delivery)
            
            # Get next available actions
            next_actions = self._get_next_actions(delivery.status, user_id, delivery.customer_id, delivery.driver_id)
            
            # Build response in expected format
            response_data = {
                'status': self._map_status_to_expected_format(delivery.status),
                'delivery': {
                    'id': delivery_id,
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'item_name': delivery.item_name,
                    'tracking_number': delivery.tracking_number,
                    'driver_id': delivery.driver_id,
                    'created_at': delivery.created_at.isoformat() if delivery.created_at else None,
                    'updated_at': delivery.updated_at.isoformat() if delivery.updated_at else None
                },
                'driver': self._format_driver_for_response(driver_info, delivery.status) if driver_info else None
            }
            
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Error getting delivery status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to get delivery status',
                'error_code': 'GET_ERROR',
                'details': str(e)
            }, 500
    
    def _get_status_description(self, status):
        """Get human-readable status description"""
        descriptions = {
            'REQUESTED': 'Delivery request created and waiting for driver assignment',
            'ASSIGNED': 'Driver has been assigned to your delivery',
            'ACCEPTED': 'Driver has accepted your delivery request',
            'PICKED_UP': 'Package has been picked up by the driver',
            'IN_TRANSIT': 'Package is on its way to the destination',
            'DELIVERED': 'Package has been successfully delivered',
            'CANCELLED': 'Delivery has been cancelled',
            'FAILED': 'Delivery failed to complete'
        }
        return descriptions.get(status, 'Unknown status')
    
    def _calculate_eta(self, delivery):
        """Calculate ETA based on delivery status"""
        if delivery.status == 'REQUESTED':
            return {
                'status': 'waiting',
                'message': 'Waiting for driver assignment',
                'estimated_minutes': None
            }
        elif delivery.status == 'ASSIGNED':
            return {
                'status': 'assigned',
                'message': 'Driver assigned - ETA 15-30 minutes',
                'estimated_minutes': 20
            }
        elif delivery.status == 'ACCEPTED':
            return {
                'status': 'accepted',
                'message': 'Driver accepted - ETA 10-20 minutes',
                'estimated_minutes': 15
            }
        elif delivery.status == 'PICKED_UP':
            return {
                'status': 'in_transit',
                'message': 'Package picked up - en route to destination',
                'estimated_minutes': delivery.estimated_duration if delivery.estimated_duration else 15
            }
        elif delivery.status == 'IN_TRANSIT':
            return {
                'status': 'in_transit',
                'message': 'Package in transit - almost there',
                'estimated_minutes': delivery.estimated_duration if delivery.estimated_duration else 10
            }
        elif delivery.status == 'DELIVERED':
            return {
                'status': 'delivered',
                'message': 'Package delivered successfully',
                'estimated_minutes': 0
            }
        elif delivery.status == 'CANCELLED':
            return {
                'status': 'cancelled',
                'message': 'Delivery cancelled',
                'estimated_minutes': None
            }
        else:
            return {
                'status': 'unknown',
                'message': 'Status unknown',
                'estimated_minutes': None
            }
    
    def _get_status_history(self, delivery):
        """Get chronological status history"""
        history = []
        
        # Always include initial request
        history.append({
            'status': 'REQUESTED',
            'timestamp': delivery.created_at.isoformat() if delivery.created_at else None,
            'description': 'Delivery request created',
            'user_type': 'customer'
        })
        
        # Add other status changes
        if delivery.assigned_time:
            history.append({
                'status': 'ASSIGNED',
                'timestamp': delivery.assigned_time.isoformat(),
                'description': 'Driver assigned to delivery',
                'user_type': 'system'
            })
        
        if delivery.accepted_time:
            history.append({
                'status': 'ACCEPTED',
                'timestamp': delivery.accepted_time.isoformat(),
                'description': 'Driver accepted delivery',
                'user_type': 'driver'
            })
        
        if delivery.pickup_time:
            history.append({
                'status': 'PICKED_UP',
                'timestamp': delivery.pickup_time.isoformat(),
                'description': 'Package picked up by driver',
                'user_type': 'driver'
            })
        
        if delivery.delivered_time:
            history.append({
                'status': 'DELIVERED',
                'timestamp': delivery.delivered_time.isoformat(),
                'description': 'Package delivered successfully',
                'user_type': 'driver'
            })
        
        if delivery.cancelled_time:
            history.append({
                'status': 'CANCELLED',
                'timestamp': delivery.cancelled_time.isoformat(),
                'description': 'Delivery cancelled',
                'user_type': 'customer'
            })
        
        return history
    
    def _get_next_actions(self, status, user_id, customer_id, driver_id):
        """Get available next actions based on current status and user role"""
        actions = []
        
        if user_id == customer_id:  # Customer actions
            if status == 'REQUESTED':
                actions.append({'action': 'cancel', 'description': 'Cancel delivery request', 'endpoint': f'/api/deliveries/{user_id}/cancel'})
            elif status == 'ASSIGNED':
                actions.append({'action': 'cancel', 'description': 'Cancel delivery request', 'endpoint': f'/api/deliveries/{user_id}/cancel'})
                actions.append({'action': 'contact_driver', 'description': 'Contact assigned driver', 'endpoint': f'/api/deliveries/{user_id}/messages'})
            elif status == 'ACCEPTED':
                actions.append({'action': 'track', 'description': 'Track delivery progress', 'endpoint': f'/api/deliveries/{user_id}/track'})
                actions.append({'action': 'contact_driver', 'description': 'Contact driver', 'endpoint': f'/api/deliveries/{user_id}/messages'})
            elif status in ['PICKED_UP', 'IN_TRANSIT']:
                actions.append({'action': 'track', 'description': 'Track delivery progress', 'endpoint': f'/api/deliveries/{user_id}/track'})
            elif status == 'DELIVERED':
                actions.append({'action': 'rate', 'description': 'Rate delivery experience', 'endpoint': f'/api/deliveries/{user_id}/rate'})
        
        elif user_id == driver_id:  # Driver actions
            if status == 'ASSIGNED':
                actions.append({'action': 'accept', 'description': 'Accept delivery assignment', 'endpoint': f'/api/deliveries/{user_id}/accept'})
                actions.append({'action': 'decline', 'description': 'Decline delivery assignment', 'endpoint': f'/api/deliveries/{user_id}/decline'})
            elif status == 'ACCEPTED':
                actions.append({'action': 'pickup', 'description': 'Mark package as picked up', 'endpoint': f'/api/deliveries/{user_id}/pickup'})
            elif status == 'PICKED_UP':
                actions.append({'action': 'start_transit', 'description': 'Start delivery transit', 'endpoint': f'/api/deliveries/{user_id}/start-transit'})
            elif status == 'IN_TRANSIT':
                actions.append({'action': 'complete', 'description': 'Mark delivery as completed', 'endpoint': f'/api/deliveries/{user_id}/complete'})
        
        return actions
    
    def _get_poll_interval(self, status):
        """Get recommended polling interval based on status"""
        intervals = {
            'REQUESTED': 30,    # 30 seconds - waiting for assignment
            'ASSIGNED': 15,     # 15 seconds - waiting for driver acceptance
            'ACCEPTED': 10,     # 10 seconds - driver accepted, waiting for pickup
            'PICKED_UP': 5,     # 5 seconds - in transit, more frequent updates
            'IN_TRANSIT': 5,    # 5 seconds - in transit, more frequent updates
            'DELIVERED': 0,     # No polling needed
            'CANCELLED': 0,     # No polling needed
            'FAILED': 0         # No polling needed
        }
        return intervals.get(status, 30)
    
    def _map_status_to_expected_format(self, status):
        """Map database status to expected API format"""
        # Convert status to string if it's an enum
        status_str = safe_enum_to_string(status)
        
        status_mapping = {
            'REQUESTED': 'confirmed',
            'pending': 'pending',
            'paid': 'paid',
            'ASSIGNED': 'assigned', 
            'ACCEPTED': 'accepted',
            'PICKED_UP': 'picked_up',
            'IN_TRANSIT': 'in_transit',
            'in_progress': 'in_progress',
            'DELIVERED': 'delivered',
            'completed': 'completed',
            'CANCELLED': 'cancelled',
            'FAILED': 'cancelled'
        }
        # Return the mapped status or the original status (lowercased) if not in mapping
        return status_mapping.get(status_str, status_str.lower() if status_str else 'pending')
    
    def _format_driver_for_response(self, driver_info, delivery_status):
        """Format driver information for the expected response format"""
        if not driver_info:
            return None
        
        # Calculate estimated arrival based on status
        estimated_arrival = self._calculate_estimated_arrival(delivery_status)
        
        return {
            'id': driver_info['id'],
            'name': driver_info['full_name'],
            'phone': driver_info['phone_number'],
            'rating': driver_info['rating'],
            'estimated_arrival': estimated_arrival,
            'vehicle_type': driver_info['vehicle_type'].lower() if driver_info['vehicle_type'] else None,
            'vehicle_make': driver_info['vehicle_make'],
            'vehicle_model': driver_info['vehicle_model']
        }
    
    def _calculate_estimated_arrival(self, status):
        """Calculate estimated arrival time based on status"""
        if status == 'REQUESTED':
            return "Waiting for assignment"
        elif status == 'ASSIGNED':
            return "15-30 minutes"
        elif status == 'ACCEPTED':
            return "10-20 minutes"
        elif status == 'PICKED_UP':
            return "5-15 minutes"
        elif status == 'IN_TRANSIT':
            return "5-10 minutes"
        elif status == 'DELIVERED':
            return "Delivered"
        elif status == 'CANCELLED':
            return "Cancelled"
        else:
            return "Unknown"

@delivery_api.route('/<int:delivery_id>/status/public')
class PublicDeliveryStatusPolling(Resource):
    """Public delivery status polling (no auth required) - for tracking by tracking number"""
    @delivery_api.response(200, 'Delivery status retrieved successfully')
    @delivery_api.response(404, 'Delivery not found')
    def get(self, delivery_id):
        """Get delivery status publicly (no authentication required)"""
        try:
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {
                    'success': False,
                    'error': 'Delivery not found',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Get driver information if assigned (limited info for public access)
            driver_info = None
            if delivery.driver_id:
                driver = Driver.query.get(delivery.driver_id)
                if driver:
                    driver_info = {
                        'id': driver.id,
                        'first_name': driver.first_name,
                        'last_name': driver.last_name,
                        'full_name': driver.get_full_name(),
                        'vehicle_type': safe_enum_to_string(driver.vehicle_type),
                        'vehicle_make': driver.vehicle_make,
                        'vehicle_model': driver.vehicle_model,
                        'vehicle_year': driver.vehicle_year,
                        'vehicle_plate_number': driver.vehicle_plate_number,
                        'rating': float(driver.rating) if driver.rating else 5.0,
                        'total_deliveries': driver.total_deliveries or 0,
                        'verification_status': driver.verification_status,
                        'is_verified': driver.is_verified
                        # Note: No phone, email, or location data for privacy
                    }
            
            # Calculate ETA based on status
            eta_info = self._calculate_eta_public(delivery)
            
            # Get status history (simplified for public access)
            status_history = self._get_status_history_public(delivery)
            
            # Build response in expected format (public access)
            response_data = {
                'status': self._map_status_to_expected_format(delivery.status),
                'delivery': {
                    'id': delivery_id,
                    'pickup_address': delivery.pickup_address,
                    'dropoff_address': delivery.dropoff_address,
                    'item_name': delivery.item_name,
                    'tracking_number': delivery.tracking_number,
                    'driver_id': delivery.driver_id,
                    'created_at': delivery.created_at.isoformat() if delivery.created_at else None,
                    'updated_at': delivery.updated_at.isoformat() if delivery.updated_at else None
                },
                'driver': self._format_driver_for_response_public(driver_info, delivery.status) if driver_info else None
            }
            
            return response_data, 200
            
        except Exception as e:
            logger.error(f"Error getting public delivery status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to get delivery status',
                'error_code': 'GET_ERROR',
                'details': str(e)
            }, 500
    
    def _calculate_eta_public(self, delivery):
        """Calculate ETA for public access (simplified)"""
        if delivery.status == 'REQUESTED':
            return {
                'status': 'waiting',
                'message': 'Waiting for driver assignment',
                'estimated_minutes': None
            }
        elif delivery.status == 'ASSIGNED':
            return {
                'status': 'assigned',
                'message': 'Driver assigned - ETA 15-30 minutes',
                'estimated_minutes': 20
            }
        elif delivery.status == 'ACCEPTED':
            return {
                'status': 'accepted',
                'message': 'Driver accepted - ETA 10-20 minutes',
                'estimated_minutes': 15
            }
        elif delivery.status == 'PICKED_UP':
            return {
                'status': 'in_transit',
                'message': 'Package picked up - en route to destination',
                'estimated_minutes': delivery.estimated_duration if delivery.estimated_duration else 15
            }
        elif delivery.status == 'IN_TRANSIT':
            return {
                'status': 'in_transit',
                'message': 'Package in transit - almost there',
                'estimated_minutes': delivery.estimated_duration if delivery.estimated_duration else 10
            }
        elif delivery.status == 'DELIVERED':
            return {
                'status': 'delivered',
                'message': 'Package delivered successfully',
                'estimated_minutes': 0
            }
        elif delivery.status == 'CANCELLED':
            return {
                'status': 'cancelled',
                'message': 'Delivery cancelled',
                'estimated_minutes': None
            }
        else:
            return {
                'status': 'unknown',
                'message': 'Status unknown',
                'estimated_minutes': None
            }
    
    def _get_status_history_public(self, delivery):
        """Get status history for public access (simplified)"""
        history = []
        
        # Always include initial request
        history.append({
            'status': 'REQUESTED',
            'timestamp': delivery.created_at.isoformat() if delivery.created_at else None,
            'description': 'Delivery request created'
        })
        
        # Add other status changes
        if delivery.assigned_time:
            history.append({
                'status': 'ASSIGNED',
                'timestamp': delivery.assigned_time.isoformat(),
                'description': 'Driver assigned to delivery'
            })
        
        if delivery.accepted_time:
            history.append({
                'status': 'ACCEPTED',
                'timestamp': delivery.accepted_time.isoformat(),
                'description': 'Driver accepted delivery'
            })
        
        if delivery.pickup_time:
            history.append({
                'status': 'PICKED_UP',
                'timestamp': delivery.pickup_time.isoformat(),
                'description': 'Package picked up by driver'
            })
        
        if delivery.delivered_time:
            history.append({
                'status': 'DELIVERED',
                'timestamp': delivery.delivered_time.isoformat(),
                'description': 'Package delivered successfully'
            })
        
        if delivery.cancelled_time:
            history.append({
                'status': 'CANCELLED',
                'timestamp': delivery.cancelled_time.isoformat(),
                'description': 'Delivery cancelled'
            })
        
        return history
    
    def _format_driver_for_response_public(self, driver_info, delivery_status):
        """Format driver information for public response (limited info for privacy)"""
        if not driver_info:
            return None
        
        # Calculate estimated arrival based on status
        estimated_arrival = self._calculate_estimated_arrival(delivery_status)
        
        return {
            'id': driver_info['id'],
            'name': driver_info['full_name'],
            'phone': None,  # No phone for privacy in public endpoint
            'rating': driver_info['rating'],
            'estimated_arrival': estimated_arrival,
            'vehicle_type': driver_info['vehicle_type'].lower() if driver_info['vehicle_type'] else None,
            'vehicle_make': driver_info['vehicle_make'],
            'vehicle_model': driver_info['vehicle_model']
        }

@delivery_api.route('/item-photo/test-view/<int:delivery_id>')
class TestViewItemPhoto(Resource):
    """Test item photo viewing functionality - NO AUTH REQUIRED"""
    @delivery_api.response(200, 'Test item photo URL generated successfully')
    @delivery_api.response(404, 'Delivery not found or no photo available')
    def get(self, delivery_id):
        """Test item photo viewing functionality"""
        try:
            # Verify delivery exists
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return {
                    'success': False,
                    'error': 'Delivery not found',
                    'delivery_id': delivery_id
                }, 404
            
            # Check if delivery has an item photo
            if not delivery.item_photo_url:
                return {
                    'success': False,
                    'error': 'No item photo available for this delivery',
                    'delivery_id': delivery_id,
                    'item_photo_url': None
                }, 404
            
            # Get signed download URL
            download_url = get_storage_service().get_download_url(
                object_key=delivery.item_photo_url,
                expires_seconds=3600  # 1 hour
            )
            
            logger.info(f"Test item photo view URL generated for delivery {delivery_id}")
            
            return {
                'success': True,
                'message': 'Test item photo view URL generated successfully',
                'delivery_id': delivery_id,
                'item_photo_url': delivery.item_photo_url,
                'download_url': download_url,
                'expires_in': 3600,
                'view_endpoints': {
                    'authenticated': f'/api/deliveries/item-photo/{delivery_id}',
                    'public': f'/api/deliveries/item-photo/{delivery_id}/public',
                    'direct_view': f'/api/deliveries/item-photo/{delivery_id}/view',
                    'note': 'direct_view redirects directly to the image'
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Error generating test item photo view URL: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Failed to generate test view URL',
                'error_code': 'TEST_ERROR',
                'details': str(e)
            }, 500