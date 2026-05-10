#!/usr/bin/env python3
"""
Mobile Payment Routes for DeliverMe
Optimized for mobile app usage with:
- Streamlined endpoints
- Faster response times
- Mobile-friendly error handling
- Offline capability support
- Battery optimization
"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.stripe_payment_service import stripe_payment_service
from services.payment_service import payment_service
from services.maps_service import maps_service
from models.delivery import Delivery, DeliveryStatus
from models.payment import Payment, PaymentType, PaymentStatus, PaymentMethod, PaymentDirection
from models.user import Customer, Driver
from extensions import db
from datetime import datetime
import logging
import json
import stripe
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- helpers ----
def _to_coords(lat, lng) -> Optional[Tuple[float, float]]:
    """Convert DB numeric coords to float tuple."""
    if lat is None or lng is None:
        return None
    try:
        return (float(lat), float(lng))
    except Exception:
        return None


def ensure_delivery_estimated_distance_km(delivery: Delivery) -> Optional[float]:
    """
    Ensure delivery.estimated_distance_km exists.
    - If missing, compute from stored coords/addresses (Google Maps or Haversine fallback)
      and persist it so pricing/payment flows can proceed.
    """
    try:
        if delivery.estimated_distance_km is not None:
            return float(delivery.estimated_distance_km)
    except Exception:
        # If the stored value is not castable, treat it as missing and recompute
        pass
    
    origin_coords = _to_coords(delivery.pickup_latitude, delivery.pickup_longitude)
    destination_coords = _to_coords(delivery.dropoff_latitude, delivery.dropoff_longitude)
    
    route_info = maps_service.calculate_distance_and_duration(
        origin_address=delivery.pickup_address,
        destination_address=delivery.dropoff_address,
        origin_coords=origin_coords,
        destination_coords=destination_coords
    )
    
    distance_km = route_info.get('distance_km') if isinstance(route_info, dict) else None
    duration_minutes = route_info.get('duration_minutes') if isinstance(route_info, dict) else None
    
    if distance_km is None:
        return None
    
    # Persist so future pricing/payment requests are consistent
    delivery.estimated_distance_km = float(distance_km)
    if duration_minutes is not None and not delivery.estimated_duration:
        try:
            delivery.estimated_duration = int(duration_minutes)
        except Exception:
            pass
    db.session.commit()
    
    return float(delivery.estimated_distance_km)


# Create namespace for mobile payments
mobile_payment_api = Namespace('mobile-payments', description='Mobile-optimized payment operations')

# Mobile-optimized models for Swagger documentation
mobile_payment_intent_model = mobile_payment_api.model('MobilePaymentIntent', {
    'delivery_id': fields.Integer(required=True, description='Delivery ID'),
    'amount': fields.Integer(required=True, description='Payment amount in cents'),
    'tip_amount': fields.Integer(description='Tip amount in cents', default=0),
    'currency': fields.String(description='Currency code', default='usd'),
    'save_payment_method': fields.Boolean(description='Save payment method for future use', default=False)
})

mobile_payment_confirm_model = mobile_payment_api.model('MobilePaymentConfirm', {
    'payment_intent_id': fields.String(required=True, description='Stripe payment intent ID'),
    'payment_method_id': fields.String(required=True, description='Stripe payment method ID')
})

mobile_payment_status_model = mobile_payment_api.model('MobilePaymentStatus', {
    'payment_id': fields.String(required=True, description='Payment ID to check')
})

# Mobile response models
mobile_payment_response_model = mobile_payment_api.model('MobilePaymentResponse', {
    'success': fields.Boolean(description='Operation success'),
    'payment_intent_id': fields.String(description='Stripe payment intent ID'),
    'client_secret': fields.String(description='Client secret for Stripe'),
    'amount': fields.Integer(description='Payment amount in cents'),
    'payment_id': fields.String(description='Internal payment ID'),
    'delivery_id': fields.Integer(description='Delivery ID'),
    'fee_breakdown': fields.Raw(description='Fee breakdown details'),
    'estimated_completion_time': fields.String(description='Estimated completion time in seconds')
})

@mobile_payment_api.route('/create-payment-intent')
class CreatePaymentIntent(Resource):
    """Create payment intents for mobile payments"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.expect(mobile_payment_intent_model)
    @mobile_payment_api.response(201, 'Payment intent created successfully', mobile_payment_response_model)
    @mobile_payment_api.response(400, 'Validation Error')
    @mobile_payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Create payment intent for mobile payments"""
        try:
            start_time = datetime.now()
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            # Input validation
            required_fields = ['delivery_id', 'amount']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'error_code': 'MISSING_FIELD'
                    }, 400
            
            delivery_id = data['delivery_id']
            amount = data['amount']  # Already in cents
            tip_amount = data.get('tip_amount', 0)
            currency = data.get('currency', 'usd').lower()
            save_payment_method = data.get('save_payment_method', False)
            
            # Validate amount
            if amount < 50:  # Minimum $0.50
                return {
                    'success': False,
                    'error': 'Amount too small (minimum $0.50)',
                    'error_code': 'AMOUNT_TOO_SMALL'
                }, 400
            
            # Verify delivery exists and belongs to customer
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                logger.error(f"Delivery {delivery_id} not found for customer {customer_id}")
                return {
                    'success': False,
                    'error': f'Delivery {delivery_id} not found or access denied',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Get customer info
            customer = Customer.query.get(customer_id)
            if not customer:
                return {
                    'success': False,
                    'error': 'Customer not found',
                    'error_code': 'CUSTOMER_NOT_FOUND'
                }, 404
            
            # Create or get Stripe customer
            stripe_customer_id = customer.stripe_customer_id
            if not stripe_customer_id:
                stripe_result = stripe_payment_service.create_customer(
                    email=customer.email,
                    name=f"{customer.first_name} {customer.last_name}",
                    phone=customer.phone_number,
                    metadata={'mobile_customer': 'true', 'customer_id': str(customer_id)}
                )
                
                if stripe_result['success']:
                    stripe_customer_id = stripe_result['customer_id']
                    customer.stripe_customer_id = stripe_customer_id
                    db.session.commit()
                else:
                    return {
                        'success': False,
                        'error': 'Failed to initialize payment customer',
                        'error_code': 'STRIPE_CUSTOMER_ERROR'
                    }, 500
            
            # Ensure delivery distance exists (older deliveries or some creation paths may not have it)
            distance_km = ensure_delivery_estimated_distance_km(delivery)
            if not distance_km:
                # Last-resort fallback: avoid blocking checkout; still log loudly
                distance_km = 8.5
                logger.warning(
                    f"Delivery {delivery_id} missing estimated_distance_km and map calc failed; using fallback {distance_km} km"
                )
                delivery.estimated_distance_km = distance_km
                db.session.commit()
            
            # Calculate cost breakdown using pricing service
            cost_breakdown = payment_service.calculate_delivery_cost_with_pricing(
                distance_km=float(distance_km),
                vehicle_type=delivery.vehicle_type or 'car'
            )
            
            # Calculate payment breakdown with actual delivery cost
            breakdown = payment_service.calculate_delivery_payment_breakdown(
                base_amount=cost_breakdown['base_delivery_cost'],
                tip_amount=tip_amount / 100.0,
                currency=currency.upper()
            )
            
            # Create Stripe payment intent
            metadata = {
                'delivery_id': str(delivery_id),
                'customer_id': str(customer_id),
                'customer_email': customer.email,
                'mobile_payment': 'true',
                'tip_amount': str(tip_amount),
                'platform_fee': str(breakdown['platform_fee_cents']),
                'payment_processing_fee': str(int(breakdown['payment_processing_fee'] * 100))
            }
            
            payment_intent_result = stripe_payment_service.create_payment_intent(
                amount=breakdown['total_amount_cents'],
                currency=currency,
                customer_id=stripe_customer_id,
                metadata=metadata
            )
            
            if not payment_intent_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to create payment intent',
                    'error_code': 'STRIPE_INTENT_ERROR',
                    'details': payment_intent_result.get('error')
                }, 500
            
            # If the Stripe customer was missing (test vs live mismatch / deleted), the service may have
            # recreated it and returned an updated customer id. Persist it so future calls don't fail.
            updated_customer_id = payment_intent_result.get('customer_id')
            if updated_customer_id and updated_customer_id != stripe_customer_id:
                stripe_customer_id = updated_customer_id
                customer.stripe_customer_id = updated_customer_id
                db.session.commit()
            
            # Create payment record
            payment = Payment(
                payment_type=PaymentType.DELIVERY_FEE,
                amount=breakdown['total_amount'],
                currency=currency.upper(),
                status=PaymentStatus.PENDING,
                direction=PaymentDirection.INBOUND,
                payer_id=customer_id,
                payer_type='customer',
                payer_stripe_id=stripe_customer_id,
                receiver_type='platform',
                payment_method=PaymentMethod.CREDIT_CARD,
                stripe_payment_intent_id=payment_intent_result['payment_intent_id'],
                delivery_id=delivery_id,
                base_amount=breakdown['base_amount'],
                platform_fee=breakdown['platform_fee'],
                payment_processing_fee=breakdown['payment_processing_fee'],
                driver_payout=breakdown['driver_payout'],
                tip_amount=breakdown['tip_amount'],
                description=f"Mobile delivery payment for delivery {delivery_id}",
                payment_metadata={
                    'mobile_payment': True,
                    'save_payment_method': save_payment_method,
                    'creation_time': start_time.isoformat()
                }
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Calculate response time
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Response
            response = {
                'success': True,
                'payment_intent_id': payment_intent_result['payment_intent_id'],
                'client_secret': payment_intent_result['client_secret'],
                'amount': breakdown['total_amount_cents'],
                'payment_id': payment.payment_id,
                'delivery_id': delivery_id,
                'fee_breakdown': {
                    'base_amount': breakdown['base_amount'],
                    'tip_amount': breakdown['tip_amount'],
                    'platform_fee': breakdown['platform_fee'],
                    'payment_processing_fee': breakdown['payment_processing_fee'],
                    'total_amount': breakdown['total_amount'],
                    'driver_earnings': breakdown['driver_payout']
                },
                'estimated_completion_time': '2-3',  # seconds
                'response_time_ms': int(response_time * 1000)
            }
            
            logger.info(f"Payment intent created in {response_time:.3f}s for delivery {delivery_id}")
            return response, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Payment intent creation failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Payment system error: {str(e)}',
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 30  # seconds
            }, 500

@mobile_payment_api.route('/quick-payment-intent')
class MobileQuickPaymentIntent(Resource):
    """Ultra-fast payment intent creation for mobile apps"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.expect(mobile_payment_intent_model)
    @mobile_payment_api.response(201, 'Payment intent created successfully', mobile_payment_response_model)
    @mobile_payment_api.response(400, 'Validation Error')
    @mobile_payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Create payment intent optimized for mobile with minimal latency"""
        try:
            start_time = datetime.now()
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            # Input validation
            required_fields = ['delivery_id', 'amount']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'error_code': 'MISSING_FIELD'
                    }, 400
            
            delivery_id = data['delivery_id']
            amount = data['amount']  # Already in cents
            tip_amount = data.get('tip_amount', 0)
            currency = data.get('currency', 'usd').lower()
            save_payment_method = data.get('save_payment_method', False)
            
            # Validate amount
            if amount < 50:  # Minimum $0.50
                return {
                    'success': False,
                    'error': 'Amount too small (minimum $0.50)',
                    'error_code': 'AMOUNT_TOO_SMALL'
                }, 400
            
            # Verify delivery exists and belongs to customer
            delivery = Delivery.query.filter_by(id=delivery_id, customer_id=customer_id).first()
            if not delivery:
                logger.error(f"Delivery {delivery_id} not found for customer {customer_id}")
                return {
                    'success': False,
                    'error': f'Delivery {delivery_id} not found or access denied',
                    'error_code': 'DELIVERY_NOT_FOUND'
                }, 404
            
            # Get customer info (cached for mobile performance)
            customer = Customer.query.get(customer_id)
            if not customer:
                return {
                    'success': False,
                    'error': 'Customer not found',
                    'error_code': 'CUSTOMER_NOT_FOUND'
                }, 404
            
            # Create or get Stripe customer (optimized)
            stripe_customer_id = customer.stripe_customer_id
            if not stripe_customer_id:
                stripe_result = stripe_payment_service.create_customer(
                    email=customer.email,
                    name=f"{customer.first_name} {customer.last_name}",
                    phone=customer.phone_number,
                    metadata={'mobile_customer': 'true', 'customer_id': str(customer_id)}
                )
                
                if stripe_result['success']:
                    stripe_customer_id = stripe_result['customer_id']
                    customer.stripe_customer_id = stripe_customer_id
                    db.session.commit()
                else:
                    return {
                        'success': False,
                        'error': 'Failed to initialize payment customer',
                        'error_code': 'STRIPE_CUSTOMER_ERROR'
                    }, 500
            
            # Ensure delivery distance exists (older deliveries or some creation paths may not have it)
            distance_km = ensure_delivery_estimated_distance_km(delivery)
            if not distance_km:
                # Last-resort fallback: avoid blocking checkout; still log loudly
                distance_km = 8.5
                logger.warning(
                    f"Delivery {delivery_id} missing estimated_distance_km and map calc failed; using fallback {distance_km} km"
                )
                delivery.estimated_distance_km = distance_km
                db.session.commit()
            
            # Calculate cost breakdown using pricing service
            cost_breakdown = payment_service.calculate_delivery_cost_with_pricing(
                distance_km=float(distance_km),
                vehicle_type=delivery.vehicle_type or 'car'
            )
            
            # Calculate payment breakdown with actual delivery cost
            breakdown = payment_service.calculate_delivery_payment_breakdown(
                base_amount=cost_breakdown['base_delivery_cost'],
                tip_amount=tip_amount / 100.0,
                currency=currency.upper()
            )
            
            # Create Stripe payment intent with mobile optimizations
            metadata = {
                'delivery_id': str(delivery_id),
                'customer_id': str(customer_id),
                'customer_email': customer.email,
                'mobile_payment': 'true',
                'tip_amount': str(tip_amount),
                'platform_fee': str(breakdown['platform_fee_cents']),
                'payment_processing_fee': str(int(breakdown['payment_processing_fee'] * 100))
            }
            
            payment_intent_result = stripe_payment_service.create_payment_intent(
                amount=breakdown['total_amount_cents'],
                currency=currency,
                customer_id=stripe_customer_id,
                metadata=metadata
            )
            
            if not payment_intent_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to create payment intent',
                    'error_code': 'STRIPE_INTENT_ERROR',
                    'details': payment_intent_result.get('error')
                }, 500
            
            # If Stripe reports the stored customer is missing (often test-vs-live mismatch),
            # the service may recreate it and return a new customer id. Persist it.
            updated_customer_id = payment_intent_result.get('customer_id')
            if updated_customer_id and updated_customer_id != stripe_customer_id:
                stripe_customer_id = updated_customer_id
                customer.stripe_customer_id = updated_customer_id
                db.session.commit()
            
            # Create payment record
            payment = Payment(
                payment_type=PaymentType.DELIVERY_FEE,
                amount=breakdown['total_amount'],
                currency=currency.upper(),
                status=PaymentStatus.PENDING,
                direction=PaymentDirection.INBOUND,
                payer_id=customer_id,
                payer_type='customer',
                payer_stripe_id=stripe_customer_id,
                receiver_type='platform',
                payment_method=PaymentMethod.CREDIT_CARD,
                stripe_payment_intent_id=payment_intent_result['payment_intent_id'],
                delivery_id=delivery_id,
                base_amount=breakdown['base_amount'],
                platform_fee=breakdown['platform_fee'],
                payment_processing_fee=breakdown['payment_processing_fee'],
                driver_payout=breakdown['driver_payout'],
                tip_amount=breakdown['tip_amount'],
                description=f"Mobile delivery payment for delivery {delivery_id}",
                payment_metadata={
                    'mobile_payment': True,
                    'save_payment_method': save_payment_method,
                    'creation_time': start_time.isoformat()
                }
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Calculate response time for mobile optimization tracking
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Mobile-optimized response with payment page redirect
            response = {
                'success': True,
                'payment_intent_id': payment_intent_result['payment_intent_id'],
                'client_secret': payment_intent_result['client_secret'],
                'amount': breakdown['total_amount_cents'],
                'payment_id': payment.payment_id,
                'delivery_id': delivery_id,
                'fee_breakdown': {
                    'base_amount': breakdown['base_amount'],
                    'tip_amount': breakdown['tip_amount'],
                    'platform_fee': breakdown['platform_fee'],
                    'payment_processing_fee': breakdown['payment_processing_fee'],
                    'total_amount': breakdown['total_amount'],
                    'driver_earnings': breakdown['driver_payout']
                },
                'payment_page': {
                    'url': f'/payment/{payment.payment_id}',
                    'stripe_checkout_url': f'https://checkout.stripe.com/pay/{payment_intent_result["payment_intent_id"]}',
                    'redirect_required': True,
                    'payment_method': 'stripe'
                },
                'estimated_completion_time': '2-3',  # seconds
                'response_time_ms': int(response_time * 1000)
            }
            
            logger.info(f"Mobile payment intent created in {response_time:.3f}s for delivery {delivery_id}")
            return response, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Mobile payment intent creation failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Payment system error: {str(e)}',
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 30  # seconds
            }, 500

@mobile_payment_api.route('/confirm-payment')
class MobileConfirmPayment(Resource):
    """Mobile-optimized payment confirmation"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.expect(mobile_payment_confirm_model)
    @mobile_payment_api.response(200, 'Payment confirmed successfully')
    @mobile_payment_api.response(400, 'Validation Error')
    @mobile_payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Confirm payment with mobile-specific optimizations"""
        try:
            start_time = datetime.now()
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            payment_intent_id = data.get('payment_intent_id')
            payment_method_id = data.get('payment_method_id')
            
            if not payment_intent_id or not payment_method_id:
                return {
                    'success': False,
                    'error': 'Missing payment intent ID or payment method ID',
                    'error_code': 'MISSING_PARAMETERS'
                }, 400
            
            # Get payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent_id,
                payer_id=customer_id
            ).first()
            
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found or access denied',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Confirm with Stripe
            confirm_result = stripe_payment_service.confirm_payment_intent(
                payment_intent_id=payment_intent_id,
                payment_method_id=payment_method_id
            )
            
            if not confirm_result['success']:
                return {
                    'success': False,
                    'error': 'Payment confirmation failed',
                    'error_code': 'STRIPE_CONFIRM_ERROR',
                    'details': confirm_result.get('error')
                }, 400
            
            # Update payment record
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            payment.payment_method_id = payment_method_id
            
            # Update delivery payment status
            if payment.delivery_id:
                delivery = Delivery.query.get(payment.delivery_id)
                if delivery:
                    delivery.payment_status = 'completed'
                    delivery.payment_completed_at = datetime.utcnow()
                    delivery.actual_cost = payment.amount
                    # Delivery.status is an Enum column; assign the Enum value
                    delivery.status = DeliveryStatus.ASSIGNED  # move delivery into driver-visible queue
            
            db.session.commit()
            
            # Process driver transfer if delivery has a driver
            transfer_result = None
            if payment.delivery_id:
                delivery = Delivery.query.get(payment.delivery_id)
                if delivery and delivery.driver_id:
                    # Get driver's Stripe account
                    driver = Driver.query.get(delivery.driver_id)
                    if driver and driver.stripe_account_id:
                        # Calculate driver amount from payment record
                        driver_amount_cents = int(payment.driver_payout * 100)  # driver_payout is in dollars
                        platform_fee_cents = int(payment.platform_fee * 100)  # platform_fee is in dollars
                        
                        # Process transfer
                        transfer_result = stripe_payment_service.process_delivery_payment_with_transfer(
                            payment_intent_id=payment_intent_id,
                            driver_stripe_account_id=driver.stripe_account_id,
                            driver_amount_cents=driver_amount_cents,
                            platform_fee_cents=platform_fee_cents,
                            currency=payment.currency,
                            delivery_id=str(payment.delivery_id)
                        )
                        
                        if transfer_result['success']:
                            logger.info(f"Driver transfer completed: {transfer_result['transfer_id']}")
                        else:
                            logger.error(f"Driver transfer failed: {transfer_result.get('error')}")
            
            # Calculate response time
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Mobile-optimized response
            response = {
                'success': True,
                'payment_id': payment.payment_id,
                'delivery_id': payment.delivery_id,
                'amount': payment.amount,
                'status': 'completed',
                'completion_time': payment.completed_at.isoformat(),
                'response_time_ms': int(response_time * 1000),
                'next_steps': {
                    'track_delivery': f'/deliveries/{payment.delivery_id}/track',
                    'receipt': f'/payments/{payment.payment_id}/receipt'
                }
            }
            
            logger.info(f"Mobile payment confirmed in {response_time:.3f}s for payment {payment.payment_id}")
            return response, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Mobile payment confirmation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment confirmation failed',
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 10
            }, 500

@mobile_payment_api.route('/status/<string:payment_id>')
class MobilePaymentStatus(Resource):
    """Ultra-fast payment status check for mobile"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.response(200, 'Payment status retrieved')
    @mobile_payment_api.response(404, 'Payment not found')
    @jwt_required()
    def get(self, payment_id):
        """Get payment status optimized for mobile polling"""
        try:
            customer_id = get_jwt_identity()
            
            # Fast lookup with minimal data
            payment = Payment.query.filter_by(
                payment_id=payment_id,
                payer_id=customer_id
            ).first()
            
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Mobile-optimized minimal response
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'status': payment.status.value,
                'amount': payment.amount,
                'delivery_id': payment.delivery_id,
                'created_at': payment.created_at.isoformat(),
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'is_complete': payment.status == PaymentStatus.COMPLETED
            }, 200
            
        except Exception as e:
            logger.error(f"Mobile payment status check failed: {str(e)}")
            return {
                'success': False,
                'error': 'Status check failed',
                'error_code': 'SYSTEM_ERROR'
            }, 500

