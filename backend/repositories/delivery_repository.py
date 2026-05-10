from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from repositories.firestore_counters import next_int_id
from services.firestore_client import get_firestore


class DeliveryRepository:
    """
    Firestore-backed delivery repository.

    Collection: `deliveries/{deliveryId}`
    - `deliveryId` is a stringified int to preserve existing URL patterns.
    """

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("deliveries")

    def _doc_ref(self, delivery_id: Union[int, str]):
        return self._col.document(str(delivery_id))

    def create(self, *, customer_id: int, data: dict[str, Any]) -> dict[str, Any]:
        delivery_id = next_int_id("deliveries")
        now = datetime.utcnow()
        tracking_number = data.get("tracking_number") or f"DM{delivery_id:08d}"

        doc: dict[str, Any] = {
            "id": delivery_id,
            "tracking_number": tracking_number,
            "customer_id": int(customer_id),
            "driver_id": data.get("driver_id"),
            "pickup_address": data.get("pickup_address"),
            "dropoff_address": data.get("dropoff_address"),
            "pickup_latitude": data.get("pickup_latitude"),
            "pickup_longitude": data.get("pickup_longitude"),
            "dropoff_latitude": data.get("dropoff_latitude"),
            "dropoff_longitude": data.get("dropoff_longitude"),
            "item_name": data.get("item_name"),
            "item_description": data.get("item_description"),
            "item_photo_url": data.get("item_photo_url"),
            "vehicle_type": data.get("vehicle_type"),
            "package_size": data.get("package_size"),
            "package_type": data.get("package_type"),
            "width": data.get("width"),
            "height": data.get("height"),
            "length": data.get("length"),
            "weight": data.get("weight"),
            "item_count": data.get("item_count", 1),
            "estimated_distance_km": data.get("estimated_distance_km"),
            "actual_distance_km": data.get("actual_distance_km"),
            "is_fragile": bool(data.get("is_fragile", False)),
            "is_perishable": bool(data.get("is_perishable", False)),
            "requires_signature": bool(data.get("requires_signature", False)),
            "special_instructions": data.get("special_instructions"),
            "delivery_type": data.get("delivery_type", "standard"),
            "schedule_type": data.get("schedule_type", "immediate"),
            "scheduled_date": data.get("scheduled_date"),
            "time_slot": data.get("time_slot"),
            "delivery_preference": data.get("delivery_preference", "attended"),
            "status": data.get("status", "requested"),
            "estimated_cost": data.get("estimated_cost"),
            "actual_cost": data.get("actual_cost"),
            "insurance_amount": data.get("insurance_amount"),
            "estimated_duration": data.get("estimated_duration"),
            "actual_duration": data.get("actual_duration"),
            "payment_status": data.get("payment_status", "pending"),
            "payment_completed_at": data.get("payment_completed_at"),
            "created_at": now,
            "updated_at": now,
            # optional timestamps used by existing APIs
            "assigned_time": data.get("assigned_time"),
            "accepted_time": data.get("accepted_time"),
            "pickup_time": data.get("pickup_time"),
            "delivered_time": data.get("delivered_time"),
            "cancelled_time": data.get("cancelled_time"),
        }

        self._doc_ref(delivery_id).set(doc)
        return self.to_public_dict(doc)

    def get_by_id(self, delivery_id: Union[int, str]) -> Optional[dict[str, Any]]:
        snap = self._doc_ref(delivery_id).get()
        if not snap.exists:
            return None
        return snap.to_dict() or None

    def get_by_tracking_number(self, tracking_number: str) -> Optional[dict[str, Any]]:
        docs = self._col.where("tracking_number", "==", tracking_number).limit(1).stream()
        for d in docs:
            return d.to_dict()
        return None

    def list_for_customer(self, customer_id: Union[int, str], limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        q = (
            self._col.where("customer_id", "==", int(customer_id))
            .order_by("created_at", direction="DESCENDING")
            .limit(max(limit + offset, 1))
        )
        docs = [d.to_dict() for d in q.stream()]
        docs = docs[offset : offset + limit]
        return [self.to_public_dict(d) for d in docs]

    def list_for_driver(self, driver_id: Union[int, str], limit: int = 50, offset: int = 0, statuses: Optional[list[str]] = None) -> list[dict[str, Any]]:
        print(f"🔍 Querying deliveries for driver {driver_id} with statuses: {statuses}")
        print(f"🔍 Driver ID type: {type(driver_id)}, value: {driver_id}")
        
        q = self._col.where("driver_id", "==", int(driver_id)).order_by("created_at", direction="DESCENDING").limit(200)
        
        all_docs = [d.to_dict() for d in q.stream()]
        print(f"📦 Retrieved {len(all_docs)} total deliveries for driver {driver_id}")
        
        # Log each delivery for debugging
        for doc in all_docs:
            print(f"   - Delivery {doc.get('id')}: status='{doc.get('status')}', driver_id={doc.get('driver_id')} (type: {type(doc.get('driver_id'))})")
        
        if statuses:
            docs = [d for d in all_docs if d.get("status") in statuses]
            print(f"🔍 After status filtering ({statuses}): {len(docs)} deliveries")
            for doc in docs:
                print(f"   - Matched: Delivery {doc.get('id')}: status='{doc.get('status')}'")
        else:
            docs = all_docs
        
        docs = docs[offset : offset + limit]
        print(f"📊 Returning {len(docs)} deliveries after pagination (offset={offset}, limit={limit})")
        
        return [self.to_public_dict(d) for d in docs]

    def update_fields(self, delivery_id: Union[int, str], fields: dict[str, Any]) -> bool:
        ref = self._doc_ref(delivery_id)
        if not ref.get().exists:
            return False
        fields = dict(fields or {})
        fields["updated_at"] = datetime.utcnow()
        ref.set(fields, merge=True)
        return True

    def set_status(self, delivery_id: Union[int, str], status: str, *, timestamp_field: Optional[str] = None) -> bool:
        payload: dict[str, Any] = {"status": status}
        if timestamp_field:
            payload[timestamp_field] = datetime.utcnow()
        return self.update_fields(delivery_id, payload)

    def mark_payment_completed(self, delivery_id: Union[int, str], actual_cost: Optional[float] = None) -> bool:
        payload: dict[str, Any] = {"payment_status": "completed", "payment_completed_at": datetime.utcnow()}
        if actual_cost is not None:
            payload["actual_cost"] = float(actual_cost)
        return self.update_fields(delivery_id, payload)

    def to_public_dict(self, doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        # Fetch customer data if customer_id exists
        customer_data = None
        customer_id = doc.get("customer_id")
        if customer_id:
            try:
                customer_ref = self._db.collection("customers").document(str(customer_id))
                customer_snap = customer_ref.get()
                if customer_snap.exists:
                    customer_data = customer_snap.to_dict()
            except Exception as e:
                print(f"⚠️ Error fetching customer {customer_id}: {e}")

        # Fetch driver data if driver_id exists
        driver_data = None
        driver_id = doc.get("driver_id")
        if driver_id:
            try:
                driver_ref = self._db.collection("drivers").document(str(driver_id))
                driver_snap = driver_ref.get()
                if driver_snap.exists:
                    driver_data = driver_snap.to_dict()
            except Exception as e:
                print(f"⚠️ Error fetching driver {driver_id}: {e}")

        # Keep keys close to the SQLAlchemy model's `to_dict()` output.
        result = {
            **{k: v for k, v in doc.items() if k not in {"created_at", "updated_at", "assigned_time", "accepted_time", "pickup_time", "delivered_time", "cancelled_time", "payment_completed_at"}},
            "created_at": _iso(doc.get("created_at")),
            "updated_at": _iso(doc.get("updated_at")),
            "assigned_time": _iso(doc.get("assigned_time")),
            "accepted_time": _iso(doc.get("accepted_time")),
            "pickup_time": _iso(doc.get("pickup_time")),
            "delivered_time": _iso(doc.get("delivered_time")),
            "cancelled_time": _iso(doc.get("cancelled_time")),
            "payment_completed_at": _iso(doc.get("payment_completed_at")),
        }
        
        # Add customer data if available
        if customer_data:
            result["customer"] = {
                "id": customer_data.get("id"),
                "first_name": customer_data.get("first_name", ""),
                "last_name": customer_data.get("last_name", ""),
                "email": customer_data.get("email"),
                "phone": customer_data.get("phone_number"),
            }
        
        # Add driver data if available
        if driver_data:
            result["driver"] = {
                "id": driver_data.get("id"),
                "first_name": driver_data.get("first_name", ""),
                "last_name": driver_data.get("last_name", ""),
                "email": driver_data.get("email"),
                "phone": driver_data.get("phone_number"),
                "rating": driver_data.get("rating", 5.0),
                "vehicle_type": driver_data.get("vehicle_type"),
                "vehicle_make": driver_data.get("vehicle_make"),
                "vehicle_model": driver_data.get("vehicle_model"),
                "vehicle_plate_number": driver_data.get("vehicle_plate_number"),
            }
        
        return result

