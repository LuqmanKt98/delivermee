#!/usr/bin/env python3
"""
Delivery Model for DeliverMe
Matches the actual database schema from migrations
"""

from extensions import db
from datetime import datetime
from enum import Enum
import json

class DeliveryStatus(Enum):
    """Delivery statuses"""
    REQUESTED = 'REQUESTED'
    PENDING = 'pending'
    PAID = 'paid'
    ASSIGNED = 'ASSIGNED'
    ACCEPTED = 'ACCEPTED'
    IN_PROGRESS = 'in_progress'
    PICKED_UP = 'PICKED_UP'
    IN_TRANSIT = 'IN_TRANSIT'
    DELIVERED = 'DELIVERED'
    COMPLETED = 'completed'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'

class DeliveryPriority(Enum):
    """Delivery priorities"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'

class PackageType(Enum):
    """Package types"""
    SMALL = 'SMALL'
    MEDIUM = 'MEDIUM'
    LARGE = 'LARGE'
    EXTRA_LARGE = 'EXTRA_LARGE'
    FRAGILE = 'FRAGILE'
    PERISHABLE = 'PERISHABLE'
    ELECTRONICS = 'ELECTRONICS'

class Delivery(db.Model):
    """Delivery model for tracking delivery requests"""
    
    __tablename__ = 'deliveries'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Customer information
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Driver information
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    
    # Delivery details
    pickup_address = db.Column(db.Text, nullable=False)
    dropoff_address = db.Column(db.Text, nullable=False)
    
    # Location coordinates
    pickup_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    pickup_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    dropoff_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    dropoff_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    
    # Item details
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.Text, nullable=True)
    item_photo_url = db.Column(db.String(500), nullable=True)
    
    # Package details
    package_type = db.Column(db.Enum(PackageType), nullable=False)
    package_size = db.Column(db.String(20), nullable=True)  # small, medium, large, extra_large, huge
    width = db.Column(db.Numeric(8, 2), nullable=True)
    height = db.Column(db.Numeric(8, 2), nullable=True)
    length = db.Column(db.Numeric(8, 2), nullable=True)
    weight = db.Column(db.Numeric(8, 2), nullable=True)
    item_count = db.Column(db.Integer, nullable=True, default=1)
    
    # Vehicle details
    vehicle_type = db.Column(db.String(50), nullable=True)
    
    # Distance and cost
    estimated_distance_km = db.Column(db.Numeric(8, 2), nullable=True)
    actual_distance_km = db.Column(db.Numeric(8, 2), nullable=True)
    estimated_cost = db.Column(db.Numeric(10, 2), nullable=True)
    actual_cost = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Package characteristics
    is_fragile = db.Column(db.Boolean, nullable=True)
    is_perishable = db.Column(db.Boolean, nullable=True)
    requires_signature = db.Column(db.Boolean, nullable=True)
    
    # Additional information
    special_instructions = db.Column(db.Text, nullable=True)
    delivery_type = db.Column(db.String(20), nullable=True)
    
    # Status
    status = db.Column(db.Enum(DeliveryStatus), nullable=True)
    
    # Pricing
    estimated_cost = db.Column(db.Numeric(10, 2), nullable=True)
    actual_cost = db.Column(db.Numeric(10, 2), nullable=True)
    insurance_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Payment information
    payment_status = db.Column(db.String(20), nullable=True, default='pending')
    payment_intent_id = db.Column(db.String(100), nullable=True)  # Stripe payment intent ID
    payment_completed_at = db.Column(db.DateTime, nullable=True)
    currency = db.Column(db.String(3), nullable=True, default='USD')
    
    # Timing
    scheduled_time = db.Column(db.DateTime, nullable=True)
    scheduled_date = db.Column(db.Date, nullable=True)  # For scheduled deliveries
    time_slot = db.Column(db.String(20), nullable=True)  # Time slot for scheduled deliveries
    schedule_type = db.Column(db.String(20), nullable=True)  # immediate, scheduled
    delivery_preference = db.Column(db.String(20), nullable=True, default='attended')  # attended, unattended
    requested_time = db.Column(db.DateTime, nullable=True)
    assigned_time = db.Column(db.DateTime, nullable=True)
    accepted_time = db.Column(db.DateTime, nullable=True)
    pickup_time = db.Column(db.DateTime, nullable=True)
    delivered_time = db.Column(db.DateTime, nullable=True)
    cancelled_time = db.Column(db.DateTime, nullable=True)
    
    # Tracking
    tracking_number = db.Column(db.String(50), nullable=True, unique=True)
    estimated_duration = db.Column(db.Integer, nullable=True)
    actual_duration = db.Column(db.Integer, nullable=True)
    
    # Customer feedback
    customer_rating = db.Column(db.Numeric(3, 2), nullable=True)
    customer_feedback = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, **kwargs):
        super(Delivery, self).__init__(**kwargs)
        if not self.requested_time:
            self.requested_time = datetime.utcnow()
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Delivery {self.id}: {self.item_name} ({self.status.value if self.status else "Unknown"})>'
    
    def to_dict(self):
        """Convert delivery to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'driver_id': self.driver_id,
            'pickup_address': self.pickup_address,
            'dropoff_address': self.dropoff_address,
            'pickup_latitude': float(self.pickup_latitude) if self.pickup_latitude else None,
            'pickup_longitude': float(self.pickup_longitude) if self.pickup_longitude else None,
            'dropoff_latitude': float(self.dropoff_latitude) if self.dropoff_latitude else None,
            'dropoff_longitude': float(self.dropoff_longitude) if self.dropoff_longitude else None,
            'item_name': self.item_name,
            'item_description': self.item_description,
            'item_photo_url': self.item_photo_url,
            'package_type': self.package_type.value if self.package_type else None,
            'package_size': self.package_size,
            'width': float(self.width) if self.width else None,
            'height': float(self.height) if self.height else None,
            'length': float(self.length) if self.length else None,
            'weight': float(self.weight) if self.weight else None,
            'item_count': self.item_count,
            'vehicle_type': self.vehicle_type.value if self.vehicle_type else None,
            'estimated_distance_km': float(self.estimated_distance_km) if self.estimated_distance_km else None,
            'actual_distance_km': float(self.actual_distance_km) if self.actual_distance_km else None,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'is_fragile': self.is_fragile,
            'is_perishable': self.is_perishable,
            'requires_signature': self.requires_signature,
            'special_instructions': self.special_instructions,
            'delivery_type': self.delivery_type.value if self.delivery_type else None,
            'status': self.status.value if self.status else None,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'insurance_amount': float(self.insurance_amount) if self.insurance_amount else None,
            'payment_status': self.payment_status,
            'payment_intent_id': self.payment_intent_id,
            'payment_completed_at': self.payment_completed_at.isoformat() if self.payment_completed_at else None,
            'currency': self.currency,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'scheduled_date': str(self.scheduled_date) if self.scheduled_date else None,
            'time_slot': self.time_slot,
            'schedule_type': self.schedule_type,
            'delivery_preference': self.delivery_preference,
            'requested_time': self.requested_time.isoformat() if self.requested_time else None,
            'assigned_time': self.assigned_time.isoformat() if self.assigned_time else None,
            'accepted_time': self.accepted_time.isoformat() if self.accepted_time else None,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'delivered_time': self.delivered_time.isoformat() if self.delivered_time else None,
            'cancelled_time': self.cancelled_time.isoformat() if self.cancelled_time else None,
            'tracking_number': self.tracking_number,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'customer_rating': float(self.customer_rating) if self.customer_rating else None,
            'customer_feedback': self.customer_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def assign_driver(self, driver_id: int):
        """Assign a driver to the delivery"""
        self.driver_id = driver_id
        self.status = DeliveryStatus.ASSIGNED
        self.assigned_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def accept_delivery(self):
        """Driver accepts the delivery"""
        if self.status != DeliveryStatus.ASSIGNED:
            raise ValueError("Delivery must be assigned before it can be accepted")
        
        self.status = DeliveryStatus.ACCEPTED
        self.accepted_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def pick_up(self):
        """Mark delivery as picked up"""
        if self.status != DeliveryStatus.ACCEPTED:
            raise ValueError("Delivery must be accepted before it can be picked up")
        
        self.status = DeliveryStatus.PICKED_UP
        self.pickup_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def start_transit(self):
        """Mark delivery as in transit"""
        if self.status != DeliveryStatus.PICKED_UP:
            raise ValueError("Delivery must be picked up before it can be in transit")
        
        self.status = DeliveryStatus.IN_TRANSIT
        self.updated_at = datetime.utcnow()
    
    def complete_delivery(self):
        """Mark delivery as completed"""
        if self.status not in [DeliveryStatus.IN_TRANSIT, DeliveryStatus.PICKED_UP]:
            raise ValueError("Delivery must be in transit or picked up before it can be completed")
        
        self.status = DeliveryStatus.DELIVERED
        self.delivered_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def cancel_delivery(self, reason: str = None):
        """Cancel the delivery"""
        if self.status in [DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED]:
            raise ValueError("Cannot cancel a completed or already cancelled delivery")
        
        self.status = DeliveryStatus.CANCELLED
        self.cancelled_time = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if reason:
            if not hasattr(self, 'delivery_metadata') or not self.delivery_metadata:
                self.delivery_metadata = {}
            self.delivery_metadata['cancellation_reason'] = reason
    
    def update_payment_status(self, payment_intent_id: str, amount: float, currency: str = 'USD'):
        """Update payment status after successful payment"""
        self.payment_intent_id = payment_intent_id
        self.payment_status = 'completed'
        self.payment_completed_at = datetime.utcnow()
        self.actual_cost = amount
        self.currency = currency.upper()
        self.status = DeliveryStatus.PAID
        self.updated_at = datetime.utcnow()
    
    def can_be_updated(self):
        """Check if delivery can be updated"""
        return self.status not in [DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED, DeliveryStatus.FAILED]
    
    def can_be_cancelled(self):
        """Check if delivery can be cancelled"""
        return self.status not in [DeliveryStatus.DELIVERED, DeliveryStatus.CANCELLED]
    
    def is_completed(self):
        """Check if delivery is completed"""
        return self.status == DeliveryStatus.DELIVERED
    
    def get_duration_minutes(self):
        """Get delivery duration in minutes"""
        if self.delivered_time and self.requested_time:
            duration = self.delivered_time - self.requested_time
            return duration.total_seconds() / 60
        return None
    
    @classmethod
    def get_by_customer(cls, customer_id: int, limit: int = 50):
        """Get deliveries by customer"""
        return cls.query.filter_by(customer_id=customer_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_by_driver(cls, driver_id: int, limit: int = 50):
        """Get deliveries by driver"""
        return cls.query.filter_by(driver_id=driver_id).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_by_status(cls, status: DeliveryStatus, limit: int = 100):
        """Get deliveries by status"""
        return cls.query.filter_by(status=status).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_pending_deliveries(cls, limit: int = 100):
        """Get pending deliveries"""
        return cls.query.filter_by(status=DeliveryStatus.REQUESTED).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_active_deliveries(cls, limit: int = 100):
        """Get active deliveries"""
        active_statuses = [DeliveryStatus.ASSIGNED, DeliveryStatus.ACCEPTED, DeliveryStatus.PICKED_UP, DeliveryStatus.IN_TRANSIT]
        return cls.query.filter(cls.status.in_(active_statuses)).order_by(cls.created_at.desc()).limit(limit).all()