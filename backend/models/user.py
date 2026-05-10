#!/usr/bin/env python3
"""
User Models for DeliverMe
Simplified user models without Stripe integration
Stripe integration is handled exclusively by the mobile payment system
"""

from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
import json

class DriverStatus(Enum):
    """Driver status enumeration"""
    AVAILABLE = 'AVAILABLE'
    BUSY = 'BUSY'
    OFFLINE = 'OFFLINE'
    INACTIVE = 'INACTIVE'

class Customer(db.Model):
    """Customer model for delivery service users"""
    
    __tablename__ = 'customers'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    
    # Address information
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True, default='USA')
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    phone_verified_at = db.Column(db.DateTime, nullable=True)
    
    # Preferences
    notification_preferences = db.Column(db.JSON, default=lambda: {
        'email_notifications': True,
        'sms_notifications': True,
        'push_notifications': True,
        'marketing_emails': False
    })
    
    # Stripe integration (Mobile Only)
    stripe_customer_id = db.Column(db.String(255), nullable=True, unique=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, **kwargs):
        # Extract password before passing to parent
        password = kwargs.pop('password', None)
        super(Customer, self).__init__(**kwargs)
        if password:
            self.set_password(password)
    
    def __repr__(self):
        return f'<Customer {self.email}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password).encode('utf-8')
    
    def check_password(self, password):
        """Check password hash"""
        try:
            if isinstance(self.password_hash, bytes):
                password_hash_str = self.password_hash.decode('utf-8')
            else:
                password_hash_str = self.password_hash
            
            # Check if this is a plain text password (not a proper hash)
            if not password_hash_str.startswith(('$2b$', '$2a$', '$2y$', 'scrypt:', 'pbkdf2:')):
                # This is a plain text password, compare directly
                return password_hash_str == password
            
            # This is a proper hash, use Werkzeug's check_password_hash
            return check_password_hash(password_hash_str, password)
        except Exception as e:
            print(f"Password check error in Customer model: {str(e)}")
            return False
    
    def to_dict(self):
        """Convert customer to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'phone_verified_at': self.phone_verified_at.isoformat() if self.phone_verified_at else None,
            'notification_preferences': self.notification_preferences,
            'stripe_customer_id': self.stripe_customer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    def get_full_name(self):
        """Get customer's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def verify_email(self):
        """Mark email as verified"""
        self.is_verified = True
        self.email_verified_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def verify_phone(self):
        """Mark phone as verified"""
        self.phone_verified_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_notification_preferences(self, preferences: dict):
        """Update notification preferences"""
        if not self.notification_preferences:
            self.notification_preferences = {}
        
        self.notification_preferences.update(preferences)
        self.updated_at = datetime.utcnow()
    
    def is_fully_verified(self):
        """Check if customer is fully verified"""
        return self.is_verified and self.email_verified_at is not None
    
    @classmethod
    def get_by_email(cls, email: str):
        """Get customer by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_active_customers(cls, limit: int = 100):
        """Get active customers"""
        return cls.query.filter_by(is_active=True).order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_verified_customers(cls, limit: int = 100):
        """Get verified customers"""
        return cls.query.filter_by(is_verified=True).order_by(cls.created_at.desc()).limit(limit).all()

class Driver(db.Model):
    """Driver model for delivery service drivers"""
    
    __tablename__ = 'drivers'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic information
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    
    # Driver-specific information
    license_number = db.Column(db.String(50), nullable=False, unique=True)
    vehicle_type = db.Column(db.String(50), nullable=False)
    vehicle_make = db.Column(db.String(50), nullable=True)
    vehicle_model = db.Column(db.String(50), nullable=True)
    vehicle_year = db.Column(db.Integer, nullable=True)
    vehicle_plate_number = db.Column(db.String(20), nullable=True)
    
    # Document storage (GCS object keys)
    driving_license_image = db.Column(db.String(500), nullable=True)
    id_card_image = db.Column(db.String(500), nullable=True)
    insurance_image = db.Column(db.String(500), nullable=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected
    status = db.Column(db.Enum(DriverStatus), nullable=False, default=DriverStatus.AVAILABLE)
    intelligent_mode_enabled = db.Column(db.Boolean, default=False)
    
    # Stripe integration (Mobile Only)
    stripe_account_id = db.Column(db.String(255), nullable=True)  # Stripe Connect account ID for payouts
    
    # Ratings and performance
    rating = db.Column(db.Numeric(3, 2), default=5.0)
    total_deliveries = db.Column(db.Integer, default=0)
    completed_deliveries = db.Column(db.Integer, default=0)
    cancelled_deliveries = db.Column(db.Integer, default=0)
    
    # Location tracking
    current_latitude = db.Column(db.Numeric(10, 8), nullable=True)
    current_longitude = db.Column(db.Numeric(11, 8), nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, **kwargs):
        # Extract password before passing to parent
        password = kwargs.pop('password', None)
        super(Driver, self).__init__(**kwargs)
        if password:
            self.set_password(password)
    
    def __repr__(self):
        return f'<Driver {self.email}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password).encode('utf-8')
    
    def check_password(self, password):
        """Check password hash"""
        try:
            if isinstance(self.password_hash, bytes):
                password_hash_str = self.password_hash.decode('utf-8')
            else:
                password_hash_str = self.password_hash
            
            # Check if this is a plain text password (not a proper hash)
            if not password_hash_str.startswith(('$2b$', '$2a$', '$2y$', 'scrypt:', 'pbkdf2:')):
                # This is a plain text password, compare directly
                return password_hash_str == password
            
            # This is a proper hash, use Werkzeug's check_password_hash
            return check_password_hash(password_hash_str, password)
        except Exception as e:
            print(f"Password check error in Driver model: {str(e)}")
            return False
    
    def to_dict(self):
        """Convert driver to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'license_number': self.license_number,
            'vehicle_type': self.vehicle_type,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_year': self.vehicle_year,
            'vehicle_plate_number': self.vehicle_plate_number,
            'driving_license_image': self.driving_license_image,
            'id_card_image': self.id_card_image,
            'insurance_image': self.insurance_image,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_available': self.is_available,
            'verification_status': self.verification_status,
            'status': self.status.value if self.status else DriverStatus.AVAILABLE.value,
            'intelligent_mode_enabled': self.intelligent_mode_enabled,
            'stripe_account_id': self.stripe_account_id,
            'rating': float(self.rating) if self.rating else 5.0,
            'total_deliveries': self.total_deliveries,
            'completed_deliveries': self.completed_deliveries,
            'cancelled_deliveries': self.cancelled_deliveries,
            'current_latitude': float(self.current_latitude) if self.current_latitude else None,
            'current_longitude': float(self.current_longitude) if self.current_longitude else None,
            'last_location_update': self.last_location_update.isoformat() if self.last_location_update else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None
        }
    
    def get_full_name(self):
        """Get driver's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def verify_driver(self):
        """Mark driver as verified"""
        self.is_verified = True
        self.verification_status = 'verified'
        self.updated_at = datetime.utcnow()
    
    def reject_driver(self, reason: str = None):
        """Reject driver verification"""
        self.verification_status = 'rejected'
        self.updated_at = datetime.utcnow()
        
        if reason:
            # Store rejection reason in metadata if needed
            pass
    
    def update_availability(self, is_available: bool):
        """Update driver availability"""
        self.is_available = is_available
        self.updated_at = datetime.utcnow()
        
        if is_available:
            self.last_active_at = datetime.utcnow()
    
    def set_status(self, status: DriverStatus):
        """Set driver status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status == DriverStatus.AVAILABLE:
            self.is_available = True
            self.last_active_at = datetime.utcnow()
        elif status == DriverStatus.BUSY:
            self.is_available = False
        elif status == DriverStatus.OFFLINE:
            self.is_available = False
    
    def update_rating(self, new_rating: float):
        """Update driver rating"""
        if 0.0 <= new_rating <= 5.0:
            self.rating = new_rating
            self.updated_at = datetime.utcnow()
    
    def increment_delivery_count(self, completed: bool = True):
        """Increment delivery count"""
        self.total_deliveries += 1
        if completed:
            self.completed_deliveries += 1
        else:
            self.cancelled_deliveries += 1
        
        self.updated_at = datetime.utcnow()
    
    def get_success_rate(self):
        """Get delivery success rate"""
        if self.total_deliveries == 0:
            return 0.0
        return (self.completed_deliveries / self.total_deliveries) * 100
    
    def update_location(self, latitude: float, longitude: float):
        """Update driver's current location"""
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.last_location_update = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def is_fully_verified(self):
        """Check if driver is fully verified"""
        return self.is_verified and self.verification_status == 'verified'
    
    @classmethod
    def get_by_email(cls, email: str):
        """Get driver by email"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_available_drivers(cls, vehicle_type: str = None, limit: int = 100):
        """Get available drivers"""
        query = cls.query.filter_by(is_active=True, is_available=True, is_verified=True)
        
        if vehicle_type:
            query = query.filter_by(vehicle_type=vehicle_type)
        
        return query.order_by(cls.rating.desc()).limit(limit).all()
    
    @classmethod
    def get_verified_drivers(cls, limit: int = 100):
        """Get verified drivers"""
        return cls.query.filter_by(is_verified=True, verification_status='verified').order_by(cls.rating.desc()).limit(limit).all() 