#!/usr/bin/env python3
"""
Payment Routes for DeliverMe
Simplified payment routes - Stripe integration moved to mobile payments only
"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.payment_service import payment_service
from models.delivery import Delivery, DeliveryStatus
from models.payment import Payment, PaymentType, PaymentStatus, PaymentMethod, PaymentDirection
from models.user import Customer, Driver
from extensions import db
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create namespace for payments
payment_api = Namespace('payments', description='Payment operations')

# Payment models for Swagger documentation
payment_intent_model = payment_api.model('PaymentIntent', {
    'delivery_id': fields.Integer(required=True, description='Delivery ID'),
    'amount': fields.Integer(required=True, description='Payment amount in cents'),
    'tip_amount': fields.Integer(description='Tip amount in cents', default=0),
    'currency': fields.String(description='Currency code', default='usd'),
    'save_payment_method': fields.Boolean(description='Save payment method for future use (handled by Stripe)', default=False)
})

payment_confirm_model = payment_api.model('PaymentConfirm', {
    'payment_intent_id': fields.String(required=True, description='Stripe payment intent ID'),
    'payment_method_id': fields.String(required=True, description='Stripe payment method ID')
})

# Response models
payment_response_model = payment_api.model('PaymentResponse', {
    'success': fields.Boolean(description='Operation success'),
    'payment_intent_id': fields.String(description='Payment intent ID'),
    'amount': fields.Integer(description='Payment amount in cents'),
    'payment_id': fields.String(description='Internal payment ID'),
    'delivery_id': fields.Integer(description='Delivery ID'),
    'fee_breakdown': fields.Raw(description='Fee breakdown details'),
    'estimated_completion_time': fields.String(description='Estimated completion time in seconds')
})

delivery_cost_model = payment_api.model('DeliveryCost', {
    'distance_km': fields.Float(required=True, description='Distance in kilometers'),
    'vehicle_type': fields.String(description='Vehicle type', default='car'),
    'tip_amount': fields.Float(description='Tip amount', default=0)
})

delivery_cost_response_model = payment_api.model('DeliveryCostResponse', {
    'success': fields.Boolean(description='Operation success'),
    'estimate': fields.Raw(description='Cost estimate breakdown'),
    'currency': fields.String(description='Currency code'),
    'valid_for_minutes': fields.Integer(description='Estimate validity in minutes')
})

@payment_api.route('/create-payment-intent')
class CreatePaymentIntent(Resource):
    """Create payment intent for delivery"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.expect(payment_intent_model)
    @payment_api.response(201, 'Payment intent created successfully', payment_response_model)
    @payment_api.response(400, 'Validation Error')
    @payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Create payment intent for delivery"""
        try:
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
                return {
                    'success': False,
                    'error': 'Delivery not found or access denied',
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
            
            # Calculate fee breakdown using payment service
            total_amount = (amount + tip_amount) / 100.0
            breakdown = payment_service.calculate_delivery_payment_breakdown(
                base_amount=amount / 100.0,
                tip_amount=tip_amount / 100.0,
                currency=currency.upper()
            )
            
            # Create payment record (without Stripe integration)
            payment = Payment(
                payment_type=PaymentType.DELIVERY_FEE,
                amount=breakdown['total_amount'],
                currency=currency.upper(),
                status=PaymentStatus.PENDING,
                direction=PaymentDirection.INBOUND,
                payer_id=customer_id,
                payer_type='customer',
                receiver_type='platform',
                payment_method=PaymentMethod.CREDIT_CARD,
                delivery_id=delivery_id,
                base_amount=breakdown['base_amount'],
                platform_fee=breakdown['platform_fee'],
                payment_processing_fee=breakdown['payment_processing_fee'],
                driver_payout=breakdown['driver_payout'],
                tip_amount=breakdown['tip_amount'],
                description=f"Delivery payment for delivery {delivery_id}",
                payment_metadata={
                    'save_payment_method': save_payment_method,
                    'creation_time': datetime.utcnow().isoformat()
                }
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Simplified response (no Stripe integration)
            response = {
                'success': True,
                'payment_intent_id': f"pi_{payment.payment_id}_{int(datetime.utcnow().timestamp())}",
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
                'note': 'Mobile payment system handles Stripe integration'
            }
            
            logger.info(f"Payment intent created for delivery {delivery_id}")
            return response, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Payment intent creation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment system temporarily unavailable',
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 30  # seconds
            }, 500

@payment_api.route('/confirm-payment')
class ConfirmPayment(Resource):
    """Confirm payment"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.expect(payment_confirm_model)
    @payment_api.response(200, 'Payment confirmed successfully')
    @payment_api.response(400, 'Validation Error')
    @payment_api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Confirm payment"""
        try:
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
                payment_id=payment_intent_id.split('_')[1] if '_' in payment_intent_id else payment_intent_id,
                payer_id=customer_id
            ).first()
            
            if not payment:
                return {
                    'success': False,
                    'error': 'Payment not found or access denied',
                    'error_code': 'PAYMENT_NOT_FOUND'
                }, 404
            
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
                    delivery.status = DeliveryStatus.ASSIGNED  # ready for driver assignment/visibility
            
            db.session.commit()
            
            # Simplified response
            response = {
                'success': True,
                'payment_id': payment.payment_id,
                'delivery_id': payment.delivery_id,
                'amount': payment.amount,
                'status': 'completed',
                'completion_time': payment.completed_at.isoformat(),
                'note': 'Payment confirmed - Stripe integration handled by mobile system'
            }
            
            logger.info(f"Payment confirmed for payment {payment.payment_id}")
            return response, 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Payment confirmation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment confirmation failed',
                'error_code': 'SYSTEM_ERROR',
                'retry_after': 10
            }, 500

@payment_api.route('/status/<string:payment_id>')
class PaymentStatus(Resource):
    """Get payment status"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.response(200, 'Payment status retrieved')
    @payment_api.response(404, 'Payment not found')
    @jwt_required()
    def get(self, payment_id):
        """Get payment status"""
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
            
            # Minimal response
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
            logger.error(f"Payment status check failed: {str(e)}")
            return {
                'success': False,
                'error': 'Status check failed',
                'error_code': 'SYSTEM_ERROR'
            }, 500

