# API Documentation - Uber/Lyft Style Driver App

## Overview

This API provides a complete Uber/Lyft-style driver app system with features for driver management, ride scheduling, real-time location tracking, earnings management, and comprehensive analytics.

## Base URL

```
http://localhost:5000/api
```

## Authentication

All protected endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## 1. Driver Management APIs

### 1.1 Driver Registration

**Endpoint:** `POST /drivers/register`

**Description:** Register a new driver account

**Request Body:**
```json
{
  "email": "driver@example.com",
  "password": "password123",
  "phone_number": "+1234567890",
  "first_name": "John",
  "last_name": "Driver",
  "license_number": "DL123456789",
  "vehicle_plate": "ABC123",
  "vehicle_model": "Toyota Camry",
  "vehicle_color": "Silver"
}
```

**Response (201):**
```json
{
  "message": "Driver registered successfully",
  "access_token": "jwt_token_here",
  "driver": {
    "id": 1,
    "email": "driver@example.com",
    "first_name": "John",
    "last_name": "Driver",
    "phone_number": "+1234567890",
    "license_number": "DL123456789",
    "vehicle_plate": "ABC123",
    "vehicle_model": "Toyota Camry",
    "vehicle_color": "Silver",
    "status": "offline",
    "rating": 0.0,
    "total_rides": 0,
    "is_active": true
  }
}
```

### 1.2 Driver Login

**Endpoint:** `POST /drivers/login`

**Description:** Authenticate driver and get access token

**Request Body:**
```json
{
  "email": "driver@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "access_token": "jwt_token_here",
  "driver": {
    "id": 1,
    "email": "driver@example.com",
    "first_name": "John",
    "last_name": "Driver",
    "status": "offline"
  }
}
```

### 1.3 Get Driver Profile

**Endpoint:** `GET /drivers/profile`

**Description:** Get current driver's profile information

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "email": "driver@example.com",
  "first_name": "John",
  "last_name": "Driver",
  "phone_number": "+1234567890",
  "license_number": "DL123456789",
  "vehicle_plate": "ABC123",
  "vehicle_model": "Toyota Camry",
  "vehicle_color": "Silver",
  "status": "available",
  "current_latitude": 40.7128,
  "current_longitude": -74.0060,
  "rating": 4.5,
  "total_rides": 25,
  "is_active": true
}
```

### 1.4 Update Driver Location

**Endpoint:** `POST /drivers/location`

**Description:** Update driver's current GPS location

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

**Response (200):**
```json
{
  "message": "Location updated successfully",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

### 1.5 Update Driver Status

**Endpoint:** `POST /drivers/status`

**Description:** Update driver's status (available/busy/offline)

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "status": "available"
}
```

**Response (200):**
```json
{
  "message": "Status updated successfully",
  "status": "available"
}
```

### 1.6 Update Push Token

**Endpoint:** `POST /drivers/push-token`

**Description:** Update driver's push notification token

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "push_token": "fcm_token_here",
  "device_id": "device_identifier"
}
```

**Response (200):**
```json
{
  "message": "Push token updated successfully",
  "push_token": "fcm_token_here"
}
```

### 1.7 Accept Ride

**Endpoint:** `POST /drivers/rides/{ride_id}/accept`

**Description:** Accept a ride assignment

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride accepted successfully",
  "ride_id": 123,
  "status": "accepted",
  "accepted_time": "2025-07-10T20:32:00Z"
}
```

### 1.8 Reject Ride

**Endpoint:** `POST /drivers/rides/{ride_id}/reject`

**Description:** Reject a ride assignment

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride rejected successfully",
  "ride_id": 123,
  "status": "rejected"
}
```

---

## 2. Driver App APIs

### 2.1 Get Driver App Status

**Endpoint:** `GET /driver-app/status`

**Description:** Get driver's current app status and active ride

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "driver_status": "available",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "last_update": "2025-07-10T20:30:00Z"
  },
  "active_ride": {
    "ride_id": 123,
    "status": "assigned",
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "customer": {
      "name": "Jane Customer",
      "phone": "+1987654321",
      "rating": 4.8
    },
    "estimated_cost": 25.0,
    "estimated_duration": 20
  },
  "online": true,
  "total_rides_today": 5
}
```

### 2.2 Go Online

**Endpoint:** `POST /driver-app/go-online`

**Description:** Set driver status to available (online)

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Driver is now online",
  "status": "available",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

### 2.3 Go Offline

**Endpoint:** `POST /driver-app/go-offline`

**Description:** Set driver status to offline

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Driver is now offline",
  "status": "offline"
}
```

### 2.4 Update Location (Driver App)

**Endpoint:** `POST /driver-app/location`

**Description:** Update driver's location with additional metadata

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 5.0,
  "speed": 25.5,
  "heading": 180.0
}
```

**Response (200):**
```json
{
  "message": "Location updated successfully",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 5.0,
    "speed": 25.5,
    "heading": 180.0,
    "timestamp": "2025-07-10T20:30:00Z"
  }
}
```

### 2.5 Get Ride Requests

**Endpoint:** `GET /driver-app/ride-requests`

**Description:** Get available ride requests for driver

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "ride_requests": [
    {
      "ride_id": 123,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "estimated_cost": 25.0,
      "estimated_duration": 20,
      "distance_from_driver": 2.5,
      "customer_name": "Jane Customer",
      "customer_rating": 4.8,
      "special_instructions": "Please call when arriving",
      "requested_time": "2025-07-10T20:25:00Z",
      "vehicle_type": "SEDAN"
    }
  ],
  "total_requests": 1
}
```

### 2.6 Accept Ride

