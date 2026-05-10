from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from services.firestore_client import get_firestore


class PaymentRepository:
    """Firestore-backed payments. Collection: `payments/{paymentId}` where paymentId is a UUID string."""

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("payments")

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow()
        payment_id = data.get("payment_id") or str(uuid.uuid4())

        doc = {
            "payment_id": payment_id,
            "payment_type": data.get("payment_type"),
            "amount": float(data.get("amount") or 0.0),
            "currency": (data.get("currency") or "USD"),
            "status": data.get("status", "pending"),
            "direction": data.get("direction"),
            "payer_id": data.get("payer_id"),
            "payer_type": data.get("payer_type"),
            "payer_stripe_id": data.get("payer_stripe_id"),
            "receiver_id": data.get("receiver_id"),
            "receiver_type": data.get("receiver_type"),
            "receiver_stripe_id": data.get("receiver_stripe_id"),
            "payment_method": data.get("payment_method"),
            "payment_method_id": data.get("payment_method_id"),
            "stripe_payment_intent_id": data.get("stripe_payment_intent_id"),
            "stripe_charge_id": data.get("stripe_charge_id"),
            "stripe_transfer_id": data.get("stripe_transfer_id"),
            "delivery_id": data.get("delivery_id"),
            "driver_id": data.get("driver_id"),
            "base_amount": data.get("base_amount"),
            "platform_fee": data.get("platform_fee"),
            "payment_processing_fee": data.get("payment_processing_fee"),
            "driver_payout": data.get("driver_payout"),
            "tip_amount": data.get("tip_amount"),
            "description": data.get("description"),
            "payment_metadata": data.get("payment_metadata") or {},
            "created_at": now,
            "updated_at": now,
            "completed_at": data.get("completed_at"),
            "error_message": data.get("error_message"),
            "retry_count": int(data.get("retry_count") or 0),
        }

        self._col.document(payment_id).set(doc)
        return self.to_public_dict(doc)

    def get_by_id(self, payment_id: str) -> Optional[dict[str, Any]]:
        snap = self._col.document(payment_id).get()
        if not snap.exists:
            return None
        return snap.to_dict() or None

    def update_fields(self, payment_id: str, fields: dict[str, Any]) -> bool:
        ref = self._col.document(payment_id)
        if not ref.get().exists:
            return False
        payload = dict(fields or {})
        payload["updated_at"] = datetime.utcnow()
        ref.set(payload, merge=True)
        return True

    def mark_completed(self, payment_id: str, *, payment_method_id: Optional[str] = None) -> bool:
        payload: dict[str, Any] = {"status": "completed", "completed_at": datetime.utcnow()}
        if payment_method_id:
            payload["payment_method_id"] = payment_method_id
        return self.update_fields(payment_id, payload)

    def list_for_payer(self, payer_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        q = (
            self._col.where("payer_id", "==", int(payer_id))
            .order_by("created_at", direction="DESCENDING")
            .limit(max(limit + offset, 1))
        )
        docs = [d.to_dict() for d in q.stream()]
        docs = docs[offset : offset + limit]
        return [self.to_public_dict(d) for d in docs]

    def to_public_dict(self, doc: dict[str, Any]) -> dict[str, Any]:
        def _iso(dt):
            return dt.isoformat() if dt else None

        return {
            **{k: v for k, v in doc.items() if k not in {"created_at", "updated_at", "completed_at"}},
            "created_at": _iso(doc.get("created_at")),
            "updated_at": _iso(doc.get("updated_at")),
            "completed_at": _iso(doc.get("completed_at")),
        }

