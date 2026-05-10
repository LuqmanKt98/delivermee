from __future__ import annotations

from functools import wraps

import firebase_admin.auth
from flask import g, request


def _extract_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        token = header.split(" ", 1)[1].strip()
        return token if token else None
    return None


def _verify_token(token: str) -> dict | None:
    try:
        return firebase_admin.auth.verify_id_token(token)
    except firebase_admin.auth.ExpiredIdTokenError:
        return None
    except firebase_admin.auth.InvalidIdTokenError:
        return None
    except Exception:
        return None


def firebase_token_required(f):
    """Verify Firebase ID token. Sets g.firebase_uid on success."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return {"error": "Missing authorization token"}, 401
        decoded = _verify_token(token)
        if not decoded:
            return {"error": "Invalid or expired token"}, 401
        g.firebase_uid = decoded["uid"]
        g.firebase_claims = decoded
        return f(*args, **kwargs)
    return decorated


def firebase_customer_required(f):
    """Verify Firebase token and look up customer profile.
    Sets g.firebase_uid, g.customer_id, g.customer on success."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return {"error": "Missing authorization token"}, 401
        decoded = _verify_token(token)
        if not decoded:
            return {"error": "Invalid or expired token"}, 401
        g.firebase_uid = decoded["uid"]
        g.firebase_claims = decoded

        from repositories.customer_repository import CustomerRepository
        customer = CustomerRepository().get_by_firebase_uid(g.firebase_uid)
        if not customer:
            return {"error": "Customer profile not found"}, 404
        g.customer_id = customer["id"]
        g.customer = customer
        return f(*args, **kwargs)
    return decorated


def firebase_driver_required(f):
    """Verify Firebase token and look up driver profile.
    Sets g.firebase_uid, g.driver_id, g.driver on success."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return {"error": "Missing authorization token"}, 401
        decoded = _verify_token(token)
        if not decoded:
            return {"error": "Invalid or expired token"}, 401
        g.firebase_uid = decoded["uid"]
        g.firebase_claims = decoded

        from repositories.driver_repository import DriverRepository
        driver = DriverRepository().get_by_firebase_uid(g.firebase_uid)
        if not driver:
            return {"error": "Driver profile not found"}, 404
        g.driver_id = driver["id"]
        g.driver = driver
        return f(*args, **kwargs)
    return decorated
