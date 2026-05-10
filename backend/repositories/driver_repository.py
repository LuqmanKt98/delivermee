from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from models.user import DriverStatus
from repositories.firestore_counters import next_int_id
from services.firestore_client import get_firestore


class DriverRepository:
    """
    Firestore-backed driver repository.
    Auth is handled by Firebase Auth — no passwords stored here.
    Each driver document carries a firebase_uid field linking to a Firebase Auth user.
    """

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("drivers")

    def _doc_ref(self, driver_id: Union[int, str]):
        return self._col.document(str(driver_id))

    def get_by_id(self, driver_id: Union[int, str]) -> Optional[dict[str, Any]]:
        snap = self._doc_ref(driver_id).get()
        return snap.to_dict() if snap.exists else None

    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[dict[str, Any]]:
        docs = self._col.where("firebase_uid", "==", firebase_uid).limit(1).stream()
        for d in docs:
            return d.to_dict()
        return None

    def get_by_email(self, email: str) -> Optional[dict[str, Any]]:
        docs = self._col.where("email", "==", email).limit(1).stream()
        for d in docs:
            return d.to_dict()
        return None

    def get_by_phone(self, phone_number: str) -> Optional[dict[str, Any]]:
        docs = self._col.where("phone_number", "==", phone_number).limit(1).stream()
        for d in docs:
            return d.to_dict()
        return None

    def exists_by_field(self, field: str, value: Any) -> bool:
        docs = self._col.where(field, "==", value).limit(1).stream()
        return any(True for _ in docs)

    def create_driver(self, data: dict[str, Any]) -> dict[str, Any]:
        driver_id = next_int_id("drivers")
        now = datetime.utcnow()

        doc = {
            "id": driver_id,
            "firebase_uid": data["firebase_uid"],
            "email": data["email"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "phone_number": data["phone_number"],
            "license_number": data["license_number"],
            "vehicle_type": data["vehicle_type"],
            "vehicle_make": data.get("vehicle_make"),
            "vehicle_model": data.get("vehicle_model"),
            "vehicle_year": data.get("vehicle_year"),
            "vehicle_plate_number": data.get("vehicle_plate_number"),
            "driving_license_image": data.get("driving_license_image"),
            "id_card_image": data.get("id_card_image"),
            "insurance_image": data.get("insurance_image"),
            "is_active": bool(data.get("is_active", True)),
            "is_verified": bool(data.get("is_verified", False)),
            "is_available": bool(data.get("is_available", True)),
            "verification_status": data.get("verification_status", "pending"),
            "status": data.get("status", DriverStatus.AVAILABLE.value),
            "intelligent_mode_enabled": bool(data.get("intelligent_mode_enabled", False)),
            "stripe_account_id": data.get("stripe_account_id"),
            "rating": float(data.get("rating", 5.0) or 5.0),
            "total_deliveries": int(data.get("total_deliveries", 0) or 0),
            "completed_deliveries": int(data.get("completed_deliveries", 0) or 0),
            "cancelled_deliveries": int(data.get("cancelled_deliveries", 0) or 0),
            "current_latitude": data.get("current_latitude"),
            "current_longitude": data.get("current_longitude"),
            "last_location_update": data.get("last_location_update"),
            "created_at": now,
            "updated_at": now,
            "last_active_at": data.get("last_active_at"),
            "push_token": data.get("push_token"),
            "device_id": data.get("device_id"),
            "has_payment_method": bool(data.get("has_payment_method", False)),
        }

        self._doc_ref(driver_id).set(doc)
        return self.to_public_dict(doc)

    def update_location(self, driver_id: Union[int, str], latitude: float, longitude: float) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        now = datetime.utcnow()
        ref.set(
            {"current_latitude": latitude, "current_longitude": longitude, "last_location_update": now, "updated_at": now},
            merge=True,
        )
        return True

    def update_push_token(self, driver_id: Union[int, str], push_token: str, device_id: Optional[str] = None) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        now = datetime.utcnow()
        payload: dict[str, Any] = {"push_token": push_token, "updated_at": now}
        if device_id is not None:
            payload["device_id"] = device_id
        ref.set(payload, merge=True)
        return True

    def set_status(self, driver_id: Union[int, str], status_value: str, is_available: Optional[bool] = None) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        now = datetime.utcnow()
        payload: dict[str, Any] = {"status": status_value, "updated_at": now}
        if is_available is not None:
            payload["is_available"] = is_available
            if is_available:
                payload["last_active_at"] = now
        ref.set(payload, merge=True)
        return True

    def set_availability(self, driver_id: Union[int, str], is_available: bool) -> bool:
        return self.set_status(
            driver_id,
            status_value=DriverStatus.AVAILABLE.value if is_available else DriverStatus.OFFLINE.value,
            is_available=is_available,
        )

    def set_has_payment_method(self, driver_id: Union[int, str], has_payment_method: bool) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        ref.set({"has_payment_method": bool(has_payment_method), "updated_at": datetime.utcnow()}, merge=True)
        return True

    def update_document_key(self, driver_id: Union[int, str], doc_type: str, object_key: str) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        field_map = {"driver_license": "driving_license_image", "id_card": "id_card_image", "insurance": "insurance_image"}
        if doc_type not in field_map:
            return False
        ref.set({field_map[doc_type]: object_key, "updated_at": datetime.utcnow()}, merge=True)
        return True

    def update_fields(self, driver_id: Union[int, str], fields: dict[str, Any]) -> bool:
        ref = self._doc_ref(driver_id)
        if not ref.get().exists:
            return False
        fields["updated_at"] = datetime.utcnow()
        ref.set(fields, merge=True)
        return True

    def to_public_dict(self, driver_doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        return {
            "id": driver_doc.get("id"),
            "firebase_uid": driver_doc.get("firebase_uid"),
            "email": driver_doc.get("email"),
            "first_name": driver_doc.get("first_name"),
            "last_name": driver_doc.get("last_name"),
            "phone_number": driver_doc.get("phone_number"),
            "license_number": driver_doc.get("license_number"),
            "vehicle_type": driver_doc.get("vehicle_type"),
            "vehicle_make": driver_doc.get("vehicle_make"),
            "vehicle_model": driver_doc.get("vehicle_model"),
            "vehicle_year": driver_doc.get("vehicle_year"),
            "vehicle_plate_number": driver_doc.get("vehicle_plate_number"),
            "driving_license_image": driver_doc.get("driving_license_image"),
            "id_card_image": driver_doc.get("id_card_image"),
            "insurance_image": driver_doc.get("insurance_image"),
            "is_active": driver_doc.get("is_active", True),
            "is_verified": driver_doc.get("is_verified", False),
            "is_available": driver_doc.get("is_available", True),
            "verification_status": driver_doc.get("verification_status", "pending"),
            "status": driver_doc.get("status", DriverStatus.AVAILABLE.value),
            "intelligent_mode_enabled": driver_doc.get("intelligent_mode_enabled", False),
            "stripe_account_id": driver_doc.get("stripe_account_id"),
            "rating": float(driver_doc.get("rating") or 5.0),
            "total_deliveries": int(driver_doc.get("total_deliveries") or 0),
            "completed_deliveries": int(driver_doc.get("completed_deliveries") or 0),
            "cancelled_deliveries": int(driver_doc.get("cancelled_deliveries") or 0),
            "current_latitude": driver_doc.get("current_latitude"),
            "current_longitude": driver_doc.get("current_longitude"),
            "last_location_update": _iso(driver_doc.get("last_location_update")),
            "created_at": _iso(driver_doc.get("created_at")),
            "updated_at": _iso(driver_doc.get("updated_at")),
            "last_active_at": _iso(driver_doc.get("last_active_at")),
            "push_token": driver_doc.get("push_token"),
            "device_id": driver_doc.get("device_id"),
            "has_payment_method": driver_doc.get("has_payment_method", False),
        }
