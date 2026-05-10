# 🏗️ Uber/Lyft-Style Ride-Sharing System Architecture

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Database Schema](#database-schema)
4. [API Structure](#api-structure)
5. [Core Components](#core-components)
6. [Data Flow](#data-flow)
7. [Security Architecture](#security-architecture)
8. [Scalability Considerations](#scalability-considerations)

---

## System Overview

The Uber/Lyft-style ride-sharing system is built as a RESTful API using Flask, SQLAlchemy, and PostgreSQL. The system follows a microservices-inspired architecture with clear separation of concerns.

### Technology Stack
- **Backend Framework**: Flask
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **API Documentation**: Flask-RESTX (Swagger)
- **Database Migrations**: Alembic
- **Testing**: Python unittest with requests

### System Components
1. **Authentication Service** - User registration and JWT management
2. **Driver Management** - Driver app functionality
3. **Ride Management** - Ride creation and assignment
4. **Notification Service** - Real-time notifications
5. **Location Service** - GPS tracking and proximity calculations
6. **Payment Service** - Earnings and fare calculation

---

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Driver App    │    │  Customer App   │    │  Admin Panel    │
│   (Mobile)      │    │   (Mobile)      │    │   (Web)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (Nginx)       │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Flask API     │
                    │   (Gunicorn)    │
                    └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Redis Cache   │    │   File Storage  │
│   (Primary DB)  │    │   (Sessions)    │    │   (Logs/Media)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Database Schema

### Core Tables

#### 1. Drivers Table
```sql
CREATE TABLE drivers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash BYTEA NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    license_number VARCHAR(50) UNIQUE NOT NULL,
    vehicle_plate VARCHAR(20) NOT NULL,
    vehicle_model VARCHAR(100) NOT NULL,
    vehicle_color VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'offline',
    current_latitude DECIMAL(10, 8),
    current_longitude DECIMAL(11, 8),
    last_location_update TIMESTAMP,
    rating DECIMAL(3, 2) DEFAULT 0.0,
    total_rides INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. Customers Table
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash BYTEA NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. Rides Table
```sql
CREATE TABLE rides (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    driver_id INTEGER REFERENCES drivers(id),
    pickup_address TEXT NOT NULL,
    dropoff_address TEXT NOT NULL,
    pickup_latitude DECIMAL(10, 8),
    pickup_longitude DECIMAL(11, 8),
    dropoff_latitude DECIMAL(10, 8),
    dropoff_longitude DECIMAL(11, 8),
    ride_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'requested',
    estimated_distance DECIMAL(8, 2),
    estimated_duration INTEGER,
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    scheduled_time TIMESTAMP,
    requested_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_time TIMESTAMP,
    accepted_time TIMESTAMP,
    pickup_time TIMESTAMP,
    completed_time TIMESTAMP,
    cancelled_time TIMESTAMP,
    vehicle_type VARCHAR(20),
    special_instructions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. Notifications Table
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    driver_id INTEGER REFERENCES drivers(id),
    ride_id INTEGER REFERENCES rides(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Vehicles Table
```sql
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    driver_id INTEGER REFERENCES drivers(id),
    vehicle_type VARCHAR(20) NOT NULL,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    color VARCHAR(50) NOT NULL,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_drivers_status ON drivers(status);
CREATE INDEX idx_drivers_location ON drivers(current_latitude, current_longitude);
CREATE INDEX idx_rides_status ON rides(status);
CREATE INDEX idx_rides_customer ON rides(customer_id);
CREATE INDEX idx_rides_driver ON rides(driver_id);
CREATE INDEX idx_rides_requested_time ON rides(requested_time);
CREATE INDEX idx_notifications_driver ON notifications(driver_id);
CREATE INDEX idx_notifications_status ON notifications(status);
```

---

## API Structure

### Namespace Organization
```
/api
├── /drivers          # Driver registration and authentication
├── /customers        # Customer registration and authentication  
├── /driver-app       # Driver app functionality
├── /rides            # Ride management
└── /notifications    # Notification system
```

### Endpoint Categories

#### 1. Authentication Endpoints
- `POST /drivers/register` - Driver registration
- `POST /drivers/login` - Driver authentication
- `POST /customers/register` - Customer registration
- `POST /customers/login` - Customer authentication

#### 2. Driver App Endpoints
- `POST /driver-app/location` - Update driver location
- `POST /driver-app/go-online` - Set driver online
- `POST /driver-app/go-offline` - Set driver offline
- `GET /driver-app/status` - Get driver status
- `GET /driver-app/ride-requests` - Get available rides
- `POST /driver-app/accept-ride/{id}` - Accept ride
- `POST /driver-app/start-ride/{id}` - Start ride
- `POST /driver-app/complete-ride/{id}` - Complete ride
- `GET /driver-app/earnings` - Get earnings
- `GET /driver-app/ride-history` - Get ride history

#### 3. Ride Management Endpoints
- `POST /rides/schedule` - Create ride request
- `GET /rides/` - Get customer ride history
- `GET /rides/{id}` - Get ride details
- `PUT /rides/{id}` - Update ride
- `POST /rides/{id}/cancel` - Cancel ride

#### 4. Notification Endpoints
- `GET /drivers/notifications` - Get driver notifications
- `POST /drivers/notifications/{id}/read` - Mark notification read

---

## Core Components

### 1. Authentication Service
**File**: `routes/driver_routes.py`, `routes/user_routes.py`

**Responsibilities**:
- User registration and validation
- JWT token generation and validation
- Password hashing and verification
- Input validation and sanitization

**Key Features**:
- Email and phone number uniqueness validation
- Password strength requirements
- JWT token expiration handling
- Account status management

### 2. Driver Management Service
**File**: `routes/driver_app.py`

**Responsibilities**:
- Driver location tracking
- Online/offline status management
- Ride request handling
- Driver earnings calculation

**Key Features**:
- Real-time location updates
- Proximity-based ride assignment
- Driver status transitions
- Earnings analytics

### 3. Ride Management Service
**File**: `routes/ride_routes.py`

**Responsibilities**:
- Ride creation and scheduling
- Driver assignment logic
- Ride status management
- Fare calculation

**Key Features**:
- Immediate and scheduled rides
- Automatic driver assignment
- Ride status tracking
- Distance and cost estimation

### 4. Notification Service
**File**: `services/notification_service.py`

**Responsibilities**:
- Push notification management
- In-app notification handling
- Notification status tracking

**Key Features**:
- Real-time notifications
- Notification queuing
- Delivery status tracking
- Notification preferences

### 5. Database Models
**Files**: `models/driver.py`, `models/user.py`, `models/ride.py`, `models/notification.py`

**Responsibilities**:
- Data structure definition
- Database relationships
- Business logic encapsulation
- Data validation

---

## Data Flow

### 1. Driver Registration Flow
```
Driver App → POST /drivers/register → Validation → Database → JWT Token → Response
```

### 2. Ride Request Flow
```
Customer App → POST /rides/schedule → Driver Assignment → Notification → Response
```

### 3. Driver Assignment Flow
```
Ride Request → Location Check → Available Drivers → Proximity Calculation → Assignment
```

### 4. Ride Completion Flow
```
Driver App → POST /driver-app/complete-ride → Earnings Update → Status Update → Response
```

### 5. Real-time Location Flow
```
Driver App → POST /driver-app/location → Database Update → Proximity Check → Ride Assignment
```

---

## Security Architecture

### 1. Authentication Security
- **JWT Tokens**: Secure token-based authentication
- **Password Hashing**: bcrypt for password security
- **Token Expiration**: 24-hour token lifetime
- **Input Validation**: Comprehensive input sanitization

### 2. Data Security
- **SQL Injection Protection**: SQLAlchemy ORM
- **XSS Protection**: JSON response handling
- **Data Encryption**: Sensitive data encryption
- **Access Control**: Role-based access control

### 3. API Security
- **Rate Limiting**: Request throttling (planned)
- **CORS Protection**: Cross-origin request handling
- **HTTPS Enforcement**: SSL/TLS in production
- **Error Handling**: Secure error responses

### 4. Database Security
- **Connection Security**: SSL database connections
- **Query Optimization**: Prepared statements
- **Data Backup**: Regular backup procedures
- **Access Logging**: Database access monitoring

---

## Scalability Considerations

### 1. Horizontal Scaling
- **Load Balancing**: Multiple API instances
- **Database Sharding**: Geographic data distribution
- **Caching Layer**: Redis for session management
- **CDN Integration**: Static content delivery

### 2. Performance Optimization
- **Database Indexing**: Optimized query performance
- **Connection Pooling**: Database connection management
- **Caching Strategy**: Redis for frequently accessed data
- **Async Processing**: Background task processing

### 3. Monitoring and Logging
- **Application Monitoring**: Performance metrics
- **Error Tracking**: Comprehensive error logging
- **User Analytics**: Usage pattern analysis
- **System Health**: Real-time system monitoring

### 4. Future Enhancements
- **Microservices**: Service decomposition
- **Message Queues**: Asynchronous processing
- **Real-time Communication**: WebSocket integration
- **Machine Learning**: Predictive analytics

---

## Deployment Architecture

### Development Environment
```
┌─────────────────┐
│   Flask Dev     │
│   Server        │
└─────────────────┘
         │
┌─────────────────┐
│   PostgreSQL    │
│   (Local)       │
└─────────────────┘
```

### Production Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Server 1  │    │   API Server 2  │
│   (Nginx)       │    │   (Gunicorn)    │    │   (Gunicorn)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Master)      │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Redis Cache   │
                    └─────────────────┘
```

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: 100 Mbps

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 100GB+ SSD
- **Network**: 1 Gbps

### Production Requirements
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **Storage**: 500GB+ SSD
- **Network**: 10 Gbps
- **Load Balancer**: Required
- **Database**: Master-Slave setup
- **Monitoring**: Comprehensive logging

---

*This architecture provides a solid foundation for a scalable, secure, and maintainable ride-sharing platform that can handle real-world traffic and user demands.* 