**Endpoint:** `POST /driver-app/accept-ride/{ride_id}`

**Description:** Accept a ride request

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride accepted successfully",
  "ride": {
    "ride_id": 123,
    "status": "accepted",
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "customer": {
      "name": "Jane Customer",
      "phone": "+1987654321",
      "rating": 4.8
    },
    "estimated_cost": 25.0,
    "estimated_duration": 20,
    "pickup_latitude": 40.7128,
    "pickup_longitude": -74.0060,
    "dropoff_latitude": 40.7589,
    "dropoff_longitude": -73.9851,
    "special_instructions": "Please call when arriving",
    "vehicle_type": "SEDAN"
  }
}
```

### 2.7 Start Ride

**Endpoint:** `POST /driver-app/start-ride/{ride_id}`

**Description:** Start the ride (arrived at pickup)

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride started successfully",
  "ride_id": 123,
  "status": "in_progress",
  "pickup_time": "2025-07-10T20:35:00Z"
}
```

### 2.8 Complete Ride

**Endpoint:** `POST /driver-app/complete-ride/{ride_id}`

**Description:** Complete the ride

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride completed successfully",
  "earnings": 25.0,
  "total_rides": 26,
  "completion_time": "2025-07-10T20:55:00Z"
}
```

### 2.9 Get Driver Earnings

**Endpoint:** `GET /driver-app/earnings`

**Description:** Get driver's earnings summary

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "today_earnings": 125.0,
  "week_earnings": 450.0,
  "month_earnings": 1800.0,
  "total_earnings": 4500.0,
  "today_rides": 5,
  "week_rides": 18,
  "month_rides": 72,
  "total_rides": 180,
  "average_rating": 4.7
}
```

### 2.10 Get Ride History

**Endpoint:** `GET /driver-app/ride-history`

**Description:** Get driver's ride history

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional): Number of rides to return (default: 20)
- `offset` (optional): Number of rides to skip (default: 0)

**Response (200):**
```json
{
  "rides": [
    {
      "ride_id": 123,
      "status": "completed",
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "estimated_cost": 25.0,
      "completed_time": "2025-07-10T20:55:00Z",
      "customer_name": "Jane Customer",
      "earnings": 25.0
    }
  ],
  "total": 180,
  "limit": 20,
  "offset": 0
}
```

---

## 3. Driver Dashboard APIs

### 3.1 Get Dashboard Summary

**Endpoint:** `GET /driver-dashboard/summary`

**Description:** Get driver dashboard summary with key metrics

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "online_hours": 8.5,
  "total_rides_today": 5,
  "earnings_today": 125.0,
  "acceptance_rate": 95.0,
  "completion_rate": 98.0,
  "average_rating": 4.7,
  "total_rides": 180,
  "total_earnings": 4500.0
}
```

### 3.2 Get Performance Metrics

**Endpoint:** `GET /driver-dashboard/performance`

**Description:** Get detailed performance metrics

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_rides": 180,
  "completed_rides": 176,
  "cancelled_rides": 4,
  "total_earnings": 4500.0,
  "average_earnings_per_ride": 25.0,
  "best_day": "2025-07-10",
  "best_day_earnings": 150.0,
  "weekly_goal_progress": 75.0,
  "monthly_goal_progress": 60.0,
  "acceptance_rate": 95.0,
  "completion_rate": 98.0,
  "average_rating": 4.7
}
```

### 3.3 Get Earnings Breakdown

**Endpoint:** `GET /driver-dashboard/earnings-breakdown`

**Description:** Get detailed earnings breakdown by period

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `period` (optional): Time period - week, month, year (default: week)

**Response (200):**
```json
{
  "period": "week",
  "total_earnings": 450.0,
  "total_rides": 18,
  "breakdown": [
    {
      "date": "2025-07-10",
      "earnings": 125.0,
      "rides": 5,
      "average_per_ride": 25.0
    }
  ]
}
```

### 3.4 Get Dashboard Notifications

**Endpoint:** `GET /driver-dashboard/notifications`

**Description:** Get driver's recent notifications

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "ride_assignment",
      "title": "New Ride Assignment",
      "message": "New ride from 123 Main St to 456 Broadway",
      "status": "read",
      "created_at": "2025-07-10T20:31:00Z"
    }
  ],
  "total": 15
}
```

### 3.5 Get Driver Stats

**Endpoint:** `GET /driver-dashboard/stats`

**Description:** Get comprehensive driver statistics

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_rides": 180,
  "total_earnings": 4500.0,
  "average_rating": 4.7,
  "acceptance_rate": 95.0,
  "completion_rate": 98.0,
  "online_hours": 120.5,
  "best_earnings_day": "2025-07-10",
  "best_earnings_amount": 150.0
}
```

---

## 4. Customer APIs

### 4.1 Customer Registration

**Endpoint:** `POST /customers/register`

**Description:** Register a new customer account

**Request Body:**
```json
{
  "email": "customer@example.com",
  "password": "password123",
  "phone_number": "+1987654321",
  "first_name": "Jane",
  "last_name": "Customer"
}
```

**Response (201):**
```json
{
  "message": "Customer registered successfully",
  "access_token": "jwt_token_here",
  "customer": {
    "id": 1,
    "email": "customer@example.com",
    "first_name": "Jane",
    "last_name": "Customer",
    "phone_number": "+1987654321"
  }
}
```

### 4.2 Customer Login

**Endpoint:** `POST /customers/login`

**Description:** Authenticate customer and get access token

**Request Body:**
```json
{
  "email": "customer@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "access_token": "jwt_token_here",
  "customer": {
    "id": 1,
    "email": "customer@example.com",
    "first_name": "Jane",
    "last_name": "Customer"
  }
}
```

