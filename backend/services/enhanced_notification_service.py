import requests
import json
import logging
from datetime import datetime, timedelta
from models.notification import Notification, NotificationType, NotificationStatus
from models.delivery import Delivery
from models.user import Driver
from extensions import db
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class EnhancedNotificationService(NotificationService):
    """
    Enhanced notification service with intelligent delivery alerts,
    real-time updates, and seamless driver communication
    """
    
    def __init__(self):
        super().__init__()
        self.priority_levels = {
            'urgent': {'sound': 'urgent.mp3', 'vibration': [0, 500, 200, 500]},
            'high': {'sound': 'high.mp3', 'vibration': [0, 300, 100, 300]},
            'normal': {'sound': 'normal.mp3', 'vibration': [0, 200]},
            'low': {'sound': None, 'vibration': [0, 100]}
        }
    
    def send_intelligent_delivery_notification(self, driver_id: int, assignments: list, metadata: dict = None) -> bool:
        """
        Send intelligent notification for delivery assignments with enhanced features
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver:
                logger.error(f"Driver {driver_id} not found")
                return False
            
            # Determine notification priority based on earnings and urgency
            total_earnings = sum(float(assignment.get('estimated_cost', 0)) for assignment in assignments)
            batch_size = len(assignments)
            
            # Calculate priority
            if total_earnings > 50 or batch_size > 2:
                priority = 'urgent'
            elif total_earnings > 25 or batch_size > 1:
                priority = 'high'
            else:
                priority = 'normal'
            
            # Create notification content
            if batch_size == 1:
                assignment = assignments[0]
                title = f"Perfect Match! ${assignment.get('estimated_cost', 0):.2f}"
                message = f"High-value delivery: {assignment.get('item_name', 'Package')} - {assignment.get('distance_from_driver', 0):.1f}km away"
                notification_type = 'smart_single_delivery'
            else:
                title = f"Smart Batch! ${total_earnings:.2f} ({batch_size} deliveries)"
                message = f"Optimized route with {batch_size} stops - Estimated {metadata.get('total_duration', 30)} mins"
                notification_type = 'smart_batch_delivery'
            
            # Add contextual information
            if metadata:
                if metadata.get('auto_accepted'):
                    message += " - Auto-accepted"
                if metadata.get('optimal_route'):
                    message += " - Route optimized"
            
            # Create enhanced notification
            notification = Notification(
                driver_id=driver_id,
                delivery_id=assignments[0].get('delivery_id') if assignments else None,
                type=NotificationType.DELIVERY_ASSIGNMENT,
                title=title,
                message=message,
                priority=priority,
                metadata={
                    'assignments': assignments,
                    'batch_size': batch_size,
                    'total_earnings': total_earnings,
                    'notification_type': notification_type,
                    **(metadata or {})
                }
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send through multiple channels with priority settings
            success = self._send_enhanced_push_notification(notification, driver, priority)
            
            # Fallback to SMS for urgent notifications
            if not success and priority in ['urgent', 'high'] and driver.sms_notifications:
                success = self.send_sms_notification(notification, driver)
            
            # Update notification status
            if success:
                notification.mark_as_sent()
            else:
                notification.mark_as_failed()
            
            db.session.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error sending intelligent delivery notification: {str(e)}")
            return False
    
    def _send_enhanced_push_notification(self, notification: Notification, driver: Driver, priority: str) -> bool:
        """
        Send enhanced push notification with custom sound, vibration, and actions
        """
        try:
            if not driver.push_token:
                return False
            
            priority_config = self.priority_levels.get(priority, self.priority_levels['normal'])
            
            # Enhanced push notification payload
            payload = {
                'to': driver.push_token,
                'notification': {
                    'title': notification.title,
                    'body': notification.message,
                    'sound': priority_config.get('sound', 'default'),
                    'badge': 1,
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                    'channel_id': f'delivery_notifications_{priority}'
                },
                'data': {
                    'notification_id': str(notification.id),
                    'delivery_id': str(notification.delivery_id) if notification.delivery_id else '',
                    'priority': priority,
                    'type': notification.metadata.get('notification_type', 'delivery'),
                    'vibration_pattern': json.dumps(priority_config.get('vibration', [0, 200])),
                    'auto_cancel': 'false' if priority == 'urgent' else 'true',
                    'actions': json.dumps(self._get_notification_actions(notification)),
                    'metadata': json.dumps(notification.metadata or {})
                },
                'android': {
                    'priority': 'high' if priority in ['urgent', 'high'] else 'normal',
                    'notification': {
                        'channel_id': f'delivery_notifications_{priority}',
                        'sound': priority_config.get('sound', 'default'),
                        'vibrate_timings': priority_config.get('vibration', [0, 200]),
                        'sticky': priority == 'urgent',
                        'local_only': False,
                        'default_vibrate_timings': False
                    }
                },
                'apns': {
                    'payload': {
                        'aps': {
                            'sound': priority_config.get('sound', 'default'),
                            'badge': 1,
                            'alert': {
                                'title': notification.title,
                                'body': notification.message
                            },
                            'category': f'DELIVERY_CATEGORY_{priority.upper()}'
                        }
                    }
                }
            }
            
            headers = {
                'Authorization': f'key={self.fcm_server_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                data=json.dumps(payload),
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success', 0) > 0:
                    logger.info(f"Enhanced push notification sent successfully to driver {driver.id}")
                    return True
                else:
                    logger.error(f"FCM error: {response_data.get('results', [{}])[0].get('error', 'Unknown')}")
                    return False
            else:
                logger.error(f"FCM request failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending enhanced push notification: {str(e)}")
            return False
    
    def _get_notification_actions(self, notification: Notification) -> list:
        """
        Get context-aware notification actions based on notification type and content
        """
        actions = []
        
        notification_type = notification.metadata.get('notification_type', 'delivery') if notification.metadata else 'delivery'
        
        if notification_type in ['smart_single_delivery', 'smart_batch_delivery']:
            actions.extend([
                {
                    'id': 'accept',
                    'title': 'Accept',
                    'action': 'accept_delivery',
                    'input': False
                },
                {
                    'id': 'view_details',
                    'title': 'View Route',
                    'action': 'view_delivery_details',
                    'input': False
                },
                {
                    'id': 'decline',
                    'title': 'Pass',
                    'action': 'decline_delivery',
                    'input': False
                }
            ])
        
        return actions
    
    def send_real_time_update(self, driver_id: int, update_type: str, data: dict) -> bool:
        """
        Send real-time updates to driver for seamless experience
        """
        try:
            driver = Driver.query.get(driver_id)
            if not driver or not driver.push_token:
                return False
            
            update_messages = {
                'earnings_milestone': f"You've earned ${data.get('amount', 0):.2f} today!",
                'peak_hours': f"Peak hours active! Earnings up {data.get('increase', 0)}%",
                'route_optimized': f"Route optimized! Save {data.get('time_saved', 0)} minutes",
                'new_opportunities': f"{data.get('count', 0)} new deliveries nearby!",
                'performance_boost': f"Great job! {data.get('rating', 0):.1f}★ average today"
            }
            
            message = update_messages.get(update_type, f"Update: {update_type}")
            
            # Create low-priority notification for updates
            notification = Notification(
                driver_id=driver_id,
                type=NotificationType.SYSTEM_UPDATE,
                title="DeliverMee Update",
                message=message,
                priority='low',
                metadata={
                    'update_type': update_type,
                    'data': data,
                    'real_time': True
                }
            )
            
            db.session.add(notification)
            db.session.commit()
            
            # Send as low-priority silent update
            return self._send_silent_update(driver, notification)
            
        except Exception as e:
            logger.error(f"Error sending real-time update: {str(e)}")
            return False
    
    def _send_silent_update(self, driver: Driver, notification: Notification) -> bool:
        """
        Send silent background update to app
        """
        try:
            payload = {
                'to': driver.push_token,
                'data': {
                    'type': 'silent_update',
                    'update_type': notification.metadata.get('update_type', 'general'),
                    'message': notification.message,
                    'data': json.dumps(notification.metadata.get('data', {})),
                    'timestamp': datetime.utcnow().isoformat()
                },
                'content_available': True,
                'priority': 'normal'
            }
            
            headers = {
                'Authorization': f'key={self.fcm_server_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                data=json.dumps(payload),
                headers=headers,
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending silent update: {str(e)}")
            return False
    
    def send_batch_progress_update(self, driver_id: int, batch_info: dict) -> bool:
        """
        Send progress updates for batch deliveries
        """
        try:
            progress_messages = {
                'batch_started': f"Batch started! {batch_info.get('total', 0)} deliveries to go",
                'delivery_completed': f"{batch_info.get('completed', 0)}/{batch_info.get('total', 0)} completed - ${batch_info.get('earnings', 0):.2f} earned",
                'batch_completed': f"Batch complete! ${batch_info.get('total_earnings', 0):.2f} earned in {batch_info.get('duration', 0)} mins",
                'next_pickup': f"Next pickup: {batch_info.get('next_address', 'Address')} - {batch_info.get('distance', 0):.1f}km away"
            }
            
            message = progress_messages.get(batch_info.get('status', 'update'), "Batch update")
            
            return self.send_real_time_update(driver_id, 'batch_progress', {
                'message': message,
                'batch_info': batch_info
            })
            
        except Exception as e:
            logger.error(f"Error sending batch progress update: {str(e)}")
            return False
    
    def create_notification(self, driver_id: int, delivery_id: int = None, notification_type: str = 'general', 
                          title: str = '', message: str = '', metadata: dict = None) -> Notification:
        """
        Enhanced notification creation with intelligent categorization
        """
        try:
            # Map string types to enum types
            type_mapping = {
                'delivery_assignment': NotificationType.DELIVERY_ASSIGNMENT,
                'intelligent_assignment': NotificationType.DELIVERY_ASSIGNMENT,
                'ride_assignment': NotificationType.RIDE_ASSIGNMENT,
                'system_update': NotificationType.SYSTEM_UPDATE,
                'earnings_update': NotificationType.EARNINGS_UPDATE,
                'general': NotificationType.GENERAL
            }
            
            notification_enum_type = type_mapping.get(notification_type, NotificationType.GENERAL)
            
            # Determine priority based on content
            priority = 'normal'
            if 'urgent' in title.lower() or 'urgent' in message.lower():
                priority = 'urgent'
            elif '$' in message and (notification_type == 'delivery_assignment' or notification_type == 'intelligent_assignment'):
                priority = 'high'
            elif notification_type == 'system_update':
                priority = 'low'
            
            notification = Notification(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=notification_enum_type,
                title=title,
                message=message,
                priority=priority,
                metadata=metadata or {}
            )
            
            db.session.add(notification)
            db.session.commit()
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating enhanced notification: {str(e)}")
            return None
    
    def get_notification_by_delivery(self, driver_id: int, delivery_id: int, notification_type: str) -> Notification:
        """
        Get notification by delivery and type
        """
        try:
            type_mapping = {
                'delivery_assignment': NotificationType.DELIVERY_ASSIGNMENT,
                'intelligent_assignment': NotificationType.DELIVERY_ASSIGNMENT,
                'ride_assignment': NotificationType.RIDE_ASSIGNMENT
            }
            
            notification_enum_type = type_mapping.get(notification_type, NotificationType.DELIVERY_ASSIGNMENT)
            
            return Notification.query.filter_by(
                driver_id=driver_id,
                delivery_id=delivery_id,
                type=notification_enum_type
            ).first()
            
        except Exception as e:
            logger.error(f"Error getting notification by delivery: {str(e)}")
            return None

# Global enhanced notification service instance
enhanced_notification_service = EnhancedNotificationService()
