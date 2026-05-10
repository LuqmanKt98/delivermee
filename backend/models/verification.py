from extensions import db
from datetime import datetime, timedelta
import secrets
import string

class VerificationCode(db.Model):
    __tablename__ = 'verification_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    code = db.Column(db.String(6), nullable=False)
    verification_type = db.Column(db.String(20), nullable=False)  # 'phone', 'email', 'forgot_password'
    user_type = db.Column(db.String(20), nullable=False)  # 'customer', 'driver'
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, email=None, phone_number=None, verification_type='phone', user_type='customer'):
        self.email = email
        self.phone_number = phone_number
        self.verification_type = verification_type
        self.user_type = user_type
        self.code = self._generate_code()
        self.expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
    
    def _generate_code(self):
        """Generate a 6-digit verification code"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    def is_expired(self):
        """Check if the verification code has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if the verification code is valid and not used"""
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark the verification code as used"""
        self.is_used = True
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'phone_number': self.phone_number,
            'verification_type': self.verification_type,
            'user_type': self.user_type,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<VerificationCode {self.verification_type} for {self.email or self.phone_number}>'

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    token = db.Column(db.String(64), nullable=False, unique=True)
    user_type = db.Column(db.String(20), nullable=False)  # 'customer', 'driver'
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, email, phone_number=None, user_type='customer'):
        self.email = email
        self.phone_number = phone_number
        self.user_type = user_type
        self.token = self._generate_token()
        self.expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    
    def _generate_token(self):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        """Check if the reset token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if the reset token is valid and not used"""
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark the reset token as used"""
        self.is_used = True
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'phone_number': self.phone_number,
            'user_type': self.user_type,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<PasswordResetToken for {self.email}>' 