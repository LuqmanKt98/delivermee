#!/usr/bin/env python3
"""
Payment Model for DeliverMe
Simplified payment model without Stripe integration
Stripe integration is handled exclusively by the mobile payment system
"""

from extensions import db
from datetime import datetime
from enum import Enum
import uuid

class PaymentType(Enum):
    """Payment types"""
    DELIVERY_FEE = 'delivery_fee'
    DRIVER_PAYOUT = 'driver_payout'
    TIP = 'tip'
    REFUND = 'refund'
    PLATFORM_FEE = 'platform_fee'
    ADJUSTMENT = 'adjustment'

class PaymentStatus(Enum):
    """Payment statuses"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'
    EXPIRED = 'expired'

class PaymentMethod(Enum):
    """Payment methods"""
    CREDIT_CARD = 'credit_card'
    DEBIT_CARD = 'debit_card'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    DIGITAL_WALLET = 'digital_wallet'

class PaymentDirection(Enum):
    """Payment directions"""
    INBOUND = 'inbound'  # Money coming in
    OUTBOUND = 'outbound'  # Money going out

class Payment(db.Model):
    """Payment model for tracking all financial transactions"""
    
    __tablename__ = 'payments'
    
    # Primary key
    payment_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Payment details
    payment_type = db.Column(db.Enum(PaymentType), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    direction = db.Column(db.Enum(PaymentDirection), nullable=False)
    
    # Payer information
    payer_id = db.Column(db.Integer, nullable=False)
    payer_type = db.Column(db.String(20), nullable=False)  # customer, driver, platform
    payer_stripe_id = db.Column(db.String(255), nullable=True)  # Stripe customer ID (mobile only)
    
    # Receiver information
    receiver_id = db.Column(db.Integer, nullable=True)
    receiver_type = db.Column(db.String(20), nullable=False)  # platform, driver, customer
    receiver_stripe_id = db.Column(db.String(255), nullable=True)  # Stripe account ID (mobile only)
    
    # Payment method
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    payment_method_id = db.Column(db.String(255), nullable=True)  # Stripe payment method ID (mobile only)
    
    # Stripe Integration (Mobile Only)
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    stripe_transfer_id = db.Column(db.String(255), nullable=True)  # For driver payouts
    
    # Associated entities
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    
    # Fee breakdown
    base_amount = db.Column(db.Numeric(10, 2), nullable=True)
    platform_fee = db.Column(db.Numeric(10, 2), nullable=True)
    payment_processing_fee = db.Column(db.Numeric(10, 2), nullable=True)
    driver_payout = db.Column(db.Numeric(10, 2), nullable=True)
    tip_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    payment_metadata = db.Column(db.JSON, default=lambda: {})
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Error handling
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    def __init__(self, **kwargs):
        super(Payment, self).__init__(**kwargs)
        if not self.payment_id:
            self.payment_id = str(uuid.uuid4())
    
    def __repr__(self):
        return f'<Payment {self.payment_id}: {self.amount} {self.currency} ({self.status.value})>'
    
    def to_dict(self):
        """Convert payment to dictionary"""
        return {
            'payment_id': self.payment_id,
            'payment_type': self.payment_type.value if self.payment_type else None,
            'amount': float(self.amount) if self.amount else 0.0,
            'currency': self.currency,
            'status': self.status.value if self.status else None,
            'direction': self.direction.value if self.direction else None,
            'payer_id': self.payer_id,
            'payer_type': self.payer_type,
            'payer_stripe_id': self.payer_stripe_id,
            'receiver_id': self.receiver_id,
            'receiver_type': self.receiver_type,
            'receiver_stripe_id': self.receiver_stripe_id,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'payment_method_id': self.payment_method_id,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'stripe_charge_id': self.stripe_charge_id,
            'stripe_transfer_id': self.stripe_transfer_id,
            'delivery_id': self.delivery_id,
            'driver_id': self.driver_id,
            'base_amount': float(self.base_amount) if self.base_amount else None,
            'platform_fee': float(self.platform_fee) if self.platform_fee else None,
            'payment_processing_fee': float(self.payment_processing_fee) if self.payment_processing_fee else None,
            'driver_payout': float(self.driver_payout) if self.driver_payout else None,
            'tip_amount': float(self.tip_amount) if self.tip_amount else None,
            'description': self.description,
            'payment_metadata': self.payment_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return (
            self.status == PaymentStatus.COMPLETED and
            self.direction == PaymentDirection.INBOUND and
            self.payment_type in [PaymentType.DELIVERY_FEE, PaymentType.TIP]
        )
    
    def can_be_cancelled(self):
        """Check if payment can be cancelled"""
        return self.status == PaymentStatus.PENDING
    
    def mark_as_failed(self, error_message: str):
        """Mark payment as failed"""
        self.status = PaymentStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
    
    def increment_retry_count(self):
        """Increment retry count"""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def get_total_amount_with_tip(self):
        """Get total amount including tip"""
        base = float(self.amount) if self.amount else 0.0
        tip = float(self.tip_amount) if self.tip_amount else 0.0
        return base + tip
    
    def get_fee_breakdown(self):
        """Get fee breakdown"""
        return {
            'base_amount': float(self.base_amount) if self.base_amount else 0.0,
            'platform_fee': float(self.platform_fee) if self.platform_fee else 0.0,
            'payment_processing_fee': float(self.payment_processing_fee) if self.payment_processing_fee else 0.0,
            'driver_payout': float(self.driver_payout) if self.driver_payout else 0.0,
            'tip_amount': float(self.tip_amount) if self.tip_amount else 0.0
        }
    
    @classmethod
    def get_by_customer(cls, customer_id: int, limit: int = 50):
        """Get payments by customer"""
        return cls.query.filter_by(payer_id=customer_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_by_delivery(cls, delivery_id: int):
        """Get payments by delivery"""
        return cls.query.filter_by(delivery_id=delivery_id).all()
    
    @classmethod
    def get_by_status(cls, status: PaymentStatus, limit: int = 100):
        """Get payments by status"""
        return cls.query.filter_by(status=status).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_payments(cls, limit: int = 100):
        """Get pending payments"""
        return cls.get_by_status(PaymentStatus.PENDING, limit)
    
    @classmethod
    def get_completed_payments(cls, limit: int = 100):
        """Get completed payments"""
        return cls.get_by_status(PaymentStatus.COMPLETED, limit)
    
    @classmethod
    def get_failed_payments(cls, limit: int = 100):
        """Get failed payments"""
        return cls.get_by_status(PaymentStatus.FAILED, limit)
