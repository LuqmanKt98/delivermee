from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from services.firestore_client import get_firestore


class VerificationCodeRepository:
    """
    Firestore-backed verification codes.

    Collection: `verification_codes/{codeId}`
    """

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("verification_codes")

    def create(
        self,
        *,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        verification_type: str = "phone",
        user_type: str = "customer",
        ttl_minutes: int = 10,
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=int(ttl_minutes))

        code = f"{secrets.randbelow(1_000_000):06d}"
        doc = {
            "code": code,
            "email": email,
            "phone_number": phone_number,
            "verification_type": verification_type,
            "user_type": user_type,
            "is_used": False,
            "created_at": now,
            "expires_at": expires_at,
        }

        ref = self._col.document()
        ref.set(doc)
        doc["id"] = ref.id
        return doc

    def get_latest_unused(
        self,
        *,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        verification_type: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        q = self._col.where("is_used", "==", False)

        if user_type:
            q = q.where("user_type", "==", user_type)
        if verification_type:
            q = q.where("verification_type", "==", verification_type)

        if email:
            q = q.where("email", "==", email)
        elif phone_number:
            q = q.where("phone_number", "==", phone_number)
        else:
            return None

        q = q.order_by("created_at", direction="DESCENDING").limit(1)
        for d in q.stream():
            doc = d.to_dict() or {}
            doc["id"] = d.id
            return doc
        return None

    def mark_used(self, code_id: str) -> None:
        self._col.document(code_id).set({"is_used": True, "used_at": datetime.utcnow()}, merge=True)

