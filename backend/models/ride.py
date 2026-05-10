from extensions import db
from datetime import datetime
from enum import Enum
from models.vehicle import VehicleType

class RideStatus(Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_DRIVER_AVAILABLE = "no_driver_available"

class RideType(Enum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"

class Ride(db.Model):
    __tablename__ = 'rides'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=True)
    
    # Ride details
    pickup_address = db.Column(db.String(500), nullable=False)
    dropoff_address = db.Column(db.String(500), nullable=False)
    pickup_latitude = db.Column(db.Float, nullable=True)
    pickup_longitude = db.Column(db.Float, nullable=True)
    dropoff_latitude = db.Column(db.Float, nullable=True)
    dropoff_longitude = db.Column(db.Float, nullable=True)
    
    # Scheduling
    ride_type = db.Column(db.Enum(RideType, values_callable=lambda obj: [e.value for e in obj]), default=RideType.IMMEDIATE)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    requested_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status and tracking
    status = db.Column(db.Enum(RideStatus, values_callable=lambda obj: [e.value for e in obj]), default=RideStatus.REQUESTED)
    estimated_duration = db.Column(db.Integer, nullable=True)  # in minutes
    estimated_distance = db.Column(db.Float, nullable=True)  # in kilometers
    estimated_cost = db.Column(db.Float, nullable=True)
    
    # Driver assignment and tracking
    assigned_time = db.Column(db.DateTime, nullable=True)
    accepted_time = db.Column(db.DateTime, nullable=True)
    pickup_time = db.Column(db.DateTime, nullable=True)
    completed_time = db.Column(db.DateTime, nullable=True)
    
    # Ride preferences
    vehicle_type = db.Column(db.String(50), nullable=True)
    special_instructions = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='rides')
    driver = db.relationship('Driver', backref='rides')

    def __init__(self, customer_id, pickup_address, dropoff_address, **kwargs):
        self.customer_id = customer_id
        self.pickup_address = pickup_address
        self.dropoff_address = dropoff_address
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'driver_id': self.driver_id,
            'pickup_address': self.pickup_address,
            'dropoff_address': self.dropoff_address,
            'pickup_latitude': self.pickup_latitude,
            'pickup_longitude': self.pickup_longitude,
            'dropoff_latitude': self.dropoff_latitude,
            'dropoff_longitude': self.dropoff_longitude,
            'ride_type': self.ride_type.value if self.ride_type else None,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'requested_time': self.requested_time.isoformat(),
            'status': self.status.value if self.status else None,
            'estimated_duration': self.estimated_duration,
            'estimated_distance': self.estimated_distance,
            'estimated_cost': self.estimated_cost,
            'assigned_time': self.assigned_time.isoformat() if self.assigned_time else None,
            'accepted_time': self.accepted_time.isoformat() if self.accepted_time else None,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'vehicle_type': self.vehicle_type,
            'special_instructions': self.special_instructions,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def can_be_cancelled(self):
        """Check if ride can be cancelled based on current status"""
        cancellable_statuses = [
            RideStatus.REQUESTED,
            RideStatus.ASSIGNED,
            RideStatus.ACCEPTED
        ]
        return self.status in cancellable_statuses

    def can_be_updated(self):
        """Check if ride can be updated based on current status"""
        updatable_statuses = [
            RideStatus.REQUESTED,
            RideStatus.ASSIGNED
        ]
        return self.status in updatable_statuses

    def __repr__(self):
        return f'<Ride {self.id}: {self.pickup_address} to {self.dropoff_address}>' 