### 4.3 Get Customer Profile

**Endpoint:** `GET /customers/profile`

**Description:** Get customer profile information

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "id": 1,
  "email": "customer@example.com",
  "first_name": "Jane",
  "last_name": "Customer",
  "phone_number": "+1987654321",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "total_rides": 15,
  "total_spent": 275.50,
  "average_rating": 4.8
}
```

### 4.4 Update Customer Profile

**Endpoint:** `PUT /customers/profile`

**Description:** Update customer profile information

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Customer",
  "phone_number": "+1987654321"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "customer": {
    "id": 1,
    "email": "customer@example.com",
    "first_name": "Jane",
    "last_name": "Customer",
    "phone_number": "+1987654321"
  }
}
```

### 4.5 Change Customer Password

**Endpoint:** `POST /customers/change-password`

**Description:** Change customer password

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword123"
}
```

**Response (200):**
```json
{
  "message": "Password changed successfully"
}
```

### 4.6 Get Customer Statistics

**Endpoint:** `GET /customers/statistics`

**Description:** Get customer's ride statistics and analytics

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "total_rides": 15,
  "completed_rides": 14,
  "cancelled_rides": 1,
  "total_spent": 275.50,
  "average_ride_cost": 18.37,
  "favorite_destinations": [
    {
      "address": "456 Broadway, New York, NY",
      "count": 5,
      "total_spent": 91.85
    }
  ],
  "monthly_usage": [
    {
      "month": "2025-07",
      "rides": 15,
      "spent": 275.50
    }
  ],
  "preferred_vehicle_types": [
    {
      "vehicle_type": "SEDAN",
      "count": 10,
      "percentage": 66.7
    }
  ]
}
```

---

## 5. Ride Management APIs

### 5.1 Schedule Ride

**Endpoint:** `POST /rides/schedule`

**Description:** Schedule a new ride (immediate or scheduled)

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "pickup_address": "123 Main St, New York, NY",
  "dropoff_address": "456 Broadway, New York, NY",
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "dropoff_latitude": 40.7589,
  "dropoff_longitude": -73.9851,
  "ride_type": "immediate",
  "vehicle_type": "SEDAN",
  "special_instructions": "Please call when arriving"
}
```

**Response (201):**
```json
{
  "message": "Ride scheduled successfully",
  "ride": {
    "id": 123,
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "status": "assigned",
    "estimated_cost": 25.0,
    "estimated_duration": 20,
    "requested_time": "2025-07-10T20:30:00Z"
  },
  "driver": {
    "id": 1,
    "first_name": "John",
    "last_name": "Driver",
    "phone_number": "+1234567890",
    "vehicle_model": "Toyota Camry",
    "vehicle_color": "Silver"
  },
  "eta": "5-10 minutes"
}
```

### 5.2 Get Customer Rides

**Endpoint:** `GET /rides`

**Description:** Get all rides for the authenticated customer

**Headers:** `Authorization: Bearer <token>` (customer token)

**Query Parameters:**
- `status` (optional): Filter by ride status
- `ride_type` (optional): Filter by ride type
- `limit` (optional): Number of rides to return (default: 20)
- `offset` (optional): Number of rides to skip (default: 0)

**Response (200):**
```json
{
  "rides": [
    {
      "id": 123,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "status": "completed",
      "estimated_cost": 25.0,
      "driver": {
        "id": 1,
        "first_name": "John",
        "last_name": "Driver",
        "phone_number": "+1234567890"
      }
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### 5.3 Get Ride Details

**Endpoint:** `GET /rides/{ride_id}`

**Description:** Get specific ride details

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "ride": {
    "id": 123,
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "status": "in_progress",
    "estimated_cost": 25.0,
    "estimated_duration": 20,
    "requested_time": "2025-07-10T20:30:00Z",
    "assigned_time": "2025-07-10T20:31:00Z",
    "accepted_time": "2025-07-10T20:32:00Z",
    "pickup_time": "2025-07-10T20:35:00Z"
  },
  "driver": {
    "id": 1,
    "first_name": "John",
    "last_name": "Driver",
    "phone_number": "+1234567890",
    "vehicle_model": "Toyota Camry",
    "vehicle_color": "Silver",
    "rating": 4.7
  },
  "eta": "3-5 minutes"
}
```

### 5.4 Cancel Ride

**Endpoint:** `POST /rides/{ride_id}/cancel`

**Description:** Cancel a ride

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "message": "Ride cancelled successfully",
  "cancellation_fee": 0.0
}
```

### 5.5 Update Ride

**Endpoint:** `PUT /rides/{ride_id}`

**Description:** Update ride details

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "pickup_address": "Updated pickup address",
  "dropoff_address": "Updated dropoff address",
  "special_instructions": "Updated instructions"
}
```

**Response (200):**
```json
{
  "message": "Ride updated successfully",
  "ride": {
    "id": 123,
    "pickup_address": "Updated pickup address",
    "dropoff_address": "Updated dropoff address",
    "status": "assigned",
    "estimated_cost": 25.0
  }
}
```

### 5.6 Get Ride Status

**Endpoint:** `GET /rides/{ride_id}/status`

**Description:** Get current ride status

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "ride_id": 123,
  "status": "in_progress",
  "driver": {
    "id": 1,
    "name": "John Driver",
    "phone": "+1234567890",
    "vehicle": "Toyota Camry - ABC123"
  },
  "eta": "5-10 minutes",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

### 5.7 Rate Driver

**Endpoint:** `POST /rides/{ride_id}/rate`

**Description:** Rate the driver after ride completion

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "rating": 5,
  "feedback": "Great driver, very professional and on time"
}
```

**Response (200):**
```json
{
  "message": "Rating submitted successfully",
  "ride_id": 123,
  "rating": 5,
  "feedback": "Great driver, very professional and on time"
}
```

### 5.8 Get Ride Receipt

**Endpoint:** `GET /rides/{ride_id}/receipt`

**Description:** Get detailed ride receipt after completion

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "ride_id": 123,
  "receipt_number": "RIDE-2025-00123",
  "pickup_address": "123 Main St, New York, NY",
  "dropoff_address": "456 Broadway, New York, NY",
  "driver": {
    "name": "John Driver",
    "phone": "+1234567890",
    "vehicle": "Toyota Camry - ABC123"
  },
  "ride_details": {
    "requested_time": "2025-07-10T20:30:00Z",
    "pickup_time": "2025-07-10T20:35:00Z",
    "completed_time": "2025-07-10T20:55:00Z",
    "duration": 20,
    "distance": 5.2
  },
  "cost_breakdown": {
    "base_fare": 10.0,
    "distance_cost": 5.72,
    "special_fees": 0.0,
    "subtotal": 15.72,
    "platform_fee": 2.36,
    "payment_processing_fee": 0.47,
    "total_cost": 18.55
  },
  "payment_method": "Credit Card",
  "status": "completed"
}
```

### 5.9 Get Ride History Summary

**Endpoint:** `GET /rides/history/summary`

**Description:** Get customer's ride history summary and statistics

**Headers:** `Authorization: Bearer <token>` (customer token)

**Query Parameters:**
- `period` (optional): Time period - week, month, year (default: month)

**Response (200):**
```json
{
  "period": "month",
  "total_rides": 15,
  "completed_rides": 14,
  "cancelled_rides": 1,
  "total_spent": 275.50,
  "average_ride_cost": 18.37,
  "favorite_destinations": [
    {
      "address": "456 Broadway, New York, NY",
      "count": 5,
      "total_spent": 91.85
    }
  ],
  "favorite_drivers": [
    {
      "driver_id": 1,
      "name": "John Driver",
      "rides": 3,
      "average_rating": 4.8
    }
  ],
  "monthly_trends": [
    {
      "month": "2025-07",
      "rides": 15,
      "spent": 275.50
    }
  ]
}
```

### 5.10 Get Ride Tracking

**Endpoint:** `GET /rides/{ride_id}/track`

**Description:** Get real-time ride tracking information

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "ride_id": 123,
  "status": "in_progress",
  "driver": {
    "id": 1,
    "name": "John Driver",
    "phone": "+1234567890",
    "vehicle": "Toyota Camry - ABC123",
    "rating": 4.7
  },
  "current_location": {
    "latitude": 40.7300,
    "longitude": -73.9900,
    "last_update": "2025-07-10T20:45:00Z"
  },
  "route": {
    "pickup": {
      "address": "123 Main St, New York, NY",
      "coordinates": {
        "latitude": 40.7128,
        "longitude": -74.0060
      }
    },
    "dropoff": {
      "address": "456 Broadway, New York, NY",
      "coordinates": {
        "latitude": 40.7589,
        "longitude": -73.9851
      }
    }
  },
  "eta": "5-10 minutes",
  "progress": {
    "distance_completed": 3.2,
    "distance_remaining": 2.0,
    "progress_percentage": 62
  }
}
```

