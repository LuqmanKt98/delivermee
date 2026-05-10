#!/usr/bin/env python3
"""
Payment Service for DeliverMe
Handles payment calculations and business logic without Stripe integration
Stripe integration is handled exclusively by the mobile payment system
"""

from models.payment import Payment, PaymentType, PaymentStatus, PaymentMethod, PaymentDirection
from models.user import Customer, Driver
from models.delivery import Delivery
from extensions import db
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentService:
    """Service for handling payment operations without Stripe integration"""
    
    def __init__(self):
        # Fee percentages
        self.platform_fee_percentage = 0.15  # 15%
        self.payment_processing_fee_percentage = 0.032  # 3.2%
        self.driver_earnings_percentage = 1.0  # 100%
        
        # Vehicle pricing (base + per km) - Updated to match specifications
        self.vehicle_pricing = {
            'car': {'base': 10.0, 'per_km': 1.10},
            'suv': {'base': 30.0, 'per_km': 1.20},
            'pickup_truck': {'base': 65.0, 'per_km': 1.50},  # Updated: $65 base
            'cargo_van': {'base': 75.0, 'per_km': 1.50},    # Updated: $75 base
            'box_truck': {'base': 90.0, 'per_km': 2.00}     # Correct: $90 base + $2.00/km
        }
    
    def calculate_delivery_cost_with_pricing(self, distance_km: float, vehicle_type: str = 'car') -> dict:
        """
        Calculate delivery cost using vehicle-specific pricing model
        
        Args:
            distance_km: Distance in kilometers
            vehicle_type: Vehicle type (car, suv, pickup_truck, cargo_van, box_truck)
        
        Returns:
            Dictionary with cost breakdown
        """
        try:
            # Normalize vehicle type
            vehicle_type = vehicle_type.lower()
            
            # Get vehicle pricing
            if vehicle_type not in self.vehicle_pricing:
                vehicle_type = 'car'  # Default to car
            
            pricing = self.vehicle_pricing[vehicle_type]
            
            # Calculate base delivery cost
            base_delivery_cost = pricing['base'] + (pricing['per_km'] * distance_km)
            
            # Calculate fees
            platform_fee = base_delivery_cost * self.platform_fee_percentage
            payment_processing_fee = base_delivery_cost * self.payment_processing_fee_percentage
            
            # Driver gets 100% of base delivery cost
            driver_payout = base_delivery_cost
            
            # Total cost to customer
            total_cost = base_delivery_cost + platform_fee + payment_processing_fee
            
            # Convert to cents for consistency
            base_delivery_cost_cents = int(base_delivery_cost * 100)
            platform_fee_cents = int(platform_fee * 100)
            payment_processing_fee_cents = int(payment_processing_fee * 100)
            driver_payout_cents = int(driver_payout * 100)
            total_cost_cents = int(total_cost * 100)
            
            return {
                'base_delivery_cost': base_delivery_cost,
                'base_delivery_cost_cents': base_delivery_cost_cents,
                'platform_fee': platform_fee,
                'platform_fee_cents': platform_fee_cents,
                'payment_processing_fee': payment_processing_fee,
                'payment_processing_fee_cents': payment_processing_fee_cents,
                'driver_payout': driver_payout,
                'driver_payout_cents': driver_payout_cents,
                'total_cost': total_cost,
                'total_cost_cents': total_cost_cents,
                'vehicle_type': vehicle_type,
                'distance_km': distance_km,
                'pricing_model': {
                    'base_fare': pricing['base'],
                    'per_km_rate': pricing['per_km'],
                    'platform_fee_percentage': self.platform_fee_percentage * 100,
                    'payment_processing_fee_percentage': self.payment_processing_fee_percentage * 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating delivery cost: {str(e)}")
            raise ValueError(f"Failed to calculate delivery cost: {str(e)}")
    
    def calculate_delivery_payment_breakdown(self, base_amount: float, tip_amount: float = 0.0, currency: str = 'USD') -> dict:
        """
        Calculate payment breakdown for a delivery
        
        Args:
            base_amount: Base delivery amount in dollars
            tip_amount: Tip amount in dollars
            currency: Currency code
        
        Returns:
            Dictionary with payment breakdown
        """
        try:
            # Total amount (base + tip)
            total_amount = base_amount + tip_amount
            
            # Calculate fees on total amount
            platform_fee = total_amount * self.platform_fee_percentage
            payment_processing_fee = total_amount * self.payment_processing_fee_percentage
            
            # Driver gets 100% of base delivery amount (not including tip)
            driver_payout = base_amount
            
            # Calculate final total (base + tip + fees)
            final_total = total_amount + platform_fee + payment_processing_fee
            
            # Convert to cents
            base_amount_cents = int(base_amount * 100)
            tip_amount_cents = int(tip_amount * 100)
            platform_fee_cents = int(platform_fee * 100)
            payment_processing_fee_cents = int(payment_processing_fee * 100)
            driver_payout_cents = int(driver_payout * 100)
            total_amount_cents = int(final_total * 100)
            
            return {
                'base_amount': base_amount,
                'base_amount_cents': base_amount_cents,
                'tip_amount': tip_amount,
                'tip_amount_cents': tip_amount_cents,
                'platform_fee': platform_fee,
                'platform_fee_cents': platform_fee_cents,
                'payment_processing_fee': payment_processing_fee,
                'payment_processing_fee_cents': payment_processing_fee_cents,
                'driver_payout': driver_payout,
                'driver_payout_cents': driver_payout_cents,
                'total_amount': final_total,
                'total_amount_cents': total_amount_cents,
                'currency': currency
            }
            
        except Exception as e:
            logger.error(f"Error calculating payment breakdown: {str(e)}")
            raise ValueError(f"Failed to calculate payment breakdown: {str(e)}")
    
    def create_delivery_payment(self, customer_id: int, delivery_id: int, amount: float, 
                               tip_amount: float = 0.0, currency: str = 'USD') -> Payment:
        """
        Create a delivery payment record (without Stripe integration)
        
        Args:
            customer_id: Customer ID
            delivery_id: Delivery ID
            amount: Payment amount in dollars
            tip_amount: Tip amount in dollars
            currency: Currency code
        
        Returns:
            Payment object
        """
        try:
            # Calculate payment breakdown
            breakdown = self.calculate_delivery_payment_breakdown(
                base_amount=amount,
                tip_amount=tip_amount,
                currency=currency
            )
            
            # Create payment record
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
                    'creation_time': datetime.utcnow().isoformat(),
                    'note': 'Stripe integration handled by mobile payment system'
                }
            )
            
            db.session.add(payment)
            db.session.commit()
            
            logger.info(f"Delivery payment created: {payment.payment_id}")
            return payment
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating delivery payment: {str(e)}")
            raise ValueError(f"Failed to create delivery payment: {str(e)}")
    
    def confirm_payment(self, payment_id: str, payment_method_id: str = None) -> dict:
        """
        Confirm a payment (without Stripe integration)
        
        Args:
            payment_id: Payment ID
            payment_method_id: Payment method ID (optional)
        
        Returns:
            Dictionary with confirmation result
        """
        try:
            # Get payment record
            payment = Payment.query.get(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            # Check if payment can be confirmed
            if payment.status != PaymentStatus.PENDING:
                raise ValueError(f"Payment {payment_id} cannot be confirmed (status: {payment.status})")
            
            # Update payment status
            payment.status = PaymentStatus.COMPLETED
            payment.completed_at = datetime.utcnow()
            if payment_method_id:
                payment.payment_method_id = payment_method_id
            
            # Update delivery payment status
            if payment.delivery_id:
                delivery = Delivery.query.get(payment.delivery_id)
                if delivery:
                    delivery.payment_status = 'completed'
                    delivery.payment_completed_at = datetime.utcnow()
                    delivery.actual_cost = payment.amount
            
            db.session.commit()
            
            logger.info(f"Payment {payment_id} confirmed successfully")
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'status': payment.status.value,
                'amount': payment.amount,
                'delivery_id': payment.delivery_id,
                'completion_time': payment.completed_at.isoformat(),
                'note': 'Payment confirmed - Stripe integration handled by mobile system'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error confirming payment {payment_id}: {str(e)}")
            raise ValueError(f"Failed to confirm payment: {str(e)}")
    
    def get_payment_status(self, payment_id: str) -> dict:
        """
        Get payment status
        
        Args:
            payment_id: Payment ID
        
        Returns:
            Dictionary with payment status
        """
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'status': payment.status.value,
                'amount': payment.amount,
                'delivery_id': payment.delivery_id,
                'created_at': payment.created_at.isoformat(),
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'is_complete': payment.status == PaymentStatus.COMPLETED
            }
            
        except Exception as e:
            logger.error(f"Error getting payment status for {payment_id}: {str(e)}")
            raise ValueError(f"Failed to get payment status: {str(e)}")
    
    def get_payment_summary(self, customer_id: int) -> dict:
        """
        Get payment summary for a customer
        
        Args:
            customer_id: Customer ID
        
        Returns:
            Dictionary with payment summary
        """
        try:
            # Get customer's payments
            payments = Payment.query.filter_by(payer_id=customer_id).all()
            
            total_payments = len(payments)
            total_amount = sum(p.amount for p in payments if p.status == PaymentStatus.COMPLETED)
            pending_payments = len([p for p in payments if p.status == PaymentStatus.PENDING])
            
            return {
                'success': True,
                'total_payments': total_payments,
                'total_amount': total_amount,
                'pending_payments': pending_payments,
                'currency': 'USD',
                'note': 'Stripe integration handled by mobile payment system'
            }
            
        except Exception as e:
            logger.error(f"Error getting payment summary for customer {customer_id}: {str(e)}")
            raise ValueError(f"Failed to get payment summary: {str(e)}")

# Create global instance
payment_service = PaymentService()
