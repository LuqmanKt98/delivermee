from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime, timedelta
import os

from repositories.delivery_repository import DeliveryRepository
from settings import USE_FIREBASE_DB
from services.storage_service import storage_service, get_storage_service
from utils.firebase_auth_middleware import firebase_customer_required, firebase_driver_required


delivery_api = Namespace("deliveries", description="DeliverMe delivery operations (Firestore mode)")


create_delivery_model = delivery_api.model(
    "CreateDelivery",
    {
        "pickup_address": fields.String(required=True),
        "dropoff_address": fields.String(required=True),
        "pickup_latitude": fields.Float(),
        "pickup_longitude": fields.Float(),
        "dropoff_latitude": fields.Float(),
        "dropoff_longitude": fields.Float(),
        "item_name": fields.String(required=True),
        "item_description": fields.String(),
        "item_photo_url": fields.String(),
        "vehicle_type": fields.String(required=True, description="car/suv/pickup_truck/cargo_van/box_truck"),
        "package_size": fields.String(description="small/medium/large/extra_large/huge"),
        "weight": fields.Float(required=True),
        "item_count": fields.Integer(default=1),
        "schedule_type": fields.String(default="immediate", description="immediate/scheduled"),
        "scheduled_date": fields.String(description="ISO 8601 date format (YYYY-MM-DD)"),
        "time_slot": fields.String(description="Time slot in HH:MM-HH:MM format (e.g., 08:00-10:00)"),
        "delivery_type": fields.String(default="standard", description="standard/express/same_day"),
        "delivery_preference": fields.String(default="attended", description="attended/leave_at_location"),
        "is_fragile": fields.Boolean(default=False),
        "is_perishable": fields.Boolean(default=False),
        "requires_signature": fields.Boolean(default=False),
        "special_instructions": fields.String(),
    },
)