### 5.11 Get Ride Preferences

**Endpoint:** `GET /rides/preferences`

**Description:** Get customer's ride preferences

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "preferences": {
    "default_vehicle_type": "SEDAN",
    "default_pickup_location": "123 Main St, New York, NY",
    "default_dropoff_location": "456 Broadway, New York, NY",
    "preferred_drivers": [1, 5, 8],
    "special_instructions": "Please call when arriving",
    "payment_method": "Credit Card",
    "notification_preferences": {
      "ride_updates": true,
      "driver_arrival": true,
      "ride_completion": true
    }
  }
}
```

### 5.12 Update Ride Preferences

**Endpoint:** `PUT /rides/preferences`

**Description:** Update customer's ride preferences

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "default_vehicle_type": "SUV",
  "default_pickup_location": "Updated pickup address",
  "default_dropoff_location": "Updated dropoff address",
  "special_instructions": "Updated instructions",
  "payment_method": "PayPal",
  "notification_preferences": {
    "ride_updates": true,
    "driver_arrival": true,
    "ride_completion": false
  }
}
```

**Response (200):**
```json
{
  "message": "Preferences updated successfully",
  "preferences": {
    "default_vehicle_type": "SUV",
    "default_pickup_location": "Updated pickup address",
    "default_dropoff_location": "Updated dropoff address",
    "special_instructions": "Updated instructions",
    "payment_method": "PayPal",
    "notification_preferences": {
      "ride_updates": true,
      "driver_arrival": true,
      "ride_completion": false
    }
  }
}
```

---

## 6. Driver Management APIs (Admin)

### 6.1 Get Driver Profile

**Endpoint:** `GET /driver-management/profile`

**Description:** Get driver's complete profile with earnings

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "email": "driver@example.com",
  "first_name": "John",
  "last_name": "Driver",
  "phone_number": "+1234567890",
  "license_number": "DL123456789",
  "vehicle_plate": "ABC123",
  "vehicle_model": "Toyota Camry",
  "vehicle_color": "Silver",
  "status": "available",
  "rating": 4.7,
  "total_rides": 180,
  "total_earnings": 4500.0,
  "is_active": true
}
```

### 6.2 Update Driver Profile

**Endpoint:** `PUT /driver-management/profile`

**Description:** Update driver's profile information

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Driver",
  "phone_number": "+1234567890",
  "vehicle_plate": "ABC123",
  "vehicle_model": "Toyota Camry",
  "vehicle_color": "Silver"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "driver": {
    "id": 1,
    "first_name": "John",
    "last_name": "Driver",
    "phone_number": "+1234567890",
    "vehicle_plate": "ABC123",
    "vehicle_model": "Toyota Camry",
    "vehicle_color": "Silver"
  }
}
```

