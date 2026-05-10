from flask_restx import Namespace, Resource, fields, api
from utils.firebase_auth_middleware import firebase_customer_required
from services.pricing_service import PricingService
from models.user import Customer, Driver
from models.delivery import Delivery
from models.ride import Ride
from extensions import db

# Initialize namespace
pricing_api = Namespace('pricing', description='Pricing and fare calculation operations')

# Initialize pricing service
pricing_service = PricingService()

# Request/Response models
pricing_request = pricing_api.model('PricingRequest', {
    'pickup_latitude': fields.Float(required=True, description='Pickup latitude'),
    'pickup_longitude': fields.Float(required=True, description='Pickup longitude'),
    'dropoff_latitude': fields.Float(required=True, description='Dropoff latitude'),
    'dropoff_longitude': fields.Float(required=True, description='Dropoff longitude'),
    'vehicle_type': fields.String(required=True, description='Vehicle type (car, bike, truck)'),
    'service_type': fields.String(required=True, description='Service type (ride, delivery)'),
    'distance': fields.Float(description='Distance in kilometers'),
    'duration': fields.Float(description='Duration in minutes'),
    'surge_multiplier': fields.Float(description='Surge pricing multiplier'),
    'base_fare': fields.Float(description='Base fare amount'),
    'per_km_rate': fields.Float(description='Rate per kilometer'),
    'per_minute_rate': fields.Float(description='Rate per minute'),
    'service_fee': fields.Float(description='Service fee percentage'),
    'tax_rate': fields.Float(description='Tax rate percentage')
})

pricing_response = pricing_api.model('PricingResponse', {
    'estimated_fare': fields.Float(description='Estimated total fare'),
    'base_fare': fields.Float(description='Base fare amount'),
    'distance_fare': fields.Float(description='Distance-based fare'),
    'time_fare': fields.Float(description='Time-based fare'),
    'surge_fare': fields.Float(description='Surge pricing amount'),
    'service_fee': fields.Float(description='Service fee amount'),
    'tax_amount': fields.Float(description='Tax amount'),
    'total_fare': fields.Float(description='Total fare including all charges'),
    'currency': fields.String(description='Currency code'),
    'estimated_duration': fields.Float(description='Estimated trip duration in minutes'),
    'estimated_distance': fields.Float(description='Estimated distance in kilometers'),
    'surge_multiplier': fields.Float(description='Current surge multiplier'),
    'pricing_breakdown': fields.Raw(description='Detailed pricing breakdown')
})

@pricing_api.route('/calculate-fare')
class FareCalculation(Resource):
    @pricing_api.doc('calculate_fare')
    @pricing_api.expect(pricing_request)
    @pricing_api.marshal_with(pricing_response, code=200)
    def post(self):
        """Calculate estimated fare for a trip or delivery"""
        try:
            data = pricing_api.payload
            
            # Extract pricing parameters
            pickup_coords = (data['pickup_latitude'], data['pickup_longitude'])
            dropoff_coords = (data['dropoff_latitude'], data['dropoff_longitude'])
            vehicle_type = data.get('vehicle_type', 'car')
            service_type = data.get('service_type', 'ride')
            
            # Calculate fare using pricing service
            fare_details = pricing_service.calculate_fare(
                pickup_coords=pickup_coords,
                dropoff_coords=dropoff_coords,
                vehicle_type=vehicle_type,
                service_type=service_type,
                distance=data.get('distance'),
                duration=data.get('duration'),
                surge_multiplier=data.get('surge_multiplier', 1.0)
            )
            
            return fare_details, 200
            
        except Exception as e:
            pricing_api.abort(400, f"Error calculating fare: {str(e)}")

@pricing_api.route('/surge-pricing')
class SurgePricing(Resource):
    @pricing_api.doc('get_surge_pricing', security='Bearer Auth')
    @firebase_customer_required
    def get(self):
        """Get current surge pricing information for different areas"""
        try:
            surge_data = pricing_service.get_surge_pricing()
            return surge_data, 200
        except Exception as e:
            pricing_api.abort(400, f"Error getting surge pricing: {str(e)}")

@pricing_api.route('/pricing-zones')
class PricingZones(Resource):
    @pricing_api.doc('get_pricing_zones', security='Bearer Auth')
    @firebase_customer_required
    def get(self):
        """Get pricing zones and their base rates"""
        try:
            zones = pricing_service.get_pricing_zones()
            return zones, 200
        except Exception as e:
            pricing_api.abort(400, f"Error getting pricing zones: {str(e)}")

@pricing_api.route('/vehicle-rates')
class VehicleRates(Resource):
    @pricing_api.doc('get_vehicle_rates', security='Bearer Auth')
    def get(self):
        """Get base rates for different vehicle types"""
        try:
            rates = pricing_service.get_vehicle_rates()
            return rates, 200
        except Exception as e:
            pricing_api.abort(400, f"Error getting vehicle rates: {str(e)}")

@pricing_api.route('/service-fees')
class ServiceFees(Resource):
    @pricing_api.doc('get_service_fees', security='Bearer Auth')
    def get(self):
        """Get service fees and commission rates"""
        try:
            fees = pricing_service.get_service_fees()
            return fees, 200
        except Exception as e:
            pricing_api.abort(400, f"Error getting service fees: {str(e)}")
