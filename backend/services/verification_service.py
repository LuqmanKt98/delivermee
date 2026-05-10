import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
# ORM_DISABLED: PostgreSQL/SQLAlchemy models kept for reference (date: 2026-02-12)
# from models.verification import VerificationCode, PasswordResetToken
# from extensions import db
import logging
import secrets

from settings import USE_FIREBASE_DB
from repositories.customer_repository import CustomerRepository
from repositories.driver_repository import DriverRepository
from repositories.password_reset_repository import PasswordResetRepository
from repositories.verification_code_repository import VerificationCodeRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VerificationService:
    def __init__(self):
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        # SMS configuration (using Twilio as example)
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER', '')
        
        # For development/testing, you can use a mock SMS service
        self.use_mock_sms = os.getenv('USE_MOCK_SMS', 'true').lower() == 'true'
    
    def send_verification_code(self, email=None, phone_number=None, verification_type='phone', user_type='customer'):
        """
        Send verification code via SMS or email
        """
        try:
            if USE_FIREBASE_DB:
                repo = VerificationCodeRepository()
                doc = repo.create(
                    email=email,
                    phone_number=phone_number,
                    verification_type=verification_type,
                    user_type=user_type,
                    ttl_minutes=10,
                )

                # Send the code
                if verification_type == 'phone' and phone_number:
                    return self._send_sms(phone_number, doc["code"])
                elif verification_type == 'email' and email:
                    return self._send_email(email, doc["code"])
                else:
                    return False, "Invalid verification type or missing contact info"

            # Create verification code
            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-12)
            # verification_code = VerificationCode(
            #     email=email,
            #     phone_number=phone_number,
            #     verification_type=verification_type,
            #     user_type=user_type
            # )
            # db.session.add(verification_code)
            # db.session.commit()
            # if verification_type == 'phone' and phone_number:
            #     return self._send_sms(phone_number, verification_code.code)
            # elif verification_type == 'email' and email:
            #     return self._send_email(email, verification_code.code)
            # else:
            #     return False, "Invalid verification type or missing contact info"
            return False, "PostgreSQL verification codes disabled (Firebase migration)"
                
        except Exception as e:
            logger.error(f"Error sending verification code: {str(e)}")
            # ORM_DISABLED: db.session.rollback() (date: 2026-02-12)
            # db.session.rollback()
            return False, str(e)
    
    def verify_code(self, email=None, phone_number=None, code=None, user_type='customer'):
        """
        Verify the provided code
        """
        try:
            if USE_FIREBASE_DB:
                repo = VerificationCodeRepository()
                doc = repo.get_latest_unused(
                    email=email,
                    phone_number=phone_number,
                    verification_type="email" if email else "phone",
                    user_type=user_type,
                )
                if not doc:
                    return False, "No verification code found"
                expires_at = doc.get("expires_at")
                if expires_at and datetime.utcnow() > expires_at:
                    return False, "Verification code has expired"
                if str(doc.get("code")) != str(code):
                    return False, "Invalid verification code"
                repo.mark_used(doc["id"])
                return True, "Verification successful"

            # Find the verification code
            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-12)
            # query = VerificationCode.query.filter_by(
            #     user_type=user_type,
            #     is_used=False
            # )
            # if email:
            #     query = query.filter_by(email=email)
            # elif phone_number:
            #     query = query.filter_by(phone_number=phone_number)
            # else:
            #     return False, "Email or phone number required"
            # verification_code = query.order_by(VerificationCode.created_at.desc()).first()
            # if not verification_code:
            #     return False, "No verification code found"
            # if verification_code.is_expired():
            #     return False, "Verification code has expired"
            # if verification_code.code != code:
            #     return False, "Invalid verification code"
            # verification_code.mark_as_used()
            # return True, "Verification successful"
            return False, "PostgreSQL verification codes disabled (Firebase migration)"
            
        except Exception as e:
            logger.error(f"Error verifying code: {str(e)}")
            return False, str(e)
    
    def send_password_reset_otp(self, email, user_type='customer'):
        """
        Generate a 6-digit OTP and email it for password reset.
        """
        try:
            if user_type == 'driver':
                user = DriverRepository().get_by_email(email)
            else:
                user = CustomerRepository().get_by_email(email)
            if not user:
                return False, 'User not found'

            repo = VerificationCodeRepository()
            doc = repo.create(
                email=email,
                phone_number=None,
                verification_type='email',
                user_type=user_type,
                ttl_minutes=10,
            )
            return self._send_otp_email(email, doc['code'], user_type)
        except Exception as e:
            logger.error(f'Error sending password reset OTP: {str(e)}')
            return False, str(e)

    def send_password_reset_otp_phone(self, phone_number, user_type='customer'):
        """
        Generate a 6-digit OTP and send via SMS for password reset.
        """
        try:
            # Normalize phone: ensure it starts with +
            normalized = phone_number.strip()
            if not normalized.startswith('+'):
                normalized = '+' + normalized

            if user_type == 'driver':
                user = DriverRepository().get_by_phone(normalized)
            else:
                user = CustomerRepository().get_by_phone(normalized)
            if not user:
                return False, 'User not found'

            repo = VerificationCodeRepository()
            doc = repo.create(
                email=None,
                phone_number=normalized,
                verification_type='phone',
                user_type=user_type,
                ttl_minutes=10,
            )
            return self._send_sms(normalized, doc['code'])
        except Exception as e:
            logger.error(f'Error sending phone OTP: {str(e)}')
            return False, str(e)

    def verify_password_reset_otp_phone(self, phone_number, otp, user_type='customer'):
        """
        Verify the 6-digit SMS OTP and mark it used.
        """
        try:
            normalized = phone_number.strip()
            if not normalized.startswith('+'):
                normalized = '+' + normalized

            repo = VerificationCodeRepository()
            doc = repo.get_latest_unused(
                email=None,
                phone_number=normalized,
                verification_type='phone',
                user_type=user_type,
            )
            if not doc:
                return False, 'No OTP found. Please request a new one.'
            expires_at = doc.get('expires_at')
            if expires_at and datetime.utcnow() > expires_at:
                return False, 'OTP has expired. Please request a new one.'
            if str(doc.get('code')) != str(otp):
                return False, 'Invalid OTP. Please try again.'
            repo.mark_used(doc['id'])
            return True, 'OTP verified successfully'
        except Exception as e:
            logger.error(f'Error verifying phone OTP: {str(e)}')
            return False, str(e)

    def reset_password_with_otp_phone(self, phone_number, otp, new_password, user_type='customer'):
        """
        Verify SMS OTP and reset password.
        """
        success, message = self.verify_password_reset_otp_phone(phone_number, otp, user_type)
        if not success:
            return False, message
        try:
            normalized = phone_number.strip()
            if not normalized.startswith('+'):
                normalized = '+' + normalized
            if user_type == 'driver':
                ok = DriverRepository().set_password_by_phone(normalized, new_password)
            else:
                ok = CustomerRepository().set_password_by_phone(normalized, new_password)
            if not ok:
                return False, 'User not found'
            return True, 'Password reset successful'
        except Exception as e:
            logger.error(f'Error resetting password with phone OTP: {str(e)}')
            return False, str(e)

    def verify_password_reset_otp(self, email, otp, user_type='customer'):
        """
        Verify the 6-digit OTP without consuming it (so reset_password_with_otp can reuse it).
        Returns (success: bool, message: str)
        """
        try:
            repo = VerificationCodeRepository()
            doc = repo.get_latest_unused(
                email=email,
                phone_number=None,
                verification_type='email',
                user_type=user_type,
            )
            if not doc:
                return False, 'No OTP found. Please request a new one.'
            expires_at = doc.get('expires_at')
            if expires_at and datetime.utcnow() > expires_at:
                return False, 'OTP has expired. Please request a new one.'
            if str(doc.get('code')) != str(otp):
                return False, 'Invalid OTP. Please try again.'
            # Mark used so it cannot be reused
            repo.mark_used(doc['id'])
            return True, 'OTP verified successfully'
        except Exception as e:
            logger.error(f'Error verifying password reset OTP: {str(e)}')
            return False, str(e)

    def reset_password_with_otp(self, email, otp, new_password, user_type='customer'):
        """
        Verify OTP and reset password in one step.
        Returns (success: bool, message: str)
        """
        success, message = self.verify_password_reset_otp(email, otp, user_type)
        if not success:
            return False, message
        try:
            if user_type == 'driver':
                ok = DriverRepository().set_password_by_email(email, new_password)
            else:
                ok = CustomerRepository().set_password_by_email(email, new_password)
            if not ok:
                return False, 'User not found'
            return True, 'Password reset successful'
        except Exception as e:
            logger.error(f'Error resetting password with OTP: {str(e)}')
            return False, str(e)

    def _send_otp_email(self, email, code, user_type):
        """
        Send 6-digit OTP via email.
        """
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.warning('SMTP credentials not configured, using mock email')
                logger.info(f'MOCK EMAIL to {email}: Your DeliverMee OTP is {code}')
                return True, 'OTP sent successfully'

            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = 'DeliverMee - Password Reset OTP'
            body = f"""Hello,

Your password reset OTP for your DeliverMee {user_type} account is:

  {code}

This code is valid for 10 minutes.

If you did not request a password reset, please ignore this email.

— The DeliverMee Team
"""
            msg.attach(MIMEText(body, 'plain'))
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.smtp_username, email, msg.as_string())
            server.quit()
            return True, 'OTP sent successfully'
        except Exception as e:
            logger.error(f'Error sending OTP email: {str(e)}')
            return False, str(e)

    def create_password_reset_token(self, email, user_type='customer'):
        """
        Create a password reset token
        """
        try:
            if USE_FIREBASE_DB:
                if user_type == "driver":
                    user = DriverRepository().get_by_email(email)
                else:
                    user = CustomerRepository().get_by_email(email)
                if not user:
                    return False, "User not found"

                token = secrets.token_urlsafe(32)
                PasswordResetRepository().create(email=email, user_type=user_type, token=token)
                return self._send_password_reset_email(email, token, user_type)

            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-07)
            # Check if user exists
            # if user_type == 'customer':
            #     from models.user import Customer
            #     user = Customer.query.filter_by(email=email).first()
            # else:
            #     from models.user import Driver
            #     user = Driver.query.filter_by(email=email).first()
            #
            # if not user:
            #     return False, "User not found"
            #
            # # Create reset token
            # reset_token = PasswordResetToken(
            #     email=email,
            #     user_type=user_type
            # )
            #
            # db.session.add(reset_token)
            # db.session.commit()
            #
            # # Send reset email
            # return self._send_password_reset_email(email, reset_token.token, user_type)
            return False, "PostgreSQL password reset flow disabled (Firebase migration)"
            
        except Exception as e:
            logger.error(f"Error creating password reset token: {str(e)}")
            # ORM_DISABLED: db.session.rollback() (date: 2026-02-07)
            # db.session.rollback()
            return False, str(e)
    
    def verify_reset_token(self, token):
        """
        Verify password reset token
        """
        try:
            if USE_FIREBASE_DB:
                doc = PasswordResetRepository().get(token)
                if not doc:
                    return False, "Invalid reset token"
                if doc.get("is_used"):
                    return False, "Reset token already used"
                expires_at = doc.get("expires_at")
                if expires_at and datetime.utcnow() > expires_at:
                    return False, "Reset token has expired"
                return True, doc

            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-07)
            # reset_token = PasswordResetToken.query.filter_by(token=token).first()
            # if not reset_token:
            #     return False, "Invalid reset token"
            # if reset_token.is_expired():
            #     return False, "Reset token has expired"
            # if reset_token.is_used:
            #     return False, "Reset token already used"
            # return True, reset_token
            return False, "PostgreSQL reset tokens disabled (Firebase migration)"
            
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return False, str(e)
    
    def reset_password(self, token, new_password):
        """
        Reset password using token
        """
        try:
            success, result = self.verify_reset_token(token)
            if not success:
                return False, result

            if USE_FIREBASE_DB:
                reset_doc = result

                user_type = reset_doc.get("user_type")
                email = reset_doc.get("email")
                if not user_type or not email:
                    return False, "Invalid reset token payload"

                if user_type == "driver":
                    ok = DriverRepository().set_password_by_email(email, new_password)
                else:
                    ok = CustomerRepository().set_password_by_email(email, new_password)
                if not ok:
                    return False, "User not found"

                PasswordResetRepository().mark_used(token)
                return True, "Password reset successful"

            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-07)
            # reset_token = result
            #
            # # Update user password
            # if reset_token.user_type == 'customer':
            #     from models.user import Customer
            #     user = Customer.query.filter_by(email=reset_token.email).first()
            # else:
            #     from models.user import Driver
            #     user = Driver.query.filter_by(email=reset_token.email).first()
            #
            # if not user:
            #     return False, "User not found"
            #
            # # Set new password
            # user.set_password(new_password)
            #
            # # Mark token as used
            # reset_token.mark_as_used()
            #
            # db.session.commit()
            #
            # return True, "Password reset successful"
            return False, "PostgreSQL reset password flow disabled (Firebase migration)"
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            # ORM_DISABLED: db.session.rollback() (date: 2026-02-07)
            # db.session.rollback()
            return False, str(e)
    
    def _send_sms(self, phone_number, code):
        """
        Send SMS OTP via Twilio. Falls back to mock log if credentials not set.
        """
        try:
            if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
                logger.warning('Twilio credentials not configured, using mock SMS')
                logger.info(f'MOCK SMS to {phone_number}: Your DeliverMee OTP is {code}')
                return True, 'OTP sent successfully'

            url = f'https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json'
            data = {
                'From': self.twilio_phone_number,
                'To': phone_number,
                'Body': f'Your DeliverMee password reset OTP is: {code}. Valid for 10 minutes.',
            }
            response = requests.post(url, data=data, auth=(self.twilio_account_sid, self.twilio_auth_token))
            if response.status_code == 201:
                return True, 'OTP sent successfully'
            logger.error(f'Twilio SMS error: {response.text}')
            return False, 'Failed to send SMS'
        except Exception as e:
            logger.error(f'Error sending SMS: {str(e)}')
            return False, str(e)
    
    def _send_email(self, email, code):
        """
        Send email verification code
        """
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.warning("SMTP credentials not configured, using mock email")
                logger.info(f"MOCK EMAIL to {email}: Your verification code is {code}")
                return True, "Email sent successfully (mock)"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = "Verification Code"
            
            body = f"""
            Your verification code is: {code}
            
            This code is valid for 10 minutes.
            
            If you didn't request this code, please ignore this email.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_username, email, text)
            server.quit()
            
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False, str(e)
    
    def _send_password_reset_email(self, email, token, user_type):
        """
        Send password reset email
        """
        try:
            if not all([self.smtp_username, self.smtp_password]):
                logger.warning("SMTP credentials not configured, using mock email")
                reset_url = f"http://localhost:3000/reset-password?token={token}&type={user_type}"
                logger.info(f"MOCK EMAIL to {email}: Password reset link: {reset_url}")
                return True, "Password reset email sent successfully (mock)"
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email
            msg['Subject'] = "Password Reset Request"
            
            reset_url = f"http://localhost:3000/reset-password?token={token}&type={user_type}"
            
            body = f"""
            You requested a password reset for your {user_type} account.
            
            Click the following link to reset your password:
            {reset_url}
            
            This link is valid for 1 hour.
            
            If you didn't request this reset, please ignore this email.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_username, email, text)
            server.quit()
            
            return True, "Password reset email sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return False, str(e)

# Create global instance
verification_service = VerificationService() 