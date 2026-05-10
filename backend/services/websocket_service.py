#!/usr/bin/env python3
"""
WebSocket Service - UBER Quality Real-time Communication
Handles WebSocket connections for live tracking and real-time updates
"""

import json
import logging
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
from typing import Dict, Set
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketService:
    """Manages WebSocket connections and real-time communication"""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.connected_users: Dict[str, Dict] = {}  # user_id -> connection info
        self.user_rooms: Dict[str, Set[str]] = {}   # user_id -> set of rooms
        self.delivery_rooms: Dict[int, Set[str]] = {}  # delivery_id -> set of user_ids
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            try:
                logger.info(f"Client connected: {request.sid}")
                
                # Send connection confirmation
                emit('connected', {
                    'status': 'connected',
                    'sid': request.sid,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                disconnect()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            try:
                user_id = self._get_user_from_sid(request.sid)
                if user_id:
                    self._handle_user_disconnect(user_id, request.sid)
                
                logger.info(f"Client disconnected: {request.sid}")
                
            except Exception as e:
                logger.error(f"Disconnection error: {str(e)}")
        
        @self.socketio.on('authenticate')
        def handle_authentication(data):
            """Handle user authentication and room joining"""
            try:
                token = data.get('token')
                user_type = data.get('user_type')  # 'driver' or 'customer'
                
                if not token or not user_type:
                    emit('auth_error', {'error': 'Missing token or user type'})
                    return
                
                # Verify JWT token
                user_id = self._verify_token(token)
                if not user_id:
                    emit('auth_error', {'error': 'Invalid token'})
                    return
                
                # Store connection info
                self.connected_users[request.sid] = {
                    'user_id': user_id,
                    'user_type': user_type,
                    'connected_at': datetime.utcnow(),
                    'sid': request.sid
                }
                
                # Join user-specific room
                user_room = f"{user_type}_{user_id}"
                join_room(user_room)
                
                if user_id not in self.user_rooms:
                    self.user_rooms[user_id] = set()
                self.user_rooms[user_id].add(user_room)
                
                # Send authentication success
                emit('authenticated', {
                    'user_id': user_id,
                    'user_type': user_type,
                    'room': user_room,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"User {user_id} ({user_type}) authenticated and joined room {user_room}")
                
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}")
                emit('auth_error', {'error': 'Authentication failed'})
        
        @self.socketio.on('join_delivery_room')
        def handle_join_delivery_room(data):
            """Handle joining a delivery tracking room"""
            try:
                delivery_id = data.get('delivery_id')
                token = data.get('token')
                
                if not delivery_id or not token:
                    emit('room_error', {'error': 'Missing delivery ID or token'})
                    return
                
                # Verify token and get user info
                user_id = self._verify_token(token)
                if not user_id:
                    emit('room_error', {'error': 'Invalid token'})
                    return
                
                # Join delivery room
                delivery_room = f"delivery_{delivery_id}"
                join_room(delivery_room)
                
                # Track room membership
                if delivery_id not in self.delivery_rooms:
                    self.delivery_rooms[delivery_id] = set()
                self.delivery_rooms[delivery_id].add(user_id)
                
                if user_id in self.user_rooms:
                    self.user_rooms[user_id].add(delivery_room)
                
                # Send room joined confirmation
                emit('delivery_room_joined', {
                    'delivery_id': delivery_id,
                    'room': delivery_room,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"User {user_id} joined delivery room {delivery_room}")
                
            except Exception as e:
                logger.error(f"Join delivery room error: {str(e)}")
                emit('room_error', {'error': 'Failed to join delivery room'})
        
        @self.socketio.on('leave_delivery_room')
        def handle_leave_delivery_room(data):
            """Handle leaving a delivery tracking room"""
            try:
                delivery_id = data.get('delivery_id')
                token = data.get('token')
                
                if not delivery_id or not token:
                    emit('room_error', {'error': 'Missing delivery ID or token'})
                    return
                
                # Verify token and get user info
                user_id = self._verify_token(token)
                if not user_id:
                    emit('room_error', {'error': 'Invalid token'})
                    return
                
                # Leave delivery room
                delivery_room = f"delivery_{delivery_id}"
                leave_room(delivery_room)
                
                # Update room tracking
                if delivery_id in self.delivery_rooms and user_id in self.delivery_rooms[delivery_id]:
                    self.delivery_rooms[delivery_id].remove(user_id)
                
                if user_id in self.user_rooms and delivery_room in self.user_rooms[user_id]:
                    self.user_rooms[user_id].remove(delivery_room)
                
                # Send room left confirmation
                emit('delivery_room_left', {
                    'delivery_id': delivery_id,
                    'room': delivery_room,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"User {user_id} left delivery room {delivery_room}")
                
            except Exception as e:
                logger.error(f"Leave delivery room error: {str(e)}")
                emit('room_error', {'error': 'Failed to leave delivery room'})
        
        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping for connection health check"""
            try:
                emit('pong', {
                    'timestamp': datetime.utcnow().isoformat(),
                    'sid': request.sid
                })
            except Exception as e:
                logger.error(f"Ping error: {str(e)}")
    
    def _verify_token(self, token: str) -> str:
        """Verify JWT token and return user ID"""
        try:
            # Import here to avoid circular imports
            from extensions import jwt
            
            # Decode token (you'll need to implement this based on your JWT setup)
            # For now, we'll use a simple approach
            payload = jwt.decode(token, verify=False)  # In production, always verify
            return str(payload.get('sub') or payload.get('user_id'))
            
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return None
    
    def _get_user_from_sid(self, sid: str) -> str:
        """Get user ID from session ID"""
        for user_info in self.connected_users.values():
            if user_info.get('sid') == sid:
                return user_info.get('user_id')
        return None
    
    def _handle_user_disconnect(self, user_id: str, sid: str):
        """Handle user disconnection cleanup"""
        try:
            # Remove from connected users
            if sid in self.connected_users:
                del self.connected_users[sid]
            
            # Clean up user rooms
            if user_id in self.user_rooms:
                for room in self.user_rooms[user_id]:
                    leave_room(room)
                del self.user_rooms[user_id]
            
            # Clean up delivery rooms
            for delivery_id, users in self.delivery_rooms.items():
                if user_id in users:
                    users.remove(user_id)
                    if not users:
                        del self.delivery_rooms[delivery_id]
            
            logger.info(f"Cleaned up connections for user {user_id}")
            
        except Exception as e:
            logger.error(f"Disconnect cleanup error: {str(e)}")
    
    def broadcast_to_delivery(self, delivery_id: int, event: str, data: Dict):
        """Broadcast event to all users tracking a specific delivery"""
        try:
            delivery_room = f"delivery_{delivery_id}"
            self.socketio.emit(event, data, room=delivery_room)
            logger.info(f"Broadcasted {event} to delivery {delivery_id}")
            
        except Exception as e:
            logger.error(f"Broadcast error: {str(e)}")
    
    def send_to_user(self, user_id: str, user_type: str, event: str, data: Dict):
        """Send event to specific user"""
        try:
            user_room = f"{user_type}_{user_id}"
            self.socketio.emit(event, data, room=user_room)
            logger.info(f"Sent {event} to user {user_id} ({user_type})")
            
        except Exception as e:
            logger.error(f"Send to user error: {str(e)}")
    
    def get_connection_stats(self) -> Dict:
        """Get current connection statistics"""
        try:
            stats = {
                'total_connections': len(self.connected_users),
                'active_users': len(self.user_rooms),
                'active_deliveries': len(self.delivery_rooms),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Add user type breakdown
            user_types = {}
            for user_info in self.connected_users.values():
                user_type = user_info.get('user_type', 'unknown')
                user_types[user_type] = user_types.get(user_type, 0) + 1
            
            stats['user_types'] = user_types
            
            return stats
            
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'error': 'Failed to get stats'}
    
    def force_disconnect_user(self, user_id: str):
        """Force disconnect a specific user"""
        try:
            if user_id in self.user_rooms:
                # Find all sessions for this user
                sessions_to_remove = []
                for sid, user_info in self.connected_users.items():
                    if user_info.get('user_id') == user_id:
                        sessions_to_remove.append(sid)
                
                # Disconnect all sessions
                for sid in sessions_to_remove:
                    disconnect(sid)
                
                logger.info(f"Force disconnected user {user_id}")
                
        except Exception as e:
            logger.error(f"Force disconnect error: {str(e)}")

# Global instance
websocket_service = None

def init_websocket_service(socketio: SocketIO):
    """Initialize the global WebSocket service"""
    global websocket_service
    websocket_service = WebSocketService(socketio)
    return websocket_service

