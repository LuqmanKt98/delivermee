from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Dict, Optional, Tuple

class VehicleType(Enum):
    CAR = "CAR"
    SUV = "SUV"
    PICKUP_TRUCK = "PICKUP_TRUCK"
    CARGO_VAN = "CARGO_VAN"
    BOX_TRUCK = "BOX_TRUCK"

class PricingService:
    """
    Comprehensive pricing service for DeliverMee platform
    Implements vehicle-specific pricing, platform fees, and payment processing
    """
    
    # Vehicle-specific pricing (Base + Per KM) - Updated to match specifications
    VEHICLE_PRICING = {
        VehicleType.CAR: {
            'base_fare': Decimal('10.00'),
            'per_km_rate': Decimal('1.10')
        },
        VehicleType.SUV: {
            'base_fare': Decimal('30.00'),
            'per_km_rate': Decimal('1.20')
        },
        VehicleType.PICKUP_TRUCK: {
            'base_fare': Decimal('65.00'),  #  Correct: $65 base
            'per_km_rate': Decimal('1.50')  #  Correct: $1.50/km
        },
        VehicleType.CARGO_VAN: {
            'base_fare': Decimal('75.00'),  #  Correct: $75 base
            'per_km_rate': Decimal('1.50')  #  Correct: $1.50/km
        },
        VehicleType.BOX_TRUCK: {
            'base_fare': Decimal('90.00'),  #  Correct: $90 base
            'per_km_rate': Decimal('2.00')  #  Correct: $2.00/km
        }
    }
    
    # Platform and payment fees
    PLATFORM_FEE_PERCENTAGE = Decimal('0.15')  # 15%
    PAYMENT_PROCESSING_FEE_PERCENTAGE = Decimal('0.032')  # 3.2%
    
    # Special handling fees
    FRAGILE_HANDLING_FEE = Decimal('5.00')
    PERISHABLE_HANDLING_FEE = Decimal('8.00')
    SIGNATURE_REQUIRED_FEE = Decimal('3.00')
    
    # Delivery type multipliers
    DELIVERY_TYPE_MULTIPLIERS = {
        'standard': Decimal('1.00'),
        'express': Decimal('1.50'),
        'same_day': Decimal('2.00')
    }
    
    # Package type multipliers
    PACKAGE_TYPE_MULTIPLIERS = {
        'small': Decimal('1.00'),
        'medium': Decimal('1.20'),
        'large': Decimal('1.50'),
        'extra_large': Decimal('2.00'),
        'fragile': Decimal('1.80'),
        'perishable': Decimal('2.20'),
        'electronics': Decimal('1.50')
    }
    
    @classmethod
    def calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    @classmethod
    def calculate_ride_cost(cls, 
                          distance_km: float, 
                          vehicle_type: VehicleType,
                          special_instructions: Optional[str] = None) -> Dict[str, Decimal]:
        """
        Calculate ride cost based on distance and vehicle type
        
        Args:
            distance_km: Distance in kilometers
            vehicle_type: Type of vehicle
            special_instructions: Any special instructions that might affect pricing
            
        Returns:
            Dictionary with cost breakdown
        """
        print(f"DEBUG: calculate_ride_cost called with distance_km={distance_km} ({type(distance_km)}), vehicle_type={vehicle_type} ({type(vehicle_type)}), special_instructions={special_instructions}")
        if vehicle_type not in cls.VEHICLE_PRICING:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")
        
        pricing = cls.VEHICLE_PRICING[vehicle_type]
        base_fare = pricing['base_fare']
        per_km_rate = pricing['per_km_rate']
        
        # Calculate base cost
        distance_cost = Decimal(str(distance_km)) * per_km_rate
        subtotal = base_fare + distance_cost
        
        # Apply special handling fees if any
        special_fees = Decimal('0.00')
        if special_instructions:
            special_fees = cls._calculate_special_fees(special_instructions)
        
        subtotal += special_fees
        
        # Calculate fees according to specifications:
        # - Platform fee = 15% of delivery total (added on top)
        # - Payment processing fee = 3.2% of delivery total
        # - Driver gets 100% of delivery amount (plus tips)
        platform_fee = subtotal * cls.PLATFORM_FEE_PERCENTAGE
        payment_fee = subtotal * cls.PAYMENT_PROCESSING_FEE_PERCENTAGE
        
        # Calculate totals
        total_cost = subtotal + platform_fee + payment_fee
        driver_earnings = subtotal  # Driver gets 100% of delivery amount (plus tips)
        
        return {
            'base_fare': base_fare,
            'distance_cost': distance_cost,
            'special_fees': special_fees,
            'subtotal': subtotal,
            'platform_fee': platform_fee,
            'payment_processing_fee': payment_fee,
            'total_cost': total_cost,
            'driver_earnings': driver_earnings,
            'distance_km': Decimal(str(distance_km)),
            'vehicle_type': vehicle_type.value
        }
    
    @classmethod
    def calculate_delivery_cost(cls,
                              distance_km: float,
                              vehicle_type: VehicleType,
                              package_type: str = 'medium',
                              delivery_type: str = 'standard',
                              is_fragile: bool = False,
                              is_perishable: bool = False,
                              requires_signature: bool = False,
                              special_instructions: Optional[str] = None) -> Dict[str, Decimal]:
        """
        Calculate delivery cost with comprehensive pricing model
        
        Args:
            distance_km: Distance in kilometers
            vehicle_type: Type of vehicle
            package_type: Type of package (small, medium, large, etc.)
            delivery_type: Type of delivery (standard, express, same_day)
            is_fragile: Whether item is fragile
            is_perishable: Whether item is perishable
            requires_signature: Whether signature is required
            special_instructions: Any special instructions
            
        Returns:
            Dictionary with detailed cost breakdown
        """
        if vehicle_type not in cls.VEHICLE_PRICING:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")
        
        pricing = cls.VEHICLE_PRICING[vehicle_type]
        base_fare = pricing['base_fare']
        per_km_rate = pricing['per_km_rate']
        
        # Calculate base cost
        distance_cost = Decimal(str(distance_km)) * per_km_rate
        subtotal = base_fare + distance_cost
        
        # Apply package type multiplier
        package_multiplier = cls.PACKAGE_TYPE_MULTIPLIERS.get(package_type, Decimal('1.00'))
        subtotal = subtotal * package_multiplier
        
        # Apply delivery type multiplier
        delivery_multiplier = cls.DELIVERY_TYPE_MULTIPLIERS.get(delivery_type, Decimal('1.00'))
        subtotal = subtotal * delivery_multiplier
        
        # Apply special handling fees
        special_fees = Decimal('0.00')
        if is_fragile:
            special_fees += cls.FRAGILE_HANDLING_FEE
        if is_perishable:
            special_fees += cls.PERISHABLE_HANDLING_FEE
        if requires_signature:
            special_fees += cls.SIGNATURE_REQUIRED_FEE
        
        # Add special fees from instructions
        if special_instructions:
            instruction_fees = cls._calculate_special_fees(special_instructions)
            special_fees += instruction_fees
        
        subtotal += special_fees
        
        # Calculate fees according to specifications:
        # - Platform fee = 15% of delivery total (added on top)
        # - Payment processing fee = 3.2% of delivery total
        # - Driver gets 100% of delivery amount (plus tips)
        platform_fee = subtotal * cls.PLATFORM_FEE_PERCENTAGE
        payment_fee = subtotal * cls.PAYMENT_PROCESSING_FEE_PERCENTAGE
        
        # Calculate totals
        total_cost = subtotal + platform_fee + payment_fee
        driver_earnings = subtotal  # Driver gets 100% of delivery amount (plus tips)
        
        return {
            'base_fare': base_fare,
            'distance_cost': distance_cost,
            'package_multiplier': package_multiplier,
            'delivery_multiplier': delivery_multiplier,
            'special_fees': special_fees,
            'subtotal': subtotal,
            'platform_fee': platform_fee,
            'payment_processing_fee': payment_fee,
            'total_cost': total_cost,
            'driver_earnings': driver_earnings,
            'distance_km': Decimal(str(distance_km)),
            'vehicle_type': vehicle_type.value,
            'package_type': package_type,
            'delivery_type': delivery_type
        }
    
    @classmethod
    def _calculate_special_fees(cls, special_instructions: str) -> Decimal:
        """
        Calculate additional fees based on special instructions
        """
        instructions = special_instructions.lower()
        fees = Decimal('0.00')
        
        # Add fees for specific keywords
        if 'fragile' in instructions or 'breakable' in instructions:
            fees += cls.FRAGILE_HANDLING_FEE
        if 'perishable' in instructions or 'fresh' in instructions or 'frozen' in instructions:
            fees += cls.PERISHABLE_HANDLING_FEE
        if 'signature' in instructions or 'sign' in instructions:
            fees += cls.SIGNATURE_REQUIRED_FEE
        if 'urgent' in instructions or 'rush' in instructions:
            fees += Decimal('5.00')  # Rush fee
        if 'heavy' in instructions or 'bulky' in instructions:
            fees += Decimal('3.00')  # Heavy item fee
        
        return fees
    
    @classmethod
    def calculate_estimated_duration(cls, distance_km: float, vehicle_type: VehicleType) -> int:
        """
        Calculate estimated duration in minutes based on distance and vehicle type
        """
        # Base speed varies by vehicle type (km/h)
        vehicle_speeds = {
            VehicleType.CAR: 30,      # City driving average
            VehicleType.SUV: 28,       # Slightly slower due to size
            VehicleType.PICKUP_TRUCK: 25,  # Slower due to size and cargo
            VehicleType.CARGO_VAN: 25,     # Similar to pickup
            VehicleType.BOX_TRUCK: 20      # Slowest due to size
        }
        
        speed = vehicle_speeds.get(vehicle_type, 30)
        duration_hours = distance_km / speed
        duration_minutes = int(duration_hours * 60)
        
        # Add buffer time for pickup/delivery
        buffer_minutes = 15
        return duration_minutes + buffer_minutes
    
    @classmethod
    def get_vehicle_pricing_info(cls) -> Dict[str, Dict]:
        """
        Get pricing information for all vehicle types
        """
        pricing_info = {}
        for vehicle_type, pricing in cls.VEHICLE_PRICING.items():
            pricing_info[vehicle_type.value] = {
                'base_fare': float(pricing['base_fare']),
                'per_km_rate': float(pricing['per_km_rate']),
                'description': cls._get_vehicle_description(vehicle_type)
            }
        return pricing_info
    
    @classmethod
    def _get_vehicle_description(cls, vehicle_type: VehicleType) -> str:
        """
        Get description for vehicle type
        """
        descriptions = {
            VehicleType.CAR: "Standard car for passengers and small packages",
            VehicleType.SUV: "Sport Utility Vehicle for larger passengers and medium packages",
            VehicleType.PICKUP_TRUCK: "Pickup truck for large items and construction materials",
            VehicleType.CARGO_VAN: "Cargo van for commercial deliveries and large packages",
            VehicleType.BOX_TRUCK: "Box truck for heavy commercial deliveries and furniture"
        }
        return descriptions.get(vehicle_type, "Vehicle for transportation and delivery")
    
    @classmethod
    def format_currency(cls, amount: Decimal) -> str:
        """
        Format decimal amount as currency string
        """
        return f"${amount:.2f}"
    
    @classmethod
    def round_to_nearest_cent(cls, amount: Decimal) -> Decimal:
        """
        Round amount to nearest cent
        """
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) 