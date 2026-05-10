from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from repositories.firestore_counters import next_int_id
from services.firestore_client import get_firestore


class CustomerRepository:
    """
    Firestore-backed customer repository.
    Auth is handled by Firebase Auth — no passwords stored here.
    Each customer document carries a firebase_uid field that links it to a Firebase Auth user.
    """

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("customers")

    def _doc_ref(self, customer_id: Union[int, str]):
        return self._col.document(str(customer_id))

    def get_by_id(self, customer_id: Union[int, str]) -> Optional[dict[str, Any]]:
        snap = self._doc_ref(customer_id).get()
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

    def create_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        customer_id = next_int_id("customers")
        now = datetime.utcnow()

        doc = {
            "id": customer_id,
            "firebase_uid": data["firebase_uid"],
            "email": data["email"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "phone_number": data.get("phone_number"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip_code": data.get("zip_code"),
            "country": data.get("country", "USA"),
            "is_active": bool(data.get("is_active", True)),
            "is_verified": bool(data.get("is_verified", False)),
            "email_verified_at": data.get("email_verified_at"),
            "phone_verified_at": data.get("phone_verified_at"),
            "notification_preferences": data.get(
                "notification_preferences",
                {
                    "email_notifications": True,
                    "sms_notifications": True,
                    "push_notifications": True,
                    "marketing_emails": False,
                },
            ),
            "stripe_customer_id": data.get("stripe_customer_id"),
            "created_at": now,
            "updated_at": now,
            "last_login_at": data.get("last_login_at"),
            "current_latitude": data.get("current_latitude"),
            "current_longitude": data.get("current_longitude"),
            "last_location_update": data.get("last_location_update"),
        }

        self._doc_ref(customer_id).set(doc)
        return self.to_public_dict(doc)

    def update_last_login(self, customer_id: Union[int, str]) -> None:
        now = datetime.utcnow()
        self._doc_ref(customer_id).set({"last_login_at": now, "updated_at": now}, merge=True)

    def update_location(
        self,
        customer_id: Union[int, str],
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
    ) -> bool:
        ref = self._doc_ref(customer_id)
        if not ref.get().exists:
            return False
        now = datetime.utcnow()
        payload: dict[str, Any] = {
            "current_latitude": latitude,
            "current_longitude": longitude,
            "last_location_update": now,
            "updated_at": now,
        }
        if accuracy is not None:
            payload["location_accuracy"] = float(accuracy)
        ref.set(payload, merge=True)
        return True

    def update_fields(self, customer_id: Union[int, str], fields: dict[str, Any]) -> bool:
        ref = self._doc_ref(customer_id)
        if not ref.get().exists:
            return False
        fields["updated_at"] = datetime.utcnow()
        ref.set(fields, merge=True)
        return True

    def to_public_dict(self, customer_doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        return {
            "id": customer_doc.get("id"),
            "firebase_uid": customer_doc.get("firebase_uid"),
            "email": customer_doc.get("email"),
            "first_name": customer_doc.get("first_name"),
            "last_name": customer_doc.get("last_name"),
            "phone_number": customer_doc.get("phone_number"),
            "address": customer_doc.get("address"),
            "city": customer_doc.get("city"),
            "state": customer_doc.get("state"),
            "zip_code": customer_doc.get("zip_code"),
            "country": customer_doc.get("country", "USA"),
            "is_active": customer_doc.get("is_active", True),
            "is_verified": customer_doc.get("is_verified", False),
            "email_verified_at": _iso(customer_doc.get("email_verified_at")),
            "phone_verified_at": _iso(customer_doc.get("phone_verified_at")),
            "notification_preferences": customer_doc.get("notification_preferences"),
            "stripe_customer_id": customer_doc.get("stripe_customer_id"),
            "created_at": _iso(customer_doc.get("created_at")),
            "updated_at": _iso(customer_doc.get("updated_at")),
            "last_login_at": _iso(customer_doc.get("last_login_at")),
            "current_latitude": customer_doc.get("current_latitude"),
            "current_longitude": customer_doc.get("current_longitude"),
            "last_location_update": _iso(customer_doc.get("last_location_update")),
        }