### 6.3 Get Driver Earnings

**Endpoint:** `GET /driver-management/earnings`

**Description:** Get driver's earnings statistics

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "total_earnings": 4500.0,
  "today_earnings": 125.0,
  "week_earnings": 450.0,
  "month_earnings": 1800.0,
  "total_rides": 180,
  "completed_rides": 176,
  "cancelled_rides": 4
}
```

### 6.4 Get Active Rides

**Endpoint:** `GET /driver-management/rides/active`

**Description:** Get driver's active rides (assigned, accepted, in_progress)

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "rides": [
    {
      "id": 123,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "status": "in_progress",
      "estimated_cost": 25.0,
      "customer_name": "Jane Customer",
      "customer_phone": "+1987654321"
    }
  ],
  "total": 1
}
```

### 6.5 Get Ride History

**Endpoint:** `GET /driver-management/rides/history`

**Description:** Get driver's ride history

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (optional): Filter by ride status
- `limit` (optional): Number of rides to return (default: 20)
- `offset` (optional): Number of rides to skip (default: 0)

**Response (200):**
```json
{
  "rides": [
    {
      "id": 123,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "status": "completed",
      "estimated_cost": 25.0,
      "requested_time": "2025-07-10T20:30:00Z",
      "completed_time": "2025-07-10T20:55:00Z",
      "customer_name": "Jane Customer",
      "customer_phone": "+1987654321"
    }
  ],
  "total": 180,
  "limit": 20,
  "offset": 0
}
```

### 6.6 Start Ride

**Endpoint:** `POST /driver-management/rides/{ride_id}/start`

**Description:** Start a ride (arrived at pickup)

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride started successfully",
  "ride_id": 123,
  "status": "in_progress",
  "pickup_time": "2025-07-10T20:35:00Z"
}
```

### 6.7 Complete Ride

**Endpoint:** `POST /driver-management/rides/{ride_id}/complete`

**Description:** Complete a ride

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Ride completed successfully",
  "earnings": 25.0,
  "total_rides": 181,
  "completion_time": "2025-07-10T20:55:00Z"
}
```

### 6.8 Get Driver Availability

**Endpoint:** `GET /driver-management/availability`

**Description:** Get driver's availability status

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "driver_id": 1,
  "status": "available",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "last_update": "2025-07-10T20:30:00Z"
  },
  "online_hours_today": 8.5,
  "rides_completed_today": 5
}
```

### 6.9 Get Notification Settings

**Endpoint:** `GET /driver-management/notifications/settings`

**Description:** Get driver's notification settings

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "notification_enabled": true,
  "push_token": "fcm_token_here",
  "device_id": "device_identifier",
  "notification_types": {
    "ride_assignment": true,
    "ride_cancellation": true,
    "ride_update": true,
    "ride_reminder": true
  }
}
```

### 6.10 Update Notification Settings

**Endpoint:** `PUT /driver-management/notifications/settings`

**Description:** Update driver's notification settings

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "notification_enabled": true,
  "push_token": "new_fcm_token",
  "device_id": "device_identifier",
  "notification_types": {
    "ride_assignment": true,
    "ride_cancellation": false,
    "ride_update": true,
    "ride_reminder": true
  }
}
```

**Response (200):**
```json
{
  "message": "Notification settings updated successfully",
  "settings": {
    "notification_enabled": true,
    "push_token": "new_fcm_token",
    "device_id": "device_identifier"
  }
}
```

### 6.11 Get Driver Dashboard

**Endpoint:** `GET /driver-management/dashboard`

**Description:** Get comprehensive driver dashboard data

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "driver_info": {
    "id": 1,
    "name": "John Driver",
    "status": "available",
    "rating": 4.7,
    "total_rides": 180
  },
  "today_stats": {
    "rides": 5,
    "earnings": 125.0,
    "hours_online": 8.5
  },
  "performance": {
    "acceptance_rate": 95.0,
    "completion_rate": 98.0,
    "average_rating": 4.7
  },
  "recent_activity": [
    {
      "type": "ride_completed",
      "ride_id": 123,
      "earnings": 25.0,
      "time": "2025-07-10T20:55:00Z"
    }
  ]
}
```

---

## 7. Pricing APIs

### 7.1 Get Vehicle Pricing

**Endpoint:** `GET /pricing/vehicle-pricing`

**Description:** Get pricing information for all vehicle types

**Response (200):**
```json
{
  "pricing_info": {
    "SUV": {
      "base_fare": 15.0,
      "per_km_rate": 2.5,
      "description": "Sport Utility Vehicle"
    },
    "SEDAN": {
      "base_fare": 10.0,
      "per_km_rate": 2.0,
      "description": "Standard Sedan"
    }
  },
  "platform_fee_percentage": 15.0,
  "payment_processing_fee_percentage": 3.0,
  "special_fees": {
    "fragile_handling": 5.0,
    "perishable_handling": 8.0,
    "signature_required": 3.0
  }
}
```

### 7.2 Calculate Ride Cost

**Endpoint:** `POST /pricing/calculate-ride-cost`

**Description:** Calculate ride cost based on distance and vehicle type

