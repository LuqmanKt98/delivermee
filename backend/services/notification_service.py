import requests
import json
import logging
from datetime import datetime, timedelta
from models.notification import Notification, NotificationType, NotificationStatus
from models.ride import Ride
from models.user import Driver
from models.delivery import Delivery
from extensions import db
from settings import USE_FIREBASE_DB
from repositories.notification_repository import NotificationRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    """Service for handling driver notifications"""
    
    def __init__(self):
        # Configuration for different notification channels
        self.fcm_server_key = "YOUR_FCM_SERVER_KEY"  # Firebase Cloud Messaging
        self.twilio_account_sid = "YOUR_TWILIO_ACCOUNT_SID"
        self.twilio_auth_token = "YOUR_TWILIO_AUTH_TOKEN"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_username = "your-email@gmail.com"
        self.smtp_password = "your-app-password"
    
    def notify_ride_assignment(self, ride_id, driver_id):
        """Notify driver about a new ride assignment"""
        try:
            ride = Ride.query.get(ride_id)
            driver = Driver.query.get(driver_id)
            
            if not ride or not driver:
                logger.error(f"Ride {ride_id} or Driver {driver_id} not found")
                return False
            
            # Create notification record
            title = "New Ride Assignment"
            message = f"New ride from {ride.pickup_address} to {ride.dropoff_address}. Estimated fare: ${ride.estimated_cost}"
            
            notification = Notification(
                driver_id=driver_id,
                ride_id=ride_id,
                type=NotificationType.RIDE_ASSIGNMENT,
                title=title,
                message=message
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send notifications through different channels
            success = False
            
            # 1. Push Notification (highest priority)
            if driver.push_token:
                success = self.send_push_notification(notification, driver)
            
            # 2. SMS (fallback)
            if not success and driver.phone_number:
                success = self.send_sms_notification(notification, driver)
            
            # 3. Email (lowest priority)
            if not success and driver.email:
                success = self.send_email_notification(notification, driver)
            
            # Update notification status
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver_id} about ride {ride_id}: {str(e)}")
            return False

    def notify_delivery_assignment(self, delivery_id, driver_id, response_deadline_minutes=15):
        """Notify driver about a new delivery assignment with response tracking"""
        try:
            delivery = Delivery.query.get(delivery_id)
            driver = Driver.query.get(driver_id)
            
            if not delivery or not driver:
                logger.error(f"Delivery {delivery_id} or Driver {driver_id} not found")
                return False
            
            # Create notification record with response tracking
            title = "New Delivery Request"
            message = f"New delivery: {delivery.item_name} from {delivery.pickup_address} to {delivery.dropoff_address}. Estimated fare: ${delivery.estimated_cost}. Please respond within {response_deadline_minutes} minutes."
            
            notification = Notification(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=NotificationType.DELIVERY_ASSIGNMENT,
                title=title,
                message=message,
                response_required=True
            )
            
            # Set response deadline
            notification.set_response_deadline(response_deadline_minutes)
            
            db.session.add(notification)
            db.session.commit()
            
            # Send notifications through different channels
            success = False
            
            # 1. Push Notification (highest priority)
            if driver.push_token:
                success = self.send_push_notification(notification, driver)
            
            # 2. SMS (fallback)
            if not success and driver.phone_number:
                success = self.send_sms_notification(notification, driver)
            
            # 3. Email (lowest priority)
            if not success and driver.email:
                success = self.send_email_notification(notification, driver)
            
            # Update notification status
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            
            # Schedule expiration check
            self._schedule_notification_expiration(notification.id, response_deadline_minutes)
            
            return success
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver_id} about delivery {delivery_id}: {str(e)}")
            return False

    def notify_delivery_cancellation(self, delivery_id, driver_id):
        """Notify driver about delivery cancellation"""
        try:
            delivery = Delivery.query.get(delivery_id)
            driver = Driver.query.get(driver_id)
            
            if not delivery or not driver:
                return False
            
            title = "Delivery Cancelled"
            message = f"Delivery {delivery.tracking_number} has been cancelled by the customer."
            
            notification = Notification(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=NotificationType.DELIVERY_CANCELLATION,
                title=title,
                message=message
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send notification
            success = self.send_push_notification(notification, driver)
            if not success:
                success = self.send_sms_notification(notification, driver)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver_id} about delivery cancellation {delivery_id}: {str(e)}")
            return False

    def notify_delivery_update(self, delivery_id, driver_id, update_message):
        """Notify driver about delivery updates"""
        try:
            delivery = Delivery.query.get(delivery_id)
            driver = Driver.query.get(driver_id)
            
            if not delivery or not driver:
                return False
            
            title = "Delivery Update"
            message = f"Update for delivery {delivery.tracking_number}: {update_message}"
            
            notification = Notification(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=NotificationType.DELIVERY_UPDATE,
                title=title,
                message=message
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send notification
            success = self.send_push_notification(notification, driver)
            if not success:
                success = self.send_sms_notification(notification, driver)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver_id} about delivery update {delivery_id}: {str(e)}")
            return False

    def notify_ride_cancellation(self, ride_id, driver_id):
        """Notify driver about ride cancellation"""
        try:
            ride = Ride.query.get(ride_id)
            driver = Driver.query.get(driver_id)
            
            if not ride or not driver:
                return False
            
            title = "Ride Cancelled"
            message = f"Ride from {ride.pickup_address} to {ride.dropoff_address} has been cancelled."
            
            notification = Notification(
                driver_id=driver_id,
                ride_id=ride_id,
                type=NotificationType.RIDE_CANCELLATION,
                title=title,
                message=message
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send notification
            success = self.send_push_notification(notification, driver)
            if not success:
                success = self.send_sms_notification(notification, driver)
            
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver_id} about ride cancellation {ride_id}: {str(e)}")
            return False

    def send_push_notification(self, notification, driver):
        """Send push notification via Firebase Cloud Messaging"""
        try:
            if not driver.push_token:
                return False
            
            # FCM payload
            payload = {
                "to": driver.push_token,
                "notification": {
                    "title": notification.title,
                    "body": notification.message,
                    "sound": "default",
                    "badge": "1"
                },
                "data": {
                    "notification_id": str(notification.id),
                    "type": notification.type.value,
                    "delivery_id": str(notification.delivery_id) if notification.delivery_id else "",
                    "ride_id": str(notification.ride_id) if notification.ride_id else "",
                    "response_required": str(notification.response_required).lower(),
                    "response_deadline": notification.response_deadline.isoformat() if notification.response_deadline else ""
                },
                "priority": "high"
            }
            
            headers = {
                "Authorization": f"key={self.fcm_server_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://fcm.googleapis.com/fcm/send",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success") == 1:
                    logger.info(f"Push notification sent successfully to driver {driver.id}")
                    return True
                else:
                    logger.error(f"FCM error: {result}")
                    return False
            else:
                logger.error(f"FCM request failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return False
    
    def send_sms_notification(self, notification, driver):
        """Send SMS notification via Twilio"""
        try:
            if not driver.phone_number:
                return False
            
            # Twilio SMS API
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            
            # Add response instructions for delivery assignments
            message_body = f"{notification.title}: {notification.message}"
            if notification.response_required:
                message_body += f"\n\nReply ACCEPT to accept or REJECT to reject within {notification.response_deadline.minute if notification.response_deadline else 15} minutes."
            
            data = {
                "To": driver.phone_number,
                "From": "+1234567890",  # Your Twilio phone number
                "Body": message_body
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent successfully to driver {driver.id}")
                return True
            else:
                logger.error(f"Twilio SMS failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False
    
    def send_email_notification(self, notification, driver):
        """Send email notification"""
        try:
            if not driver.email:
                return False
            
            # For simplicity, using a mock email service
            # In production, use a proper email service like SendGrid, AWS SES, etc.
            logger.info(f"Email notification would be sent to {driver.email}: {notification.title}")
            
            # Mock successful email sending
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    def get_driver_notifications(self, driver_id, limit=20, offset=0):
        """Get notifications for a specific driver"""
        try:
            if USE_FIREBASE_DB:
                return NotificationRepository().list_for_driver(driver_id, limit=limit, offset=offset)

            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-07)
            # notifications = Notification.query.filter_by(driver_id=driver_id)\
            #     .order_by(Notification.created_at.desc())\
            #     .offset(offset)\
            #     .limit(limit)\
            #     .all()
            #
            # return [notification.to_dict() for notification in notifications]
            return []
            
        except Exception as e:
            logger.error(f"Error getting notifications for driver {driver_id}: {str(e)}")
            return []

    def get_delivery_notifications(self, delivery_id, limit=20, offset=0):
        """Get notifications for a specific delivery"""
        try:
            notifications = Notification.query.filter_by(delivery_id=delivery_id)\
                .order_by(Notification.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            return [notification.to_dict() for notification in notifications]
            
        except Exception as e:
            logger.error(f"Error getting notifications for delivery {delivery_id}: {str(e)}")
            return []

    def mark_notification_as_read(self, notification_id, driver_id):
        """Mark a notification as read"""
        try:
            if USE_FIREBASE_DB:
                doc = NotificationRepository().get_for_driver(notification_id, driver_id)
                if not doc:
                    return False
                return NotificationRepository().mark_read(notification_id)

            # ORM_DISABLED: replaced by Firestore implementation (date: 2026-02-07)
            # notification = Notification.query.filter_by(
            #     id=notification_id,
            #     driver_id=driver_id
            # ).first()
            #
            # if notification:
            #     notification.mark_as_read()
            #     db.session.commit()
            #     return True
            #
            # return False
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
            return False

    def get_notification_by_delivery(self, driver_id, delivery_id, notification_type):
        """Get notification by delivery and type"""
        try:
            notification = Notification.query.filter_by(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=notification_type
            ).first()
            
            return notification
            
        except Exception as e:
            logger.error(f"Error getting notification for delivery {delivery_id}: {str(e)}")
            return None

    def handle_delivery_response(self, notification_id, driver_id, response_action):
        """Handle driver's response to delivery assignment"""
        try:
            notification = Notification.query.filter_by(
                id=notification_id,
                driver_id=driver_id
            ).first()
            
            if not notification:
                return False, "Notification not found"
            
            if not notification.response_required:
                return False, "Notification does not require response"
            
            if notification.response_received:
                return False, "Response already received"
            
            if notification.is_expired():
                notification.mark_as_expired()
                db.session.commit()
                return False, "Response deadline expired"
            
            # Update notification with response
            notification.response_received = True
            notification.response_action = response_action
            notification.mark_as_read()
            
            # Update delivery status based on response
            if notification.delivery_id:
                delivery = Delivery.query.get(notification.delivery_id)
                if delivery:
                    if response_action == 'accepted':
                        delivery.status = 'ACCEPTED'
                        delivery.accepted_time = datetime.utcnow()
                        
                        # Update driver status
                        driver = Driver.query.get(driver_id)
                        if driver:
                            driver.status = 'BUSY'
                    elif response_action == 'rejected':
                        delivery.status = 'REQUESTED'
                        delivery.driver_id = None
                        delivery.assigned_time = None
                        
                        # Try to assign to another driver
                        self._reassign_delivery_to_another_driver(delivery)
            
            db.session.commit()
            return True, f"Delivery {response_action} successfully"
            
        except Exception as e:
            logger.error(f"Error handling delivery response: {str(e)}")
            return False, f"Error processing response: {str(e)}"

    def _reassign_delivery_to_another_driver(self, delivery):
        """Reassign delivery to another available driver"""
        try:
            from routes.delivery_routes import assign_driver_to_delivery
            new_driver = assign_driver_to_delivery(delivery)
            if new_driver:
                logger.info(f"Delivery {delivery.id} reassigned to driver {new_driver.id}")
            else:
                logger.warning(f"No available drivers for delivery {delivery.id}")
        except Exception as e:
            logger.error(f"Error reassigning delivery {delivery.id}: {str(e)}")

    def _schedule_notification_expiration(self, notification_id, minutes):
        """Schedule notification expiration check"""
        try:
            # In a production system, use a task queue like Celery
            # For now, we'll handle expiration in the response handling
            logger.info(f"Notification {notification_id} will expire in {minutes} minutes")
        except Exception as e:
            logger.error(f"Error scheduling notification expiration: {str(e)}")

    def retry_failed_notifications(self):
        """Retry sending failed notifications"""
        try:
            failed_notifications = Notification.query.filter_by(
                status=NotificationStatus.FAILED
            ).filter(
                Notification.delivery_attempts < Notification.max_attempts
            ).all()
            
            for notification in failed_notifications:
                driver = Driver.query.get(notification.driver_id)
                if driver:
                    success = self.send_push_notification(notification, driver)
                    if not success:
                        success = self.send_sms_notification(notification, driver)
                    
                    if success:
                        notification.mark_as_sent()
                    else:
                        notification.mark_as_failed()
            
            db.session.commit()
            return len(failed_notifications)
            
        except Exception as e:
            logger.error(f"Error retrying failed notifications: {str(e)}")
            return 0

    def cleanup_expired_notifications(self):
        """Clean up expired notifications"""
        try:
            expired_notifications = Notification.query.filter(
                Notification.response_required == True,
                Notification.response_deadline < datetime.utcnow(),
                Notification.response_received == False
            ).all()
            
            for notification in expired_notifications:
                notification.mark_as_expired()
                
                # Reassign delivery if it was assigned to this driver
                if notification.delivery_id:
                    delivery = Delivery.query.get(notification.delivery_id)
                    if delivery and delivery.driver_id == notification.driver_id:
                        delivery.status = 'REQUESTED'
                        delivery.driver_id = None
                        delivery.assigned_time = None
                        
                        # Try to assign to another driver
                        self._reassign_delivery_to_another_driver(delivery)
            
            db.session.commit()
            return len(expired_notifications)
            
        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {str(e)}")
            return 0

# Global notification service instance
notification_service = NotificationService() 