from datetime import datetime

from google.cloud import firestore as gcf_firestore

from services.firestore_client import get_firestore


def next_int_id(counter_name: str) -> int:
    """
    Generate a monotonically increasing integer id using a Firestore transaction.

    Stores counters in: `counters/{counter_name}` with field `value`.
    """
    db = get_firestore()
    counter_ref = db.collection("counters").document(counter_name)

    @gcf_firestore.transactional
    def _tx(transaction):
        snap = counter_ref.get(transaction=transaction)
        current = 0
        if snap.exists:
            data = snap.to_dict() or {}
            current = int(data.get("value", 0) or 0)

        new_value = current + 1
        transaction.set(
            counter_ref,
            {"value": new_value, "updated_at": datetime.utcnow()},
            merge=True,
        )
        return new_value

    transaction = db.transaction()
    return _tx(transaction)