**Request Body:**
```json
{
  "distance_km": 10.5,
  "vehicle_type": "SEDAN",
  "special_instructions": "Please call when arriving"
}
```

**Response (200):**
```json
{
  "base_fare": 10.0,
  "distance_cost": 21.0,
  "special_fees": 0.0,
  "subtotal": 31.0,
  "platform_fee": 4.65,
  "payment_processing_fee": 0.93,
  "total_cost": 36.58,
  "driver_earnings": 31.0,
  "distance_km": 10.5,
  "vehicle_type": "SEDAN",
  "estimated_duration": 25
}
```

### 7.3 Calculate Delivery Cost

**Endpoint:** `POST /pricing/calculate-delivery-cost`

**Description:** Calculate delivery cost based on distance, vehicle type, and package details

**Request Body:**
```json
{
  "distance_km": 15.0,
  "vehicle_type": "VAN",
  "package_type": "large",
  "delivery_type": "express",
  "is_fragile": true,
  "is_perishable": false,
  "requires_signature": true,
  "special_instructions": "Handle with care"
}
```

**Response (200):**
```json
{
  "base_fare": 20.0,
  "distance_cost": 45.0,
  "special_fees": 13.0,
  "subtotal": 78.0,
  "platform_fee": 11.7,
  "payment_processing_fee": 2.34,
  "total_cost": 92.04,
  "driver_earnings": 78.0,
  "distance_km": 15.0,
  "vehicle_type": "VAN",
  "estimated_duration": 35
}
```

### 7.4 Estimate Distance

**Endpoint:** `POST /pricing/estimate-distance`

**Description:** Estimate distance between two coordinates

**Request Body:**
```json
{
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "dropoff_latitude": 40.7589,
  "dropoff_longitude": -73.9851
}
```

**Response (200):**
```json
{
  "distance_km": 8.5,
  "pickup_coordinates": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "dropoff_coordinates": {
    "latitude": 40.7589,
    "longitude": -73.9851
  }
}
```

---

## 8. Delivery APIs

### 8.1 Create Delivery

**Endpoint:** `POST /deliveries/create`

**Description:** Create a new delivery request

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "pickup_address": "123 Main St, New York, NY",
  "dropoff_address": "456 Broadway, New York, NY",
  "pickup_latitude": 40.7128,
  "pickup_longitude": -74.0060,
  "dropoff_latitude": 40.7589,
  "dropoff_longitude": -73.9851,
  "item_name": "Electronics Package",
  "item_description": "Fragile electronics equipment",
  "package_type": "fragile",
  "width": 30.0,
  "height": 20.0,
  "length": 40.0,
  "weight": 5.5,
  "is_fragile": true,
  "is_perishable": false,
  "requires_signature": true,
  "special_instructions": "Handle with extreme care",
  "delivery_type": "express"
}
```

**Response (201):**
```json
{
  "message": "Delivery created successfully",
  "delivery": {
    "id": 456,
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "status": "assigned",
    "estimated_cost": 45.0,
    "tracking_number": "DEL123456789",
    "requested_time": "2025-07-10T20:30:00Z"
  },
  "driver": {
    "id": 1,
    "name": "John Driver",
    "phone": "+1234567890",
    "vehicle": "Toyota Camry - ABC123"
  },
  "eta": "30-45 minutes"
}
```

### 8.2 Get Customer Deliveries

**Endpoint:** `GET /deliveries`

**Description:** Get all deliveries for the authenticated customer

**Headers:** `Authorization: Bearer <token>` (customer token)

**Query Parameters:**
- `status` (optional): Filter by delivery status
- `delivery_type` (optional): Filter by delivery type
- `limit` (optional): Number of deliveries to return (default: 20)
- `offset` (optional): Number of deliveries to skip (default: 0)

**Response (200):**
```json
{
  "deliveries": [
    {
      "id": 456,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "status": "delivered",
      "estimated_cost": 45.0,
      "tracking_number": "DEL123456789",
      "driver": {
        "id": 1,
        "name": "John Driver",
        "phone": "+1234567890"
      }
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

### 8.3 Get Delivery Details

**Endpoint:** `GET /deliveries/{delivery_id}`

**Description:** Get specific delivery details

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "delivery": {
    "id": 456,
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "status": "in_transit",
    "estimated_cost": 45.0,
    "tracking_number": "DEL123456789",
    "item_name": "Electronics Package",
    "package_type": "fragile",
    "driver": {
      "id": 1,
      "name": "John Driver",
      "phone": "+1234567890",
      "vehicle": "Toyota Camry - ABC123"
    }
  },
  "eta": "15-20 minutes"
}
```

### 8.4 Update Delivery

**Endpoint:** `PUT /deliveries/{delivery_id}`

**Description:** Update delivery details

**Headers:** `Authorization: Bearer <token>` (customer token)

**Request Body:**
```json
{
  "pickup_address": "Updated pickup address",
  "dropoff_address": "Updated dropoff address",
  "special_instructions": "Updated instructions"
}
```

**Response (200):**
```json
{
  "message": "Delivery updated successfully",
  "delivery": {
    "id": 456,
    "pickup_address": "Updated pickup address",
    "dropoff_address": "Updated dropoff address",
    "status": "assigned",
    "estimated_cost": 45.0
  }
}
```

### 8.5 Cancel Delivery

**Endpoint:** `POST /deliveries/{delivery_id}/cancel`

**Description:** Cancel a delivery

**Headers:** `Authorization: Bearer <token>` (customer token)

**Response (200):**
```json
{
  "message": "Delivery cancelled successfully",
  "cancellation_fee": 0.0
}
```

### 8.6 Track Delivery

**Endpoint:** `GET /deliveries/track/{tracking_number}`

**Description:** Track delivery by tracking number (public endpoint)

**Response (200):**
```json
{
  "tracking_number": "DEL123456789",
  "status": "in_transit",
  "pickup_address": "123 Main St, New York, NY",
  "dropoff_address": "456 Broadway, New York, NY",
  "estimated_delivery": "2025-07-10T21:15:00Z",
  "current_location": {
    "latitude": 40.7300,
    "longitude": -73.9900
  },
  "driver": {
    "name": "John Driver",
    "vehicle": "Toyota Camry - ABC123"
  }
}
```

---

## 9. Driver Delivery App APIs

### 9.1 Get Driver Delivery Status

**Endpoint:** `GET /driver-delivery/status`

**Description:** Get driver's current delivery status and active delivery

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "driver_status": "available",
  "current_location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "last_update": "2025-07-10T20:30:00Z"
  },
  "active_delivery": {
    "delivery_id": 456,
    "status": "assigned",
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "customer": {
      "name": "Jane Customer",
      "phone": "+1987654321",
      "rating": 4.8
    },
    "item_name": "Electronics Package",
    "package_type": "fragile",
    "estimated_cost": 45.0,
    "estimated_duration": 30,
    "tracking_number": "DEL123456789"
  },
  "online": true,
  "total_deliveries_today": 3
}
```

### 9.2 Go Online (Delivery)

**Endpoint:** `POST /driver-delivery/go-online`

**Description:** Set driver status to available for deliveries

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Driver is now online",
  "status": "available",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  }
}
```

### 9.3 Go Offline (Delivery)

**Endpoint:** `POST /driver-delivery/go-offline`

**Description:** Set driver status to offline

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Driver is now offline",
  "status": "offline"
}
```

