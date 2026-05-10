from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from services.firestore_client import get_firestore


class NotificationRepository:
    """Firestore-backed notifications. Collection: `notifications/{notificationId}`"""

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("notifications")

    def list_for_driver(self, driver_id: Union[int, str], limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        # Firestore offsets are inefficient; this is acceptable for small pagination.
        q = (
            self._col.where("driver_id", "==", int(driver_id))
            .order_by("created_at", direction="DESCENDING")
            .limit(max(limit + offset, 1))
        )
        docs = [d.to_dict() for d in q.stream()]
        docs = docs[offset : offset + limit]
        return [self.to_public_dict(d) for d in docs]

    def get_for_driver(self, notification_id: Union[int, str], driver_id: Union[int, str]) -> Optional[dict[str, Any]]:
        snap = self._col.document(str(notification_id)).get()
        if not snap.exists:
            return None
        doc = snap.to_dict() or {}
        if int(doc.get("driver_id") or 0) != int(driver_id):
            return None
        return doc

    def mark_read(self, notification_id: Union[int, str]) -> bool:
        ref = self._col.document(str(notification_id))
        if not ref.get().exists:
            return False
        ref.set({"status": "read", "read_at": datetime.utcnow(), "updated_at": datetime.utcnow()}, merge=True)
        return True

    def to_public_dict(self, doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        return {
            "id": doc.get("id") or doc.get("notification_id"),
            "driver_id": doc.get("driver_id"),
            "ride_id": doc.get("ride_id"),
            "delivery_id": doc.get("delivery_id"),
            "type": doc.get("type"),
            "title": doc.get("title"),
            "message": doc.get("message"),
            "status": doc.get("status"),
            "sent_at": _iso(doc.get("sent_at")),
            "read_at": _iso(doc.get("read_at")),
            "delivery_attempts": doc.get("delivery_attempts"),
            "response_required": doc.get("response_required"),
            "response_deadline": _iso(doc.get("response_deadline")),
            "response_received": doc.get("response_received"),
            "response_action": doc.get("response_action"),
            "created_at": _iso(doc.get("created_at")),
            "updated_at": _iso(doc.get("updated_at")),
        }