@delivery_api.route("/create")
class CreateDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @delivery_api.expect(create_delivery_model)
    @firebase_customer_required
    def post(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        customer_id = g.customer_id
        data = request.get_json() or {}

        required = ["pickup_address", "dropoff_address", "item_name", "vehicle_type", "weight"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        # Auto-calculate estimated_cost if not provided
        if not data.get('estimated_cost'):
            try:
                # Simple pricing calculation based on vehicle type
                vehicle_rates = {
                    'car': {'base': 10.0, 'per_km': 1.5},
                    'suv': {'base': 15.0, 'per_km': 2.0},
                    'cargo_van': {'base': 20.0, 'per_km': 2.5},
                    'pickup_truck': {'base': 18.0, 'per_km': 2.2},
                    'box_truck': {'base': 25.0, 'per_km': 3.0},
                }
                
                vehicle_type = data.get('vehicle_type', 'cargo_van').lower()
                rates = vehicle_rates.get(vehicle_type, vehicle_rates['cargo_van'])
                
                # Estimate distance (default 10km if not provided)
                distance_km = data.get('estimated_distance_km', 10.0)
                
                # Calculate cost
                base_fare = rates['base']
                distance_cost = distance_km * rates['per_km']
                subtotal = base_fare + distance_cost
                
                # Add fees
                platform_fee = subtotal * 0.15  # 15%
                payment_fee = subtotal * 0.03   # 3%
                
                estimated_cost = subtotal + platform_fee + payment_fee
                data['estimated_cost'] = round(estimated_cost, 2)
                
                print(f"💰 Auto-calculated estimated_cost: ${estimated_cost:.2f}")
                print(f"   Base: ${base_fare}, Distance: ${distance_cost:.2f}, Fees: ${platform_fee + payment_fee:.2f}")
            except Exception as e:
                print(f"⚠️ Error calculating cost: {e}")
                # Set a default cost if calculation fails
                data['estimated_cost'] = 25.0

        # Log scheduled delivery fields for debugging
        print('📅 ─── SCHEDULED DELIVERY FIELDS ───')
        print(f"   Schedule Type: {data.get('schedule_type', 'immediate')}")
        print(f"   Scheduled Date: {data.get('scheduled_date', 'N/A')}")
        print(f"   Time Slot: {data.get('time_slot', 'N/A')}")
        print(f"   Delivery Preference: {data.get('delivery_preference', 'attended')}")
        print('📅 ─── END ───')

        repo = DeliveryRepository()
        delivery = repo.create(customer_id=customer_id, data=data)
        return {"message": "Delivery created", "delivery": delivery}, 201


@delivery_api.route("/")
class ListDeliveries(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def get(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        try:
            customer_id = g.customer_id
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            
            print(f"📋 Customer {customer_id} requesting deliveries (limit={limit}, offset={offset})")
            
            deliveries = DeliveryRepository().list_for_customer(customer_id, limit=limit, offset=offset)
            
            print(f"✅ Found {len(deliveries)} deliveries for customer {customer_id}")
            
            return {"deliveries": deliveries, "count": len(deliveries)}, 200
        except Exception as e:
            print(f"❌ Error in list deliveries endpoint: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to load deliveries", "details": str(e)}, 500


@delivery_api.route("/<int:delivery_id>")
class GetDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def get(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        customer_id = g.customer_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404
        if int(doc.get("customer_id") or 0) != int(customer_id):
            return {"error": "Access denied"}, 403
        return repo.to_public_dict(doc), 200


@delivery_api.route("/<int:delivery_id>/status")
class GetDeliveryStatus(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def get(self, delivery_id: int):
        """Get delivery status and tracking information"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        try:
            customer_id = g.customer_id
            repo = DeliveryRepository()
            doc = repo.get_by_id(delivery_id)
            
            if not doc:
                return {"error": "Delivery not found"}, 404
            
            if int(doc.get("customer_id") or 0) != int(customer_id):
                return {"error": "Access denied"}, 403
            
            # Helper function to convert datetime to string
            def serialize_datetime(value):
                if value is None:
                    return None
                if isinstance(value, datetime):
                    return value.isoformat()
                return value
            
            # Return complete delivery information
            return {
                "delivery_id": doc.get("delivery_id"),
                "status": doc.get("status"),
                "payment_status": doc.get("payment_status"),
                "tracking_number": doc.get("tracking_number"),
                "driver_id": doc.get("driver_id"),
                "customer_id": doc.get("customer_id"),
                
                # Pickup information
                "pickup_address": doc.get("pickup_address"),
                "pickup_latitude": doc.get("pickup_latitude"),
                "pickup_longitude": doc.get("pickup_longitude"),
                
                # Dropoff information
                "dropoff_address": doc.get("dropoff_address"),
                "dropoff_latitude": doc.get("dropoff_latitude"),
                "dropoff_longitude": doc.get("dropoff_longitude"),
                
                # Item information
                "item_name": doc.get("item_name"),
                "item_description": doc.get("item_description"),
                "item_photo_url": doc.get("item_photo_url"),
                "item_count": doc.get("item_count"),
                
                # Package information
                "package_size": doc.get("package_size"),
                "package_type": doc.get("package_type"),
                "weight": doc.get("weight"),
                "vehicle_type": doc.get("vehicle_type"),
                
                # Delivery details
                "delivery_type": doc.get("delivery_type"),
                "delivery_preference": doc.get("delivery_preference"),
                "schedule_type": doc.get("schedule_type"),
                "scheduled_date": doc.get("scheduled_date"),
                "time_slot": doc.get("time_slot"),
                
                # Special requirements
                "is_fragile": doc.get("is_fragile"),
                "is_perishable": doc.get("is_perishable"),
                "requires_signature": doc.get("requires_signature"),
                "special_instructions": doc.get("special_instructions"),
                
                # Timestamps
                "created_at": serialize_datetime(doc.get("created_at")),
                "updated_at": serialize_datetime(doc.get("updated_at")),
                "assigned_time": serialize_datetime(doc.get("assigned_time")),
                "accepted_time": serialize_datetime(doc.get("accepted_time")),
                "pickup_time": serialize_datetime(doc.get("pickup_time")),
                "delivered_time": serialize_datetime(doc.get("delivered_time")),
                
                # Cost information
                "estimated_cost": doc.get("estimated_cost"),
                "actual_cost": doc.get("actual_cost"),
                "estimated_distance_km": doc.get("estimated_distance_km"),
                "actual_distance_km": doc.get("actual_distance_km"),
                "estimated_duration": doc.get("estimated_duration"),
                "actual_duration": doc.get("actual_duration"),
            }, 200
        except Exception as e:
            print(f"❌ Error in delivery status endpoint: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to get delivery status", "details": str(e)}, 500


@delivery_api.route("/track/<string:tracking_number>")
class TrackByNumber(Resource):
    def get(self, tracking_number: str):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        repo = DeliveryRepository()
        doc = repo.get_by_tracking_number(tracking_number)
        if not doc:
            return {"error": "Delivery not found"}, 404
        return repo.to_public_dict(doc), 200


@delivery_api.route("/<int:delivery_id>/cancel")
class CancelDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)

        if not doc:
            return {"error": "Delivery not found"}, 404

        # Check if driver is assigned to this delivery
        if int(doc.get("driver_id") or 0) != int(driver_id):
            return {"error": "Access denied - you are not assigned to this delivery"}, 403

        current_status = (doc.get("status") or "").lower()

        # Allow cancellation only for accepted deliveries
        if current_status not in {"accepted", "assigned"}:
            return {"error": f"Delivery cannot be cancelled (status: {current_status}). Only accepted deliveries can be cancelled."}, 400

        # Get cancellation reason and review from request
        data = request.get_json() or {}
        cancellation_reason = data.get("cancellation_reason")
        review = data.get("review")

        print(f"🚫 Driver {driver_id} cancelling delivery {delivery_id}")
        print(f"   Reason: {cancellation_reason}")
        print(f"   Review: {review}")

        ok = repo.set_status(delivery_id, "cancelled", timestamp_field="cancelled_time")
        if not ok:
            return {"error": "Failed to cancel delivery"}, 500

        print(f"✅ Delivery {delivery_id} cancelled by driver {driver_id}")
        return {"message": "Delivery cancelled successfully", "delivery_id": delivery_id}, 200


@delivery_api.route("/<int:delivery_id>/assign-driver/<int:driver_id>")
class AssignDriver(Resource):
    """
    Simple driver assignment endpoint (Firestore mode).
    This is intentionally minimal; production matching/dispatch logic can be added later.
    """

    def post(self, delivery_id: int, driver_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404

        ok = repo.update_fields(
            delivery_id,
            {
                "driver_id": int(driver_id),
                "status": "assigned",
                "assigned_time": datetime.utcnow(),
            },
        )
        if not ok:
            return {"error": "Failed to assign driver"}, 500
        return {"message": "Driver assigned", "delivery_id": delivery_id, "driver_id": driver_id}, 200


@delivery_api.route("/<int:delivery_id>/auto-assign")
class AutoAssignDriver(Resource):
    """Auto-assign delivery to an available driver"""
    
    def post(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        
        try:
            from repositories.driver_repository import DriverRepository
            
            delivery_repo = DeliveryRepository()
            driver_repo = DriverRepository()
            
            # Get delivery
            delivery = delivery_repo.get_by_id(delivery_id)
            if not delivery:
                return {"error": "Delivery not found"}, 404
            
            # Check if already assigned
            if delivery.get("driver_id"):
                return {"error": "Delivery already assigned", "driver_id": delivery.get("driver_id")}, 400
            
            # Find available drivers (status = 'active' or 'available')
            db = get_firestore()
            drivers_ref = db.collection("drivers")
            
            # Query for active/available drivers
            available_drivers = []
            for doc in drivers_ref.where("status", "in", ["active", "available"]).stream():
                driver_data = doc.to_dict()
                if driver_data:
                    available_drivers.append(driver_data)
            
            if not available_drivers:
                return {"error": "No available drivers found"}, 404
            
            # Simple assignment: pick first available driver
            # TODO: Implement smart matching based on location, vehicle type, etc.
            selected_driver = available_drivers[0]
            driver_id = selected_driver.get("id") or selected_driver.get("driver_id")
            
            if not driver_id:
                return {"error": "Invalid driver data"}, 500
            
            # Assign driver
            ok = delivery_repo.update_fields(
                delivery_id,
                {
                    "driver_id": int(driver_id),
                    "status": "assigned",
                    "assigned_time": datetime.utcnow(),
                },
            )
            
            if not ok:
                return {"error": "Failed to assign driver"}, 500
            
            print(f"✅ Auto-assigned delivery {delivery_id} to driver {driver_id}")
            return {
                "message": "Driver auto-assigned successfully",
                "delivery_id": delivery_id,
                "driver_id": driver_id,
                "driver_name": selected_driver.get("name"),
            }, 200
            
        except Exception as e:
            print(f"❌ Error in auto-assign: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to auto-assign driver", "details": str(e)}, 500


@delivery_api.route("/driver/assigned")
class DriverAssigned(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def get(self):
        """Get deliveries assigned to this driver + unassigned deliveries"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        try:
            driver_id = g.driver_id
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            
            print(f"🚀 Driver {driver_id} requesting assigned deliveries (limit={limit}, offset={offset})")
            
            # Get deliveries assigned to this driver (any active status)
            repo = DeliveryRepository()
            assigned_deliveries = repo.list_for_driver(
                driver_id, 
                limit=limit, 
                offset=offset,
                statuses=["assigned", "accepted", "picked_up", "in_transit"]
            )
            
            # Get unassigned deliveries using simple query (no composite index needed)
            from services.firestore_client import get_firestore
            db = get_firestore()
            deliveries_ref = db.collection("deliveries")
            
            print(f"🔍 Querying for unassigned deliveries...")
            
            # Get driver's vehicle type for filtering
            from repositories.driver_repository import DriverRepository
            driver_repo = DriverRepository()
            driver_doc = driver_repo.get_by_id(driver_id)
            driver_vehicle_type = driver_doc.get('vehicle_type', '').lower() if driver_doc else None
            
            print(f"🚗 Driver {driver_id} vehicle type: {driver_vehicle_type}")
            
            # Vehicle type compatibility mapping
            # Each vehicle type can handle deliveries for itself and smaller vehicles
            # Normalize all keys to lowercase with underscores
            vehicle_hierarchy = {
                'car': ['car'],
                'suv': ['car', 'suv'],
                'cargo_van': ['car', 'suv', 'cargo_van'],
                'pickup_truck': ['car', 'suv', 'pickup_truck'],
                'box_truck': ['car', 'suv', 'cargo_van', 'pickup_truck', 'box_truck']
            }
            
            compatible_vehicle_types = vehicle_hierarchy.get(driver_vehicle_type, [driver_vehicle_type]) if driver_vehicle_type else []
            print(f"✅ Compatible vehicle types for driver: {compatible_vehicle_types}")
            
            # Simple query: just get recent deliveries, filter client-side
            try:
                recent_query = deliveries_ref\
                    .order_by("created_at", direction="DESCENDING")\
                    .limit(100)
                
                unassigned_deliveries = []
                for doc in recent_query.stream():
                    delivery_data = doc.to_dict()
                    # Filter for unassigned deliveries (requested or confirmed)
                    # AND not rejected by this driver
                    # AND vehicle type matches driver's capability
                    rejected_by = delivery_data.get("rejected_by_drivers", [])
                    if not isinstance(rejected_by, list):
                        rejected_by = []
                    
                    delivery_vehicle_type = delivery_data.get('vehicle_type', '').lower()
                    
                    # Check if driver can handle this delivery's vehicle type
                    vehicle_type_match = (not driver_vehicle_type or 
                                         not delivery_vehicle_type or 
                                         delivery_vehicle_type in compatible_vehicle_types)
                    
                    if (delivery_data and 
                        delivery_data.get("status") in ["requested", "confirmed"] and 
                        not delivery_data.get("driver_id") and
                        driver_id not in rejected_by and
                        vehicle_type_match):
                        unassigned_deliveries.append(repo.to_public_dict(delivery_data))
                        print(f"   📦 Unassigned: Delivery {delivery_data.get('id')}: {delivery_data.get('item_name')} (vehicle: {delivery_vehicle_type})")
                        if len(unassigned_deliveries) >= 20:  # Limit unassigned to 20
                            break
                    elif delivery_data and delivery_data.get("status") in ["requested", "confirmed"] and not delivery_data.get("driver_id") and driver_id not in rejected_by and not vehicle_type_match:
                        print(f"   ❌ Filtered out: Delivery {delivery_data.get('id')} requires {delivery_vehicle_type}, driver has {driver_vehicle_type}")
                
                print(f"✅ Found {len(unassigned_deliveries)} unassigned deliveries")
            except Exception as e:
                print(f"❌ Error querying unassigned deliveries with order_by: {e}")
                print(f"🔄 Trying without order_by...")
                # Fallback: query without ordering
                try:
                    simple_query = deliveries_ref.limit(100)
                    unassigned_deliveries = []
                    for doc in simple_query.stream():
                        delivery_data = doc.to_dict()
                        rejected_by = delivery_data.get("rejected_by_drivers", [])
                        if not isinstance(rejected_by, list):
                            rejected_by = []
                        
                        delivery_vehicle_type = delivery_data.get('vehicle_type', '').lower()
                        
                        # Check if driver can handle this delivery's vehicle type
                        vehicle_type_match = (not driver_vehicle_type or 
                                             not delivery_vehicle_type or 
                                             delivery_vehicle_type in compatible_vehicle_types)
                        
                        if (delivery_data and 
                            delivery_data.get("status") in ["requested", "confirmed"] and 
                            not delivery_data.get("driver_id") and
                            driver_id not in rejected_by and
                            vehicle_type_match):
                            unassigned_deliveries.append(repo.to_public_dict(delivery_data))
                            print(f"   📦 Unassigned: Delivery {delivery_data.get('id')}: {delivery_data.get('item_name')} (vehicle: {delivery_vehicle_type})")
                            if len(unassigned_deliveries) >= 20:
                                break
                        elif delivery_data and delivery_data.get("status") in ["requested", "confirmed"] and not delivery_data.get("driver_id") and driver_id not in rejected_by and not vehicle_type_match:
                            print(f"   ❌ Filtered out: Delivery {delivery_data.get('id')} requires {delivery_vehicle_type}, driver has {driver_vehicle_type}")
                    print(f"✅ Found {len(unassigned_deliveries)} unassigned deliveries (no ordering)")
                except Exception as e2:
                    print(f"❌ Error querying unassigned deliveries without order_by: {e2}")
                    import traceback
                    traceback.print_exc()
                    unassigned_deliveries = []
            
            # Combine assigned and unassigned
            all_deliveries = assigned_deliveries + unassigned_deliveries
            
            print(f"✅ Found {len(assigned_deliveries)} assigned + {len(unassigned_deliveries)} unassigned = {len(all_deliveries)} total deliveries")
            
            return {
                "deliveries": all_deliveries,
                "total": len(all_deliveries),
                "limit": limit,
                "offset": offset,
                "date_range": {
                    "from": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "to": datetime.utcnow().isoformat()
                },
                "status_filter": ["assigned", "accepted", "picked_up", "in_transit", "requested"],
                "vehicle_type_filter": [],
                "driver_info": {
                    "id": driver_id,
                    "name": "Driver",
                    "vehicle_type": "SEDAN"
                }
            }, 200
        except Exception as e:
            print(f"❌ Error in driver/assigned endpoint: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to load assigned deliveries", "details": str(e)}, 500


@delivery_api.route("/unassigned")
class UnassignedDeliveries(Resource):
    """Get all unassigned deliveries (for admin/dispatcher)"""
    
    def get(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            
            db = get_firestore()
            deliveries_ref = db.collection("deliveries")
            
            # Query for deliveries with status 'requested' or 'pending' and no driver assigned
            query = deliveries_ref.where("status", "in", ["requested", "pending"]).order_by("created_at", direction="DESCENDING").limit(limit + offset)
            
            all_deliveries = []
            for doc in query.stream():
                delivery_data = doc.to_dict()
                if delivery_data and not delivery_data.get("driver_id"):
                    all_deliveries.append(delivery_data)
            
            # Apply offset
            deliveries = all_deliveries[offset:offset + limit]
            
            # Convert to public format
            repo = DeliveryRepository()
            public_deliveries = [repo.to_public_dict(d) for d in deliveries]
            
            print(f"✅ Found {len(public_deliveries)} unassigned deliveries")
            
            return {
                "deliveries": public_deliveries,
                "count": len(public_deliveries),
                "total": len(all_deliveries)
            }, 200
            
        except Exception as e:
            print(f"❌ Error getting unassigned deliveries: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to get unassigned deliveries", "details": str(e)}, 500


@delivery_api.route("/<int:delivery_id>/accept")
class AcceptDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        """Driver accepts a delivery (can be unassigned or already assigned to them)"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        
        if not doc:
            return {"error": "Delivery not found"}, 404
        
        current_status = (doc.get("status") or "").lower()
        current_driver_id = doc.get("driver_id")
        
        # Allow acceptance if:
        # 1. Delivery is unassigned (status=requested/confirmed, driver_id=null)
        # 2. Delivery is already assigned to this driver (status=assigned)
        if current_status in ["requested", "confirmed"] and not current_driver_id:
            # Unassigned delivery - assign to this driver and accept
            print(f"✅ Driver {driver_id} claiming unassigned delivery {delivery_id} (status={current_status})")
            print(f"🔍 Setting driver_id to {driver_id} (type: {type(driver_id)})")
            ok = repo.update_fields(delivery_id, {
                "driver_id": int(driver_id),
                "status": "accepted",
                "assigned_time": datetime.utcnow(),
                "accepted_time": datetime.utcnow()
            })
            if not ok:
                return {"error": "Failed to accept delivery"}, 500
            
            # Verify the update
            updated_doc = repo.get_by_id(delivery_id)
            print(f"✅ Delivery updated: driver_id={updated_doc.get('driver_id')} (type: {type(updated_doc.get('driver_id'))}), status={updated_doc.get('status')}")
            
            return {
                "success": True,
                "message": "Delivery accepted successfully",
                "delivery_id": delivery_id,
                "status": "accepted",
                "next_steps": {
                    "action": "pickup",
                    "pickup_location": doc.get("pickup_address"),
                    "dropoff_location": doc.get("dropoff_address")
                }
            }, 200
            
        elif current_status == "assigned" and int(current_driver_id or 0) == int(driver_id):
            # Already assigned to this driver - just update status to accepted
            print(f"✅ Driver {driver_id} accepting assigned delivery {delivery_id}")
            ok = repo.update_fields(delivery_id, {
                "status": "accepted",
                "accepted_time": datetime.utcnow()
            })
            if not ok:
                return {"error": "Failed to accept delivery"}, 500
            
            return {
                "success": True,
                "message": "Delivery accepted successfully",
                "delivery_id": delivery_id,
                "status": "accepted",
                "next_steps": {
                    "action": "pickup",
                    "pickup_location": doc.get("pickup_address"),
                    "dropoff_location": doc.get("dropoff_address")
                }
            }, 200
            
        elif current_driver_id and int(current_driver_id) != int(driver_id):
            return {"error": "Delivery already assigned to another driver"}, 403
        else:
            return {"error": f"Delivery cannot be accepted (status: {current_status})"}, 400


@delivery_api.route("/<int:delivery_id>/reject")
class RejectDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        """Driver rejects a delivery request"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        
        if not doc:
            return {"error": "Delivery not found"}, 404
        
        current_status = (doc.get("status") or "").lower()
        current_driver_id = doc.get("driver_id")
        
        # Driver can reject if:
        # 1. Delivery is unassigned (status=requested/confirmed)
        # 2. Delivery is assigned to them (status=assigned)
        if current_status in ["requested", "confirmed", "assigned"]:
            if current_driver_id and int(current_driver_id) != int(driver_id):
                return {"error": "Cannot reject delivery assigned to another driver"}, 403
            
            print(f"✅ Driver {driver_id} rejected delivery {delivery_id}")
            
            # Add driver to rejected_by_drivers array
            rejected_by = doc.get("rejected_by_drivers", [])
            if not isinstance(rejected_by, list):
                rejected_by = []
            
            if driver_id not in rejected_by:
                rejected_by.append(driver_id)
                repo.update_fields(delivery_id, {"rejected_by_drivers": rejected_by})
                print(f"📝 Added driver {driver_id} to rejected list. Total rejections: {len(rejected_by)}")
            
            return {
                "success": True,
                "message": "Delivery rejected successfully",
                "delivery_id": delivery_id
            }, 200
        else:
            return {"error": f"Delivery cannot be rejected (status: {current_status})"}, 400


@delivery_api.route("/<int:delivery_id>/pickup")
class PickupDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404
        if int(doc.get("driver_id") or 0) != int(driver_id):
            return {"error": "Access denied"}, 403

        ok = repo.update_fields(delivery_id, {"status": "picked_up", "pickup_time": datetime.utcnow()})
        return ({"message": "Delivery picked up"}, 200) if ok else ({"error": "Failed to update delivery"}, 500)


@delivery_api.route("/<int:delivery_id>/start-transit")
class StartTransit(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404
        if int(doc.get("driver_id") or 0) != int(driver_id):
            return {"error": "Access denied"}, 403

        ok = repo.set_status(delivery_id, "in_transit")
        return ({"message": "Delivery in transit"}, 200) if ok else ({"error": "Failed to update delivery"}, 500)


@delivery_api.route("/<int:delivery_id>/complete")
class CompleteDelivery(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def post(self, delivery_id: int):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        driver_id = g.driver_id
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404
        if int(doc.get("driver_id") or 0) != int(driver_id):
            return {"error": "Access denied"}, 403

        ok = repo.update_fields(delivery_id, {"status": "delivered", "delivered_time": datetime.utcnow()})
        return ({"message": "Delivery completed"}, 200) if ok else ({"error": "Failed to complete delivery"}, 500)


@delivery_api.route("/driver/accepted")
class DriverAcceptedDeliveries(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def get(self):
        """Get driver's accepted/active deliveries (ACCEPTED, PICKED_UP, IN_TRANSIT)"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        try:
            driver_id = g.driver_id
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            
            print(f"📅 Driver {driver_id} requesting accepted deliveries (limit={limit}, offset={offset})")
            
            repo = DeliveryRepository()
            deliveries = repo.list_for_driver(
                driver_id, 
                limit=limit, 
                offset=offset,
                statuses=["accepted", "picked_up", "in_transit"]
            )
            
            print(f"✅ Found {len(deliveries)} accepted deliveries for driver {driver_id}")
            for d in deliveries:
                print(f"   - Delivery {d.get('delivery_id')}: status={d.get('status')}, driver_id={d.get('driver_id')}")
            
            return {
                "deliveries": deliveries, 
                "total": len(deliveries),
                "limit": limit,
                "offset": offset
            }, 200
        except Exception as e:
            print(f"❌ Error in driver/accepted endpoint: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to load accepted deliveries", "details": str(e)}, 500


@delivery_api.route("/driver/history")
class DriverDeliveryHistory(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_driver_required
    def get(self):
        """Get driver's completed delivery history (DELIVERED, CANCELLED)"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        try:
            driver_id = g.driver_id
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
            
            print(f"🚀 Driver {driver_id} requesting delivery history (limit={limit}, offset={offset})")
            
            repo = DeliveryRepository()
            deliveries = repo.list_for_driver(
                driver_id, 
                limit=limit, 
                offset=offset,
                statuses=["delivered", "cancelled"]
            )
            
            print(f"✅ Found {len(deliveries)} history deliveries for driver {driver_id}")
            
            return {
                "deliveries": deliveries, 
                "total": len(deliveries),
                "limit": limit,
                "offset": offset
            }, 200
        except Exception as e:
            print(f"❌ Error in driver/history endpoint: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to load delivery history", "details": str(e)}, 500


@delivery_api.route("/item-photo/upload-url/public")
class ItemPhotoUploadUrl(Resource):
    def post(self):
        """Get signed upload URL for item photo (public endpoint)"""
        if not USE_FIREBASE_DB:
            return {"error": "Firebase storage not available"}, 503
        
        data = request.get_json() or {}
        delivery_id = data.get('delivery_id')
        filename = data.get('filename')
        content_type = data.get('content_type', 'image/jpeg')
        
        if not delivery_id or not filename:
            return {"error": "Missing delivery_id or filename"}, 400
        
        try:
            print(f"📸 Generating upload URL for delivery {delivery_id}, file: {filename}")
            
            # Get storage service (will initialize if needed)
            service = storage_service if storage_service is not None else get_storage_service()
            
            # Use storage service helper method for consistent path
            signed_url, object_key = service.get_item_photo_upload_url(
                delivery_id=delivery_id,
                filename=filename,
                content_type=content_type
            )
            
            if not signed_url:
                return {"error": "Failed to generate upload URL"}, 500
            
            # Get public URL using storage service helper
            public_url = service.get_public_url(object_key)
            
            print(f"✅ Generated upload URL for {object_key}")
            print(f"📸 Public URL: {public_url}")
            print(f"📸 Bucket: {service.bucket_name}")
            
            return {
                "success": True,
                "upload_url": signed_url,
                "object_key": object_key,
                "item_photo_url": public_url,
                "expires_in": 600
            }, 200
        except Exception as e:
            print(f"❌ Error generating upload URL: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}, 500


@delivery_api.route("/<int:delivery_id>/item-photo")
class UpdateItemPhoto(Resource):
    @delivery_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def put(self, delivery_id: int):
        """Update delivery with item photo URL after upload"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        customer_id = g.customer_id
        data = request.get_json() or {}
        item_photo_url = data.get('item_photo_url')
        object_key = data.get('object_key')
        
        if not item_photo_url:
            return {"error": "Missing item_photo_url"}, 400
        
        repo = DeliveryRepository()
        doc = repo.get_by_id(delivery_id)
        if not doc:
            return {"error": "Delivery not found"}, 404
        if int(doc.get("customer_id") or 0) != int(customer_id):
            return {"error": "Access denied"}, 403
        
        # Make the uploaded file public if object_key is provided
        if object_key:
            try:
                print(f"📸 Making blob public: {object_key}")
                service = storage_service if storage_service is not None else get_storage_service()
                service.make_blob_public(object_key)
                print(f"✅ Blob is now public: {object_key}")
            except Exception as e:
                print(f"⚠️ Failed to make blob public: {e}")
                # Don't fail the request if making public fails
        
        # Update the delivery with the photo URL
        ok = repo.update_fields(delivery_id, {"item_photo_url": item_photo_url})
        if not ok:
            return {"error": "Failed to update item photo"}, 500
        
        print(f"✅ Updated delivery {delivery_id} with photo URL: {item_photo_url}")
        return {"success": True, "item_photo_url": item_photo_url}, 200