### 9.4 Update Location (Delivery)

**Endpoint:** `POST /driver-delivery/location`

**Description:** Update driver's location for deliveries

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 5.0,
  "speed": 25.5,
  "heading": 180.0
}
```

**Response (200):**
```json
{
  "message": "Location updated successfully",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 5.0,
    "speed": 25.5,
    "heading": 180.0,
    "timestamp": "2025-07-10T20:30:00Z"
  }
}
```

### 9.5 Get Delivery Requests

**Endpoint:** `GET /driver-delivery/delivery-requests`

**Description:** Get available delivery requests for driver

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "delivery_requests": [
    {
      "delivery_id": 456,
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "estimated_cost": 45.0,
      "estimated_duration": 30,
      "distance_from_driver": 2.5,
      "customer_name": "Jane Customer",
      "customer_rating": 4.8,
      "item_name": "Electronics Package",
      "package_type": "fragile",
      "special_instructions": "Handle with care",
      "requested_time": "2025-07-10T20:25:00Z",
      "tracking_number": "DEL123456789"
    }
  ],
  "total_requests": 1
}
```

### 9.6 Accept Delivery

**Endpoint:** `POST /driver-delivery/accept-delivery/{delivery_id}`

**Description:** Accept a delivery request

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Delivery accepted successfully",
  "delivery": {
    "delivery_id": 456,
    "status": "accepted",
    "pickup_address": "123 Main St, New York, NY",
    "dropoff_address": "456 Broadway, New York, NY",
    "customer": {
      "name": "Jane Customer",
      "phone": "+1987654321",
      "rating": 4.8
    },
    "estimated_cost": 45.0,
    "estimated_duration": 30,
    "item_name": "Electronics Package",
    "package_type": "fragile",
    "tracking_number": "DEL123456789"
  }
}
```

### 9.7 Pickup Delivery

**Endpoint:** `POST /driver-delivery/pickup-delivery/{delivery_id}`

**Description:** Mark delivery as picked up

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Delivery picked up successfully",
  "delivery_id": 456,
  "status": "picked_up",
  "pickup_time": "2025-07-10T20:35:00Z"
}
```

### 9.8 Start Transit

**Endpoint:** `POST /driver-delivery/start-transit/{delivery_id}`

**Description:** Start delivery transit

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Delivery in transit",
  "delivery_id": 456,
  "status": "in_transit",
  "transit_time": "2025-07-10T20:40:00Z"
}
```

### 9.9 Complete Delivery

**Endpoint:** `POST /driver-delivery/complete-delivery/{delivery_id}`

**Description:** Complete the delivery

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Delivery completed successfully",
  "earnings": 45.0,
  "total_deliveries": 26,
  "completion_time": "2025-07-10T21:05:00Z"
}
```

### 9.10 Get Delivery Earnings

**Endpoint:** `GET /driver-delivery/earnings`

**Description:** Get driver's delivery earnings summary

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "today_earnings": 135.0,
  "week_earnings": 450.0,
  "month_earnings": 1800.0,
  "total_earnings": 4500.0,
  "today_deliveries": 3,
  "week_deliveries": 15,
  "month_deliveries": 60,
  "total_deliveries": 180,
  "average_rating": 4.7
}
```

### 9.11 Get Delivery History

**Endpoint:** `GET /driver-delivery/delivery-history`

**Description:** Get driver's delivery history

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional): Number of deliveries to return (default: 20)
- `offset` (optional): Number of deliveries to skip (default: 0)

**Response (200):**
```json
{
  "deliveries": [
    {
      "delivery_id": 456,
      "status": "delivered",
      "pickup_address": "123 Main St, New York, NY",
      "dropoff_address": "456 Broadway, New York, NY",
      "estimated_cost": 45.0,
      "completed_time": "2025-07-10T21:05:00Z",
      "customer_name": "Jane Customer",
      "earnings": 45.0
    }
  ],
  "total": 180,
  "limit": 20,
  "offset": 0
}
```

---

## 10. Notification APIs

### 10.1 Get Driver Notifications

**Endpoint:** `GET /drivers/notifications`

**Description:** Get driver's notifications

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (optional): Filter by notification status
- `limit` (optional): Number of notifications to return (default: 20)
- `offset` (optional): Number of notifications to skip (default: 0)

**Response (200):**
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "ride_assignment",
      "title": "New Ride Assignment",
      "message": "New ride from 123 Main St to 456 Broadway. Estimated fare: $25.0",
      "status": "read",
      "created_at": "2025-07-10T20:31:00Z",
      "read_at": "2025-07-10T20:32:00Z"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### 10.2 Mark Notification as Read

**Endpoint:** `POST /drivers/notifications/{notification_id}/read`

**Description:** Mark a notification as read

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Notification marked as read"
}
```

