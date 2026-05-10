from extensions import db
from enum import Enum

class VehicleType(Enum):
    SUV = "SUV"
    SEDAN = "SEDAN"
    PICKUP_TRUCK = "PICKUP_TRUCK"
    CARGO_VAN = "CARGO_VAN"
    BOX_TRUCK = "BOX_TRUCK"
    CAR = "CAR"

class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('drivers.id'), nullable=False)
    
    # Vehicle details
    vehicle_type = db.Column(db.Enum(VehicleType), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(50), nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    
    # Vehicle specifications
    capacity = db.Column(db.Integer, nullable=True)  # Number of passengers
    cargo_capacity = db.Column(db.Float, nullable=True)  # Cargo capacity in cubic feet
    fuel_type = db.Column(db.String(20), nullable=True)  # Gas, Electric, Hybrid, etc.
    
    # Vehicle status
    is_active = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Relationships
    driver = db.relationship('Driver', backref='vehicles')

    def __init__(self, driver_id, vehicle_type, make, model, year, color, license_plate, **kwargs):
        self.driver_id = driver_id
        self.vehicle_type = vehicle_type
        self.make = make
        self.model = model
        self.year = year
        self.color = color
        self.license_plate = license_plate
        
        # Set optional fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            'id': self.id,
            'driver_id': self.driver_id,
            'vehicle_type': self.vehicle_type.value if self.vehicle_type else None,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'color': self.color,
            'license_plate': self.license_plate,
            'capacity': self.capacity,
            'cargo_capacity': self.cargo_capacity,
            'fuel_type': self.fuel_type,
            'is_active': self.is_active,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_full_name(self):
        """Get full vehicle name"""
        return f"{self.year} {self.make} {self.model}"

    def __repr__(self):
        return f'<Vehicle {self.get_full_name()}>' 