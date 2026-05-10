from extensions import db
from datetime import datetime, timedelta
from enum import Enum

class NotificationType(Enum):
    RIDE_ASSIGNMENT = "ride_assignment"
    RIDE_CANCELLATION = "ride_cancellation"
    RIDE_UPDATE = "ride_update"
    RIDE_REMINDER = "ride_reminder"
    DELIVERY_ASSIGNMENT = "delivery_assignment"
    DELIVERY_CANCELLATION = "delivery_cancellation"
    DELIVERY_UPDATE = "delivery_update"
    DELIVERY_REMINDER = "delivery_reminder"
    DRIVER_MESSAGE = "driver_message"
    CUSTOMER_MESSAGE = "customer_message"

class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('rides.id'), nullable=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=True)
    
    # Notification details
    type = db.Column(db.Enum(NotificationType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(NotificationStatus, values_callable=lambda obj: [e.value for e in obj]), default=NotificationStatus.PENDING)
    
    # Delivery tracking
    sent_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    delivery_attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=3)
    
    # Push notification details
    push_token = db.Column(db.String(500), nullable=True)  # FCM token or similar
    device_id = db.Column(db.String(200), nullable=True)
    
    # Response tracking for delivery assignments
    response_required = db.Column(db.Boolean, default=False)
    response_deadline = db.Column(db.DateTime, nullable=True)
    response_received = db.Column(db.Boolean, default=False)
    response_action = db.Column(db.String(50), nullable=True)  # 'accepted', 'rejected', 'expired'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='notifications')
    ride = db.relationship('Ride', backref='notifications')
    delivery = db.relationship('Delivery', backref='notifications')

    def __init__(self, driver_id, type, title, message, **kwargs):
        self.driver_id = driver_id
        self.type = type
        self.title = title
        self.message = message
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'ride_id': self.ride_id,
            'delivery_id': self.delivery_id,
            'type': self.type.value if self.type else None,
            'title': self.title,
            'message': self.message,
            'status': self.status.value if self.status else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'delivery_attempts': self.delivery_attempts,
            'response_required': self.response_required,
            'response_deadline': self.response_deadline.isoformat() if self.response_deadline else None,
            'response_received': self.response_received,
            'response_action': self.response_action,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        self.delivery_attempts += 1

    def mark_as_read(self):
        """Mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()

    def mark_as_failed(self):
        """Mark notification as failed"""
        self.status = NotificationStatus.FAILED
        self.delivery_attempts += 1

    def mark_as_expired(self):
        """Mark notification as expired"""
        self.status = NotificationStatus.EXPIRED
        self.response_action = 'expired'

    def set_response_deadline(self, minutes=15):
        """Set response deadline for delivery assignments"""
        self.response_required = True
        self.response_deadline = datetime.utcnow() + timedelta(minutes=minutes)

    def can_retry(self):
        """Check if notification can be retried"""
        return (self.status == NotificationStatus.FAILED and 
                self.delivery_attempts < self.max_attempts)

    def is_expired(self):
        """Check if notification has expired"""
        if self.response_deadline:
            return datetime.utcnow() > self.response_deadline
        return False

    def __repr__(self):
        return f'<Notification {self.id}: {self.type.value} for Driver {self.driver_id}>' 