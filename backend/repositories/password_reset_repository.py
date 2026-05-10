from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from services.firestore_client import get_firestore


class PasswordResetRepository:
    """Firestore-backed password reset tokens. Collection: `password_reset_tokens/{token}`"""

    def __init__(self):
        self._db = get_firestore()
        self._col = self._db.collection("password_reset_tokens")

    def create(self, email: str, user_type: str, token: str) -> dict[str, Any]:
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=1)
        doc = {
            "token": token,
            "email": email,
            "user_type": user_type,
            "is_used": False,
            "created_at": now,
            "expires_at": expires_at,
        }
        self._col.document(token).set(doc)
        return doc

    def get(self, token: str) -> Optional[dict[str, Any]]:
        snap = self._col.document(token).get()
        if not snap.exists:
            return None
        return snap.to_dict() or None

    def mark_used(self, token: str) -> None:
        self._col.document(token).set({"is_used": True, "used_at": datetime.utcnow()}, merge=True)