@mobile_payment_api.route('/delivery-cost-estimate')
class MobileDeliveryCostEstimate(Resource):
    """Fast delivery cost estimation for mobile"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.response(200, 'Cost estimated successfully')
    @jwt_required()
    def post(self):
        """Get delivery cost estimate optimized for mobile"""
        try:
            data = request.get_json()
            
            distance_km = data.get('distance_km')
            vehicle_type = data.get('vehicle_type', 'car')
            tip_amount = data.get('tip_amount', 0)
            
            if not distance_km:
                return {
                    'success': False,
                    'error': 'Distance required',
                    'error_code': 'MISSING_DISTANCE'
                }, 400
            
            # Calculate cost breakdown
            cost_breakdown = payment_service.calculate_delivery_cost_with_pricing(
                distance_km=distance_km,
                vehicle_type=vehicle_type
            )
            
            # Add tip to the calculation
            if tip_amount > 0:
                cost_breakdown['tip_amount'] = tip_amount
                cost_breakdown['driver_earnings'] += tip_amount
                cost_breakdown['total_cost'] += tip_amount
            
            # Mobile-friendly response
            return {
                'success': True,
                'estimate': {
                    'base_cost': cost_breakdown['base_delivery_cost'],
                    'platform_fee': cost_breakdown['platform_fee'],
                    'payment_fee': cost_breakdown['payment_processing_fee'],
                    'tip_amount': tip_amount,
                    'total_cost': cost_breakdown['total_cost'] + tip_amount,
                    'driver_earnings': cost_breakdown['driver_earnings'] + tip_amount,
                    'vehicle_type': vehicle_type,
                    'distance_km': distance_km
                },
                'currency': 'USD',
                'valid_for_minutes': 10  # Estimate validity
            }, 200
            
        except Exception as e:
            logger.error(f"Mobile cost estimation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Cost estimation failed',
                'error_code': 'ESTIMATION_ERROR'
            }, 500

# Payment method models - Note: Card details should be handled client-side with Stripe Elements
mobile_attach_payment_method_model = mobile_payment_api.model('AttachPaymentMethod', {
    'payment_method_id': fields.String(required=True, description='Stripe payment method ID created client-side'),
    'customer_id': fields.String(description='Stripe customer ID')
})

mobile_payment_method_response_model = mobile_payment_api.model('PaymentMethodResponse', {
    'success': fields.Boolean(description='Operation success'),
    'payment_method_id': fields.String(description='Stripe payment method ID'),
    'type': fields.String(description='Payment method type'),
    'card': fields.Raw(description='Card details'),
    'customer_id': fields.String(description='Stripe customer ID')
})

@mobile_payment_api.route('/payment-methods')
class MobilePaymentMethods(Resource):
    """Manage saved payment methods for mobile"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.response(200, 'Payment methods retrieved')
    @jwt_required()
    def get(self):
        """Get saved payment methods for mobile app"""
        try:
            customer_id = get_jwt_identity()
            customer = Customer.query.get(customer_id)
            
            if not customer or not customer.stripe_customer_id:
                return {
                    'success': True,
                    'payment_methods': [],
                    'count': 0
                }, 200
            
            # Get payment methods from Stripe
            methods_result = stripe_payment_service.get_payment_methods(customer.stripe_customer_id)
            
            if methods_result['success']:
                methods = methods_result['payment_methods']
                # Mobile-optimized response
                mobile_methods = []
                for method in methods:
                    if method.get('card'):
                        card = method['card']
                        mobile_methods.append({
                            'id': method['id'],
                            'type': 'card',
                            'brand': card['brand'],
                            'last4': card['last4'],
                            'exp_month': card['exp_month'],
                            'exp_year': card['exp_year'],
                            'display_name': f"{card['brand'].upper()} •••• {card['last4']}"
                        })
                
                return {
                    'success': True,
                    'payment_methods': mobile_methods,
                    'count': len(mobile_methods)
                }, 200
            else:
                return {
                    'success': True,
                    'payment_methods': [],
                    'count': 0
                }, 200
                
        except Exception as e:
            logger.error(f"Mobile payment methods retrieval failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to retrieve payment methods',
                'error_code': 'METHODS_ERROR'
            }, 500
    
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.expect(mobile_attach_payment_method_model)
    @mobile_payment_api.response(201, 'Payment method attached successfully', mobile_payment_method_response_model)
    @mobile_payment_api.response(400, 'Validation Error')
    @mobile_payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Attach a pre-created Stripe payment method to customer (card details handled client-side)"""
        try:
            customer_id = get_jwt_identity()
            data = request.get_json()
            
            # Get payment method ID from request
            payment_method_id = data.get('payment_method_id')
            if not payment_method_id:
                return {
                    'success': False,
                    'error': 'Payment method ID required',
                    'error_code': 'MISSING_PAYMENT_METHOD_ID'
                }, 400
            
            # Get customer info
            customer = Customer.query.get(customer_id)
            if not customer:
                return {
                    'success': False,
                    'error': 'Customer not found',
                    'error_code': 'CUSTOMER_NOT_FOUND'
                }, 404
            
            # Create or get Stripe customer
            stripe_customer_id = customer.stripe_customer_id
            if not stripe_customer_id:
                stripe_result = stripe_payment_service.create_customer(
                    email=customer.email,
                    name=f"{customer.first_name} {customer.last_name}",
                    phone=customer.phone_number,
                    metadata={'mobile_customer': 'true', 'customer_id': str(customer_id)}
                )
                
                if stripe_result['success']:
                    stripe_customer_id = stripe_result['customer_id']
                    customer.stripe_customer_id = stripe_customer_id
                    db.session.commit()
                else:
                    return {
                        'success': False,
                        'error': 'Failed to initialize payment customer',
                        'error_code': 'STRIPE_CUSTOMER_ERROR'
                    }, 500
            
            # Attach pre-created payment method to customer
            attach_result = stripe_payment_service.attach_payment_method(
                payment_method_id=payment_method_id,
                customer_id=stripe_customer_id
            )
            
            if not attach_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to attach payment method',
                    'error_code': 'ATTACH_ERROR',
                    'details': attach_result.get('error')
                }, 400
            
            # Get payment method details for response
            try:
                payment_method = stripe_payment_service.stripe.PaymentMethod.retrieve(payment_method_id)
                
                return {
                    'success': True,
                    'payment_method_id': payment_method.id,
                    'type': payment_method.type,
                    'card': {
                        'brand': payment_method.card.brand,
                        'last4': payment_method.card.last4,
                        'exp_month': payment_method.card.exp_month,
                        'exp_year': payment_method.card.exp_year,
                        'display_name': f"{payment_method.card.brand.upper()} •••• {payment_method.card.last4}"
                    },
                    'customer_id': stripe_customer_id
                }, 201
                
            except stripe.StripeError as e:
                logger.error(f"Stripe error retrieving payment method: {str(e)}")
                return {
                    'success': False,
                    'error': f'Failed to retrieve payment method details: {str(e)}',
                    'error_code': 'STRIPE_ERROR'
                }, 400
                
        except Exception as e:
            logger.error(f"Mobile payment method creation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment method creation failed',
                'error_code': 'SYSTEM_ERROR'
            }, 500

@mobile_payment_api.route('/payment-methods/<string:payment_method_id>')
class MobilePaymentMethodDetail(Resource):
    """Manage individual payment methods for mobile"""
    @mobile_payment_api.doc(security='Bearer Auth')
    @mobile_payment_api.response(200, 'Payment method detached successfully')
    @mobile_payment_api.response(404, 'Payment method not found')
    @jwt_required()
    def delete(self, payment_method_id):
        """Detach a payment method from customer"""
        try:
            customer_id = get_jwt_identity()
            customer = Customer.query.get(customer_id)
            
            if not customer or not customer.stripe_customer_id:
                return {
                    'success': False,
                    'error': 'Customer not found or no Stripe account',
                    'error_code': 'CUSTOMER_NOT_FOUND'
                }, 404
            
            # Detach payment method from Stripe
            detach_result = stripe_payment_service.detach_payment_method(payment_method_id)
            
            if not detach_result['success']:
                return {
                    'success': False,
                    'error': 'Failed to detach payment method',
                    'error_code': 'DETACH_ERROR',
                    'details': detach_result.get('error')
                }, 400
            
            return {
                'success': True,
                'payment_method_id': payment_method_id,
                'message': 'Payment method detached successfully'
            }, 200
            
        except Exception as e:
            logger.error(f"Mobile payment method detachment failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to detach payment method',
                'error_code': 'SYSTEM_ERROR'
            }, 500

# Health check endpoint for mobile apps
@mobile_payment_api.route('/health')
class MobilePaymentHealth(Resource):
    """Payment system health check for mobile apps"""
    def get(self):
        """Check payment system health"""
        try:
            # Quick system checks
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'database': 'healthy',
                    'stripe': 'healthy',
                    'payment_service': 'healthy'
                },
                'response_time_target': '< 500ms',
                'mobile_optimized': True
            }
            
            # Test database connection (graceful fallback)
            try:
                db.session.execute('SELECT 1')
                health_status['services']['database'] = 'healthy'
            except Exception as db_error:
                logger.warning(f"Database health check failed: {str(db_error)}")
                health_status['services']['database'] = 'degraded'
                health_status['status'] = 'degraded'
            
            # Test Stripe connection (lightweight)
            try:
                stripe_test = stripe_payment_service.stripe.api_key is not None
                if stripe_test:
                    health_status['services']['stripe'] = 'healthy'
                else:
                    health_status['services']['stripe'] = 'degraded'
                    health_status['status'] = 'degraded'
            except Exception as stripe_error:
                logger.warning(f"Stripe health check failed: {str(stripe_error)}")
                health_status['services']['stripe'] = 'degraded'
                health_status['status'] = 'degraded'
            
            # Test payment service
            try:
                if hasattr(payment_service, 'platform_fee_percentage'):
                    health_status['services']['payment_service'] = 'healthy'
                else:
                    health_status['services']['payment_service'] = 'degraded'
                    health_status['status'] = 'degraded'
            except Exception as payment_error:
                logger.warning(f"Payment service health check failed: {str(payment_error)}")
                health_status['services']['payment_service'] = 'degraded'
                health_status['status'] = 'degraded'
            
            return health_status, 200
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': 'System health check failed',
                'details': str(e)
            }, 503

@mobile_payment_api.route('/payment/<string:payment_id>')
class MobilePaymentPage(Resource):
    """Payment page for mobile apps"""
    @mobile_payment_api.response(200, 'Payment page loaded successfully')
    @mobile_payment_api.response(404, 'Payment not found')
    def get(self, payment_id):
        """Get payment page information for redirect"""
        try:
            from models.payment import Payment
            
            # Get payment details
            payment = Payment.query.filter_by(payment_id=payment_id).first()
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Get delivery details
            delivery = Delivery.query.get(payment.delivery_id)
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'delivery_id': payment.delivery_id,
                'amount': float(payment.amount) if payment.amount else 0.0,
                'currency': payment.currency,
                'status': payment.status.value if payment.status else 'PENDING',
                'stripe_payment_intent_id': payment.stripe_payment_intent_id,
                'payment_page': {
                    'title': f'Payment for Delivery #{payment.delivery_id}',
                    'amount_display': f'${float(payment.amount):.2f} {payment.currency.upper()}' if payment.amount else 'N/A',
                    'description': payment.description,
                    'stripe_checkout_url': f'https://checkout.stripe.com/pay/{payment.stripe_payment_intent_id}',
                    'redirect_required': True
                },
                'delivery_info': {
                    'pickup_address': delivery.pickup_address if delivery else 'N/A',
                    'dropoff_address': delivery.dropoff_address if delivery else 'N/A',
                    'item_name': delivery.item_name if delivery else 'N/A'
                } if delivery else None
            }, 200
            
        except Exception as e:
            logger.error(f"Payment page load failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Payment page temporarily unavailable',
                'error_code': 'SYSTEM_ERROR'
            }, 500

@mobile_payment_api.route('/redirect/<string:payment_id>')
class MobilePaymentRedirect(Resource):
    """Immediate redirect to payment page"""
    @mobile_payment_api.response(302, 'Redirect to payment page')
    @mobile_payment_api.response(404, 'Payment not found')
    def get(self, payment_id):
        """Redirect user to payment page"""
        try:
            from models.payment import Payment
            
            # Get payment details
            payment = Payment.query.filter_by(payment_id=payment_id).first()
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Return redirect response
            from flask import redirect
            stripe_checkout_url = f'https://checkout.stripe.com/pay/{payment.stripe_payment_intent_id}'
            return redirect(stripe_checkout_url, code=302)
            
        except Exception as e:
            logger.error(f"Payment redirect failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Redirect temporarily unavailable',
                'error_code': 'SYSTEM_ERROR'
            }, 500

@mobile_payment_api.route('/webhook')
class StripeWebhook(Resource):
    """Handle Stripe webhooks for payment events"""
    @mobile_payment_api.response(200, 'Webhook processed successfully')
    @mobile_payment_api.response(400, 'Invalid webhook')
    def post(self):
        """Process Stripe webhook events"""
        try:
            import stripe
            from flask import request
            import json
            
            # Get the webhook signature
            sig_header = request.headers.get('Stripe-Signature')
            payload = request.get_data()
            
            # Verify webhook signature (in production, use your webhook secret)
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, 'whsec_test_webhook_secret'  # Replace with actual webhook secret
                )
            except ValueError as e:
                logger.error(f"Invalid payload: {e}")
                return {'error': 'Invalid payload'}, 400
            except stripe.SignatureVerificationError as e:
                logger.error(f"Invalid signature: {e}")
                return {'error': 'Invalid signature'}, 400
            
            # Handle the event
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logger.info(f"Payment succeeded: {payment_intent['id']}")
                
                # Update payment status and continue delivery flow
                self._handle_payment_success(payment_intent)
                
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                logger.error(f"Payment failed: {payment_intent['id']}")
                
                # Handle payment failure
                self._handle_payment_failure(payment_intent)
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
            return {'error': 'Webhook processing failed'}, 500
    
    def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        try:
            from models.payment import Payment, PaymentStatus
            from models.delivery import Delivery, DeliveryStatus
            from datetime import datetime
            
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if not payment:
                logger.error(f"Payment not found for intent: {payment_intent['id']}")
                return
            
            # Update payment status
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            payment.stripe_charge_id = payment_intent.get('latest_charge')
            
            # Update delivery status
            delivery = Delivery.query.get(payment.delivery_id)
            if delivery:
                delivery.payment_status = 'completed'
                delivery.payment_completed_at = datetime.utcnow()
                # Delivery.status is an Enum column; assign the Enum value
                delivery.status = DeliveryStatus.ASSIGNED  # Ready for driver assignment
                
                # Log payment completion
                logger.info(f"Payment completed for delivery {delivery.id}: ${payment.amount}")
                
                # Process driver transfer if driver is assigned
                if delivery.driver_id:
                    self._process_driver_transfer(payment, delivery)
                else:
                    # If no driver assigned, mark as ready for assignment
                    logger.info(f"Delivery {delivery.id} ready for driver assignment")
            
            db.session.commit()
            logger.info(f"Payment {payment.payment_id} marked as completed")
            
        except Exception as e:
            logger.error(f"Error handling payment success: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def _handle_payment_failure(self, payment_intent):
        """Handle failed payment"""
        try:
            from models.payment import Payment, PaymentStatus
            from models.delivery import Delivery, DeliveryStatus
            from datetime import datetime
            
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if not payment:
                logger.error(f"Payment not found for intent: {payment_intent['id']}")
                return
            
            # Update payment status
            payment.status = PaymentStatus.FAILED
            payment.error_message = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
            
            # Update delivery status
            delivery = Delivery.query.get(payment.delivery_id)
            if delivery:
                delivery.payment_status = 'failed'
                delivery.status = DeliveryStatus.CANCELLED.value
                
                logger.info(f"Payment failed for delivery {delivery.id}: {payment.error_message}")
            
            db.session.commit()
            logger.info(f"Payment {payment.payment_id} marked as failed")
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def _process_driver_transfer(self, payment, delivery):
        """Process transfer to driver after successful payment"""
        try:
            from models.user import Driver
            
            # Get driver information
            driver = Driver.query.get(delivery.driver_id)
            if not driver or not driver.stripe_account_id:
                logger.error(f"Driver {delivery.driver_id} not found or no Stripe account")
                return
            
            # Calculate driver payout (base amount + tip)
            driver_payout_cents = int((payment.base_amount + payment.tip_amount) * 100)
            
            # Create transfer to driver
            transfer_result = stripe_payment_service.process_delivery_payment_with_transfer(
                payment_intent_id=payment.stripe_payment_intent_id,
                driver_stripe_account_id=driver.stripe_account_id,
                driver_amount_cents=driver_payout_cents,
                platform_fee_cents=int(payment.platform_fee * 100),
                currency=payment.currency.lower(),
                delivery_id=str(delivery.id)
            )
            
            if transfer_result['success']:
                # Update payment with transfer information
                payment.stripe_transfer_id = transfer_result['transfer_id']
                logger.info(f"Transfer created for driver {driver.id}: {transfer_result['transfer_id']}")
            else:
                logger.error(f"Transfer failed for driver {driver.id}: {transfer_result['error']}")
                
        except Exception as e:
            logger.error(f"Error processing driver transfer: {str(e)}", exc_info=True)

@mobile_payment_api.route('/webhook/stripe')
class StripeWebhookLegacy(Resource):
    """Handle Stripe webhooks for payment events"""
    @mobile_payment_api.response(200, 'Webhook processed successfully')
    @mobile_payment_api.response(400, 'Invalid webhook')
    def post(self):
        """Process Stripe webhook events"""
        try:
            import stripe
            from flask import request
            import json
            
            # Get the webhook signature
            sig_header = request.headers.get('Stripe-Signature')
            payload = request.get_data()
            
            # Verify webhook signature (in production, use your webhook secret)
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, 'whsec_test_webhook_secret'  # Replace with actual webhook secret
                )
            except ValueError as e:
                logger.error(f"Invalid payload: {e}")
                return {'error': 'Invalid payload'}, 400
            except stripe.SignatureVerificationError as e:
                logger.error(f"Invalid signature: {e}")
                return {'error': 'Invalid signature'}, 400
            
            # Handle the event
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logger.info(f"Payment succeeded: {payment_intent['id']}")
                
                # Update payment status and continue delivery flow
                self._handle_payment_success(payment_intent)
                
            elif event['type'] == 'payment_intent.payment_failed':
                payment_intent = event['data']['object']
                logger.error(f"Payment failed: {payment_intent['id']}")
                
                # Handle payment failure
                self._handle_payment_failure(payment_intent)
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
            return {'error': 'Webhook processing failed'}, 500
    
    def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        try:
            from models.payment import Payment, PaymentStatus
            from models.delivery import Delivery, DeliveryStatus
            from datetime import datetime
            
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if not payment:
                logger.error(f"Payment not found for intent: {payment_intent['id']}")
                return
            
            # Update payment status
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            payment.stripe_charge_id = payment_intent.get('latest_charge')
            
            # Update delivery status
            delivery = Delivery.query.get(payment.delivery_id)
            if delivery:
                delivery.payment_status = 'completed'
                delivery.payment_completed_at = datetime.utcnow()
                # Delivery.status is an Enum column; assign the Enum value
                delivery.status = DeliveryStatus.ASSIGNED  # Ready for driver assignment
                
                # Log payment completion
                logger.info(f"Payment completed for delivery {delivery.id}: ${payment.amount}")
                
                # Process driver transfer if driver is assigned
                if delivery.driver_id:
                    self._process_driver_transfer(payment, delivery)
                else:
                    # If no driver assigned, mark as ready for assignment
                    logger.info(f"Delivery {delivery.id} ready for driver assignment")
            
            db.session.commit()
            logger.info(f"Payment {payment.payment_id} marked as completed")
            
        except Exception as e:
            logger.error(f"Error handling payment success: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def _handle_payment_failure(self, payment_intent):
        """Handle failed payment"""
        try:
            from models.payment import Payment, PaymentStatus
            from models.delivery import Delivery, DeliveryStatus
            from datetime import datetime
            
            # Find the payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()
            
            if not payment:
                logger.error(f"Payment not found for intent: {payment_intent['id']}")
                return
            
            # Update payment status
            payment.status = PaymentStatus.FAILED
            payment.error_message = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
            
            # Update delivery status
            delivery = Delivery.query.get(payment.delivery_id)
            if delivery:
                delivery.payment_status = 'failed'
                delivery.status = DeliveryStatus.CANCELLED.value
                
                logger.info(f"Payment failed for delivery {delivery.id}: {payment.error_message}")
            
            db.session.commit()
            logger.info(f"Payment {payment.payment_id} marked as failed")
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}", exc_info=True)
            db.session.rollback()
    
    def _process_driver_transfer(self, payment, delivery):
        """Process transfer to driver after successful payment"""
        try:
            from models.user import Driver
            
            # Get driver information
            driver = Driver.query.get(delivery.driver_id)
            if not driver or not driver.stripe_account_id:
                logger.error(f"Driver {delivery.driver_id} not found or no Stripe account")
                return
            
            # Calculate driver payout (base amount + tip)
            driver_payout_cents = int((payment.base_amount + payment.tip_amount) * 100)
            
            # Create transfer to driver
            transfer_result = stripe_payment_service.process_delivery_payment_with_transfer(
                payment_intent_id=payment.stripe_payment_intent_id,
                driver_stripe_account_id=driver.stripe_account_id,
                driver_amount_cents=driver_payout_cents,
                platform_fee_cents=int(payment.platform_fee * 100),
                currency=payment.currency.lower(),
                delivery_id=str(delivery.id)
            )
            
            if transfer_result['success']:
                # Update payment with transfer information
                payment.stripe_transfer_id = transfer_result['transfer_id']
                logger.info(f"Transfer created for driver {driver.id}: {transfer_result['transfer_id']}")
            else:
                logger.error(f"Transfer failed for driver {driver.id}: {transfer_result['error']}")
                
        except Exception as e:
            logger.error(f"Error processing driver transfer: {str(e)}", exc_info=True)

@mobile_payment_api.route('/confirm-payment-manual')
class ManualPaymentConfirmation(Resource):
    """Manual payment confirmation for testing"""
    @mobile_payment_api.response(200, 'Payment confirmed successfully')
    @mobile_payment_api.response(404, 'Payment not found')
    def post(self):
        """Manually confirm payment for testing purposes"""
        try:
            data = request.get_json()
            payment_id = data.get('payment_id')
            
            if not payment_id:
                return {
                    'success': False,
                    'error': 'Payment ID required',
                    'error_code': 'MISSING_PAYMENT_ID'
                }, 400
            
            from models.payment import Payment, PaymentStatus
            from models.delivery import Delivery, DeliveryStatus
            from datetime import datetime
            
            # Find the payment record
            payment = Payment.query.filter_by(payment_id=payment_id).first()
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Simulate successful payment
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            payment.stripe_charge_id = f'ch_test_{payment_id[:8]}'
            
            # Update delivery status
            delivery = Delivery.query.get(payment.delivery_id)
            if delivery:
                delivery.payment_status = 'completed'
                delivery.payment_completed_at = datetime.utcnow()
                # Delivery.status is an Enum column; assign the Enum value
                delivery.status = DeliveryStatus.ASSIGNED
                
                logger.info(f"Payment manually confirmed for delivery {delivery.id}: ${payment.amount}")
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Payment confirmed successfully',
                'payment_id': payment.payment_id,
                'delivery_id': payment.delivery_id,
                'status': 'completed',
                'next_steps': {
                    'delivery_status': 'ASSIGNED',
                    'ready_for_driver': True,
                    'driver_transfer': 'pending' if delivery and delivery.driver_id else 'not_applicable'
                }
            }, 200
            
        except Exception as e:
            logger.error(f"Manual payment confirmation failed: {str(e)}", exc_info=True)
            db.session.rollback()
            return {
                'success': False,
                'error': 'Payment confirmation failed',
                'error_code': 'CONFIRMATION_ERROR'
            }, 500

@mobile_payment_api.route('/payment-status/<string:payment_id>')
class PaymentStatusCheck(Resource):
    """Check payment status and delivery progress"""
    @mobile_payment_api.response(200, 'Payment status retrieved')
    @mobile_payment_api.response(404, 'Payment not found')
    def get(self, payment_id):
        """Get current payment and delivery status"""
        try:
            from models.payment import Payment
            from models.delivery import Delivery
            
            # Get payment details
            payment = Payment.query.filter_by(payment_id=payment_id).first()
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
            # Get delivery details
            delivery = Delivery.query.get(payment.delivery_id)
            
            # Determine next steps based on payment status
            next_steps = []
            if payment.status.value == 'pending':
                next_steps.append('Complete payment to proceed')
            elif payment.status.value == 'completed':
                if delivery and delivery.status.value == 'ASSIGNED':
                    next_steps.append('Driver assignment in progress')
                elif delivery and delivery.status.value == 'ACCEPTED':
                    next_steps.append('Driver is on the way')
                elif delivery and delivery.status.value == 'IN_PROGRESS':
                    next_steps.append('Delivery in progress')
                elif delivery and delivery.status.value == 'COMPLETED':
                    next_steps.append('Delivery completed')
            elif payment.status.value == 'failed':
                next_steps.append('Payment failed - please retry')
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'delivery_id': payment.delivery_id,
                'payment_status': payment.status.value,
                'delivery_status': delivery.status.value if delivery else 'N/A',
                'amount': float(payment.amount) if payment.amount else 0.0,
                'currency': payment.currency,
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'next_steps': next_steps,
                'delivery_info': {
                    'pickup_address': delivery.pickup_address if delivery else 'N/A',
                    'dropoff_address': delivery.dropoff_address if delivery else 'N/A',
                    'driver_assigned': delivery.driver_id is not None if delivery else False
                } if delivery else None
            }, 200
            
        except Exception as e:
            logger.error(f"Payment status check failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Status check failed',
                'error_code': 'STATUS_CHECK_ERROR'
            }, 500

@mobile_payment_api.route('/test-payment-intent')
class MobileTestPaymentIntent(Resource):
    """Test payment intent creation without authentication"""
    @mobile_payment_api.expect(mobile_payment_intent_model)
    @mobile_payment_api.response(201, 'Payment intent created successfully', mobile_payment_response_model)
    @mobile_payment_api.response(400, 'Validation Error')
    def post(self):
        """Test payment intent creation for debugging"""
        try:
            data = request.get_json()
            delivery_id = data.get('delivery_id')
            amount = data.get('amount', 0)
            tip_amount = data.get('tip_amount', 0)
            currency = data.get('currency', 'usd')
            
            # Create a mock delivery for testing
            from models.delivery import Delivery
            delivery = Delivery()
            delivery.id = int(delivery_id)
            delivery.estimated_distance_km = 5.0
            delivery.vehicle_type = 'pickup_truck'
            
            # Calculate cost breakdown
            cost_breakdown = payment_service.calculate_delivery_cost_with_pricing(
                distance_km=delivery.estimated_distance_km,
                vehicle_type=delivery.vehicle_type or 'car'
            )
            
            # Calculate payment breakdown
            breakdown = payment_service.calculate_delivery_payment_breakdown(
                base_amount=cost_breakdown['base_delivery_cost'],
                tip_amount=tip_amount / 100.0,
                currency=currency.upper()
            )
            
            return {
                'success': True,
                'delivery_id': delivery_id,
                'amount': breakdown['total_amount_cents'],
                'breakdown': breakdown,
                'cost_breakdown': cost_breakdown
            }, 201
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TEST_ERROR'
            }, 500
