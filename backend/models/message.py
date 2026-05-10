from extensions import db
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    DRIVER_TO_CUSTOMER = "driver_to_customer"
    CUSTOMER_TO_DRIVER = "customer_to_driver"
    SYSTEM_NOTIFICATION = "system_notification"
    DELIVERY_UPDATE = "delivery_update"

class MessageStatus(Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    
    # Message context
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id'), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)  # Driver ID or Customer ID
    sender_type = db.Column(db.String(20), nullable=False)  # 'driver' or 'customer'
    recipient_id = db.Column(db.Integer, nullable=False)  # Driver ID or Customer ID
    recipient_type = db.Column(db.String(20), nullable=False)  # 'driver' or 'customer'
    
    # Message content
    type = db.Column(db.Enum(MessageType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    
    # Message status and delivery
    status = db.Column(db.Enum(MessageStatus, values_callable=lambda obj: [e.value for e in obj]), default=MessageStatus.SENT)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    is_urgent = db.Column(db.Boolean, default=False)
    requires_response = db.Column(db.Boolean, default=False)
    parent_message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)  # For threaded conversations
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    delivery = db.relationship('Delivery', backref='messages')
    parent_message = db.relationship('Message', remote_side=[id], backref='replies')

    def __init__(self, delivery_id, sender_id, sender_type, recipient_id, recipient_type, 
                 type, content, **kwargs):
        self.delivery_id = delivery_id
        self.sender_id = sender_id
        self.sender_type = sender_type
        self.recipient_id = recipient_id
        self.recipient_type = recipient_type
        self.type = type
        self.content = content
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def mark_as_delivered(self):
        """Mark message as delivered"""
        self.status = MessageStatus.DELIVERED
        self.delivered_at = datetime.utcnow()

    def mark_as_read(self):
        """Mark message as read"""
        self.status = MessageStatus.READ
        self.read_at = datetime.utcnow()

    def mark_as_failed(self):
        """Mark message as failed"""
        self.status = MessageStatus.FAILED

    def to_dict(self):
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'sender_id': self.sender_id,
            'sender_type': self.sender_type,
            'recipient_id': self.recipient_id,
            'recipient_type': self.recipient_type,
            'type': self.type.value if self.type else None,
            'subject': self.subject,
            'content': self.content,
            'status': self.status.value if self.status else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_urgent': self.is_urgent,
            'requires_response': self.requires_response,
            'parent_message_id': self.parent_message_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<Message {self.id}: {self.type.value} from {self.sender_type} {self.sender_id}>'