---

## 11. Error Responses

### Common Error Format

All endpoints may return the following error responses:

**400 Bad Request:**
```json
{
  "error": "Validation Error",
  "details": "Missing required field: email"
}
```

**401 Unauthorized:**
```json
{
  "error": "Unauthorized",
  "details": "Invalid or missing authentication token"
}
```

**404 Not Found:**
```json
{
  "error": "Resource not found",
  "details": "Driver with ID 123 not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error",
  "details": "Database connection failed"
}
```

---

## 12. Data Models

### Driver Status Enum
- `available`: Driver is online and available for rides
- `busy`: Driver is currently on a ride
- `offline`: Driver is offline
- `inactive`: Driver account is deactivated

### Ride Status Enum
- `requested`: Ride has been requested by customer
- `assigned`: Driver has been assigned to the ride
- `accepted`: Driver has accepted the ride
- `in_progress`: Ride is currently in progress
- `completed`: Ride has been completed
- `cancelled`: Ride has been cancelled
- `no_driver_available`: No drivers available for the ride

### Ride Type Enum
- `immediate`: Ride requested for immediate pickup
- `scheduled`: Ride scheduled for future pickup

### Vehicle Type Enum
- `SUV`: Sport Utility Vehicle
- `SEDAN`: Sedan car
- `PICKUP_TRUCK`: Pickup truck
- `VAN`: Van
- `BOX_TRUCK`: Box truck
- `CAR`: General car type

### Delivery Status Enum
- `requested`: Delivery has been requested by customer
- `assigned`: Driver has been assigned to the delivery
- `accepted`: Driver has accepted the delivery
- `picked_up`: Driver has picked up the delivery
- `in_transit`: Delivery is currently in transit
- `delivered`: Delivery has been completed
- `cancelled`: Delivery has been cancelled
- `failed`: Delivery failed

### Package Type Enum
- `small`: Small package
- `medium`: Medium package
- `large`: Large package
- `extra_large`: Extra large package
- `fragile`: Fragile items
- `perishable`: Perishable items
- `electronics`: Electronics

### Delivery Type Enum
- `standard`: Standard delivery
- `express`: Express delivery
- `same_day`: Same day delivery

### Notification Type Enum
- `ride_assignment`: Notification for new ride assignment
- `ride_cancellation`: Notification for ride cancellation
- `ride_update`: Notification for ride updates
- `ride_reminder`: Notification for ride reminders
- `delivery_assignment`: Notification for new delivery assignment
- `delivery_update`: Notification for delivery updates

### Notification Status Enum
- `pending`: Notification is pending to be sent
- `sent`: Notification has been sent
- `read`: Notification has been read by driver
- `failed`: Notification failed to send

---

## 13. Rate Limits

- **Authentication endpoints:** 10 requests per minute
- **Location updates:** 60 requests per minute
- **Ride requests:** 5 requests per minute
- **Delivery requests:** 5 requests per minute
- **Other endpoints:** 100 requests per minute

---

## 14. WebSocket Events (Future Implementation)

The following WebSocket events are planned for real-time updates:

- `driver_location_update`: Real-time driver location updates
- `ride_status_update`: Real-time ride status updates
- `delivery_status_update`: Real-time delivery status updates
- `new_ride_request`: Real-time new ride request notifications
- `new_delivery_request`: Real-time new delivery request notifications
- `driver_status_change`: Real-time driver status changes

---

## 15. Testing

### Test Endpoints

Use the following test scripts to verify API functionality:

1. `test_complete_flow.py` - Complete Uber/Lyft style driver flow
2. `test_driver_app.py` - Driver app functionality
3. `test_ride_creation.py` - Ride creation and assignment
4. `test_delivery_flow.py` - Delivery flow testing
5. `manual_assign.py` - Manual driver assignment testing

### Running Tests

```bash
# Start the Flask app
python app.py

# Run complete flow test
python test_complete_flow.py

# Run driver app test
python test_driver_app.py

# Run delivery flow test
python test_delivery_flow.py
```

---

## 16. Deployment

### Environment Variables

Set the following environment variables for production:

```bash
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@host:port/database
JWT_SECRET_KEY=your_secret_key
```

### Production Considerations

1. **HTTPS**: Always use HTTPS in production
2. **Rate Limiting**: Implement proper rate limiting
3. **Database**: Use PostgreSQL for production
4. **Caching**: Implement Redis for caching
5. **Monitoring**: Set up application monitoring
6. **Logging**: Configure proper logging

---

## 17. Support

For API support and questions:

- **Documentation**: This file
- **Testing**: Use the provided test scripts
- **Issues**: Check the GitHub repository issues
- **Contact**: Support email for technical issues

---

*Last updated: July 10, 2025* 