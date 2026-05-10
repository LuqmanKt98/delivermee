from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from services.firestore_client import get_firestore


class RideRepository:
    """Firestore-backed rides repository. Collection: `rides/{rideId}`"""

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("rides")

    def _doc_ref(self, ride_id: Union[int, str]):
        return self._col.document(str(ride_id))

    def get_by_id(self, ride_id: Union[int, str]) -> Optional[dict[str, Any]]:
        snap = self._doc_ref(ride_id).get()
        if not snap.exists:
            return None
        return snap.to_dict() or None

    def update_for_assignment(self, ride_id: Union[int, str], driver_id: Union[int, str], status: str) -> bool:
        ref = self._doc_ref(ride_id)
        if not ref.get().exists:
            return False
        now = datetime.utcnow()
        ref.set(
            {
                "driver_id": int(driver_id),
                "status": status,
                "assigned_time": now,
                "updated_at": now,
            },
            merge=True,
        )
        return True

    def accept(self, ride_id: Union[int, str], driver_id: Union[int, str]) -> bool:
        ref = self._doc_ref(ride_id)
        snap = ref.get()
        if not snap.exists:
            return False
        ride = snap.to_dict() or {}
        if int(ride.get("driver_id") or 0) != int(driver_id):
            return False
        if ride.get("status") != "assigned":
            return False
        now = datetime.utcnow()
        ref.set({"status": "accepted", "accepted_time": now, "updated_at": now}, merge=True)
        return True

    def reject(self, ride_id: Union[int, str], driver_id: Union[int, str]) -> bool:
        ref = self._doc_ref(ride_id)
        snap = ref.get()
        if not snap.exists:
            return False
        ride = snap.to_dict() or {}
        if int(ride.get("driver_id") or 0) != int(driver_id):
            return False
        if ride.get("status") != "assigned":
            return False
        now = datetime.utcnow()
        ref.set(
            {
                "status": "requested",
                "driver_id": None,
                "assigned_time": None,
                "updated_at": now,
            },
            merge=True,
        )
        return True

    def to_public_dict(self, ride_doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        return {
            "id": ride_doc.get("id"),
            "customer_id": ride_doc.get("customer_id"),
            "driver_id": ride_doc.get("driver_id"),
            "pickup_address": ride_doc.get("pickup_address"),
            "dropoff_address": ride_doc.get("dropoff_address"),
            "pickup_latitude": ride_doc.get("pickup_latitude"),
            "pickup_longitude": ride_doc.get("pickup_longitude"),
            "dropoff_latitude": ride_doc.get("dropoff_latitude"),
            "dropoff_longitude": ride_doc.get("dropoff_longitude"),
            "ride_type": ride_doc.get("ride_type"),
            "scheduled_time": _iso(ride_doc.get("scheduled_time")),
            "requested_time": _iso(ride_doc.get("requested_time")),
            "status": ride_doc.get("status"),
            "estimated_duration": ride_doc.get("estimated_duration"),
            "estimated_distance": ride_doc.get("estimated_distance"),
            "estimated_cost": ride_doc.get("estimated_cost"),
            "assigned_time": _iso(ride_doc.get("assigned_time")),
            "accepted_time": _iso(ride_doc.get("accepted_time")),
            "pickup_time": _iso(ride_doc.get("pickup_time")),
            "completed_time": _iso(ride_doc.get("completed_time")),
            "vehicle_type": ride_doc.get("vehicle_type"),
            "special_instructions": ride_doc.get("special_instructions"),
            "created_at": _iso(ride_doc.get("created_at")),
            "updated_at": _iso(ride_doc.get("updated_at")),
        }

