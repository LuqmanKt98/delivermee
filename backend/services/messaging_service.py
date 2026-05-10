import logging
from datetime import datetime
from models.message import Message, MessageType, MessageStatus
from models.delivery import Delivery
from models.user import Customer, Driver
from services.notification_service import notification_service
from extensions import db

logger = logging.getLogger(__name__)

class MessagingService:
    """Service for handling messaging between drivers and customers during deliveries"""
    
    def __init__(self):
        pass
    
    def send_driver_message(self, delivery_id, driver_id, customer_id, content, subject=None, is_urgent=False):
        """Send a message from driver to customer"""
        try:
            # Validate delivery exists and driver is assigned
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return False, "Delivery not found"
            
            if delivery.driver_id != driver_id:
                return False, "Driver not assigned to this delivery"
            
            # Create message
            message = Message(
                delivery_id=delivery_id,
                sender_id=driver_id,
                sender_type='driver',
                recipient_id=customer_id,
                recipient_type='customer',
                type=MessageType.DRIVER_TO_CUSTOMER,
                subject=subject,
                content=content,
                is_urgent=is_urgent
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Send notification to customer
            self._notify_customer_of_message(delivery_id, customer_id, message)
            
            logger.info(f"Driver {driver_id} sent message to customer {customer_id} for delivery {delivery_id}")
            return True, "Message sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending driver message: {str(e)}")
            return False, f"Error sending message: {str(e)}"
    
    def send_customer_message(self, delivery_id, customer_id, driver_id, content, subject=None, is_urgent=False):
        """Send a message from customer to driver"""
        try:
            # Validate delivery exists and customer owns it
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return False, "Delivery not found"
            
            if delivery.customer_id != customer_id:
                return False, "Customer not authorized for this delivery"
            
            # Create message
            message = Message(
                delivery_id=delivery_id,
                sender_id=customer_id,
                sender_type='customer',
                recipient_id=driver_id,
                recipient_type='driver',
                type=MessageType.CUSTOMER_TO_DRIVER,
                subject=subject,
                content=content,
                is_urgent=is_urgent
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Send notification to driver
            self._notify_driver_of_message(delivery_id, driver_id, message)
            
            logger.info(f"Customer {customer_id} sent message to driver {driver_id} for delivery {delivery_id}")
            return True, "Message sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending customer message: {str(e)}")
            return False, f"Error sending message: {str(e)}"
    
    def send_system_message(self, delivery_id, recipient_id, recipient_type, content, subject=None, is_urgent=False):
        """Send a system message to driver or customer"""
        try:
            # Create system message
            message = Message(
                delivery_id=delivery_id,
                sender_id=0,  # System sender
                sender_type='system',
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                type=MessageType.SYSTEM_NOTIFICATION,
                subject=subject,
                content=content,
                is_urgent=is_urgent
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Send notification
            if recipient_type == 'driver':
                self._notify_driver_of_message(delivery_id, recipient_id, message)
            elif recipient_type == 'customer':
                self._notify_customer_of_message(delivery_id, recipient_id, message)
            
            logger.info(f"System message sent to {recipient_type} {recipient_id} for delivery {delivery_id}")
            return True, "System message sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending system message: {str(e)}")
            return False, f"Error sending system message: {str(e)}"
    
    def send_delivery_update_message(self, delivery_id, recipient_id, recipient_type, update_content, subject=None):
        """Send delivery update message"""
        try:
            # Create delivery update message
            message = Message(
                delivery_id=delivery_id,
                sender_id=0,  # System sender
                sender_type='system',
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                type=MessageType.DELIVERY_UPDATE,
                subject=subject or "Delivery Update",
                content=update_content,
                is_urgent=False
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Send notification
            if recipient_type == 'driver':
                self._notify_driver_of_message(delivery_id, recipient_id, message)
            elif recipient_type == 'customer':
                self._notify_customer_of_message(delivery_id, recipient_id, message)
            
            logger.info(f"Delivery update message sent to {recipient_type} {recipient_id} for delivery {delivery_id}")
            return True, "Delivery update message sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending delivery update message: {str(e)}")
            return False, f"Error sending delivery update message: {str(e)}"
    
    def get_delivery_conversation(self, delivery_id, user_id, user_type, limit=50, offset=0):
        """Get conversation messages for a delivery"""
        try:
            # Validate user has access to this delivery
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return False, "Delivery not found"
            
            if user_type == 'driver' and delivery.driver_id != user_id:
                return False, "Driver not authorized for this delivery"
            elif user_type == 'customer' and delivery.customer_id != user_id:
                return False, "Customer not authorized for this delivery"
            
            # Get messages for this delivery
            messages = Message.query.filter_by(delivery_id=delivery_id)\
                .order_by(Message.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            # Mark messages as read if recipient is viewing
            for message in messages:
                if message.recipient_id == user_id and message.status == MessageStatus.DELIVERED:
                    message.mark_as_read()
            
            db.session.commit()
            
            # Convert to list and reverse to show oldest first
            message_list = [message.to_dict() for message in messages]
            message_list.reverse()
            
            return True, {
                'messages': message_list,
                'total': len(message_list),
                'delivery_id': delivery_id
            }
            
        except Exception as e:
            logger.error(f"Error getting delivery conversation: {str(e)}")
            return False, f"Error getting conversation: {str(e)}"
    
    def get_unread_message_count(self, user_id, user_type):
        """Get count of unread messages for a user"""
        try:
            if user_type == 'driver':
                # Get deliveries assigned to driver
                deliveries = Delivery.query.filter_by(driver_id=user_id).all()
                delivery_ids = [d.id for d in deliveries]
            elif user_type == 'customer':
                # Get deliveries owned by customer
                deliveries = Delivery.query.filter_by(customer_id=user_id).all()
                delivery_ids = [d.id for d in deliveries]
            else:
                return 0
            
            if not delivery_ids:
                return 0
            
            # Count unread messages
            unread_count = Message.query.filter(
                Message.delivery_id.in_(delivery_ids),
                Message.recipient_id == user_id,
                Message.status.in_([MessageStatus.SENT, MessageStatus.DELIVERED])
            ).count()
            
            return unread_count
            
        except Exception as e:
            logger.error(f"Error getting unread message count: {str(e)}")
            return 0
    
    def mark_message_as_read(self, message_id, user_id):
        """Mark a specific message as read"""
        try:
            message = Message.query.get(message_id)
            if not message:
                return False, "Message not found"
            
            if message.recipient_id != user_id:
                return False, "User not authorized to mark this message as read"
            
            message.mark_as_read()
            db.session.commit()
            
            return True, "Message marked as read"
            
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            return False, f"Error marking message as read: {str(e)}"
    
    def mark_all_messages_as_read(self, delivery_id, user_id):
        """Mark all messages in a delivery as read for a user"""
        try:
            # Validate user has access to this delivery
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return False, "Delivery not found"
            
            if delivery.driver_id != user_id and delivery.customer_id != user_id:
                return False, "User not authorized for this delivery"
            
            # Mark all unread messages as read
            unread_messages = Message.query.filter(
                Message.delivery_id == delivery_id,
                Message.recipient_id == user_id,
                Message.status.in_([MessageStatus.SENT, MessageStatus.DELIVERED])
            ).all()
            
            for message in unread_messages:
                message.mark_as_read()
            
            db.session.commit()
            
            return True, f"Marked {len(unread_messages)} messages as read"
            
        except Exception as e:
            logger.error(f"Error marking all messages as read: {str(e)}")
            return False, f"Error marking messages as read: {str(e)}"
    
    def _notify_driver_of_message(self, delivery_id, driver_id, message):
        """Send notification to driver about new message"""
        try:
            notification_service.notify_delivery_update(
                delivery_id=delivery_id,
                driver_id=driver_id,
                update_message=f"New message: {message.content[:100]}..."
            )
        except Exception as e:
            logger.error(f"Error notifying driver of message: {str(e)}")
    
    def _notify_customer_of_message(self, delivery_id, customer_id, message):
        """Send notification to customer about new message"""
        try:
            # In a real system, you'd implement customer notification service
            # For now, just log it
            logger.info(f"Customer {customer_id} should be notified of new message for delivery {delivery_id}")
        except Exception as e:
            logger.error(f"Error notifying customer of message: {str(e)}")
    
    def get_delivery_participants(self, delivery_id):
        """Get participants in a delivery conversation"""
        try:
            delivery = Delivery.query.get(delivery_id)
            if not delivery:
                return None
            
            participants = {
                'delivery_id': delivery_id,
                'customer': {
                    'id': delivery.customer_id,
                    'type': 'customer'
                },
                'driver': None
            }
            
            if delivery.driver_id:
                driver = Driver.query.get(delivery.driver_id)
                if driver:
                    participants['driver'] = {
                        'id': driver.id,
                        'type': 'driver',
                        'name': f"{driver.first_name} {driver.last_name}",
                        'phone': driver.phone_number
                    }
            
            return participants
            
        except Exception as e:
            logger.error(f"Error getting delivery participants: {str(e)}")
            return None

# Global messaging service instance
messaging_service = MessagingService()