@payment_api.route('/delivery-cost-estimate')
class DeliveryCostEstimate(Resource):
    """Get delivery cost estimate"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.expect(delivery_cost_model)
    @payment_api.response(200, 'Cost estimated successfully', delivery_cost_response_model)
    @jwt_required()
    def post(self):
        """Get delivery cost estimate"""
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
            
            # Response
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
            logger.error(f"Cost estimation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Cost estimation failed',
                'error_code': 'ESTIMATION_ERROR'
            }, 500

@payment_api.route('/calculate-delivery-cost')
class CalculateDeliveryCost(Resource):
    """Calculate delivery cost with pricing model"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.expect(delivery_cost_model)
    @payment_api.response(200, 'Cost calculated successfully')
    @jwt_required()
    def post(self):
        """Calculate delivery cost using integrated pricing model"""
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
            
            # Response
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
            logger.error(f"Cost calculation failed: {str(e)}")
            return {
                'success': False,
                'error': 'Cost calculation failed',
                'error_code': 'CALCULATION_ERROR'
            }, 500

@payment_api.route('/summary')
class PaymentSummary(Resource):
    """Get payment summary for customer"""
    @payment_api.doc(security='Bearer Auth')
    @payment_api.response(200, 'Payment summary retrieved')
    @jwt_required()
    def get(self):
        """Get payment summary for authenticated customer"""
        try:
            customer_id = get_jwt_identity()
            
            # Get customer's payment summary
            payments = Payment.query.filter_by(payer_id=customer_id).all()
            
            total_payments = len(payments)
            total_amount = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
            pending_payments = len([p for p in payments if p.status == PaymentStatus.PENDING])
            
            summary = {
                'success': True,
                'total_payments': total_payments,
                'total_amount': total_amount,
                'pending_payments': pending_payments,
                'currency': 'USD',
                'note': 'Stripe integration handled by mobile payment system'
            }
            
            return summary, 200
            
        except Exception as e:
            logger.error(f"Payment summary retrieval failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to retrieve payment summary',
                'error_code': 'SUMMARY_ERROR'
            }, 500

