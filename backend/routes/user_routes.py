import re

import firebase_admin.auth
from flask import g, request
from flask_restx import Namespace, Resource, fields

from repositories.customer_repository import CustomerRepository
from settings import USE_FIREBASE_DB
from utils.firebase_auth_middleware import firebase_customer_required, firebase_token_required

api = Namespace("customers", description="Customer operations")

# ── Swagger models ───────────────────────────────────────────────────────────

customer_model = api.model(
    "Customer",
    {
        "id": fields.Integer(readonly=True),
        "firebase_uid": fields.String(readonly=True),
        "email": fields.String(description="Customer email"),
        "phone_number": fields.String(description="Customer phone number"),
        "first_name": fields.String(description="First name"),
        "last_name": fields.String(description="Last name"),
        "is_active": fields.Boolean(),
        "is_verified": fields.Boolean(),
        "created_at": fields.DateTime(readonly=True),
        "updated_at": fields.DateTime(readonly=True),
    },
)

registration_model = api.model(
    "CustomerRegistration",
    {
        "first_name": fields.String(required=True),
        "last_name": fields.String(required=True),
        "phone_number": fields.String(required=True),
        "address": fields.String(),
        "city": fields.String(),
        "state": fields.String(),
        "zip_code": fields.String(),
    },
)


def _validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?1?\d{9,15}$", phone))


# ── Routes ───────────────────────────────────────────────────────────────────


@api.route("/register")
class CustomerRegistration(Resource):
    @api.expect(registration_model)
    @api.response(201, "Registered", customer_model)
    @api.response(400, "Validation Error")
    @api.response(401, "Invalid Firebase token")
    def post(self):
        """Create customer profile after Firebase Auth sign-up.
        Requires a valid Firebase ID token in the Authorization header."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        # Verify Firebase ID token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return {"error": "Firebase ID token required in Authorization header"}, 401
        id_token = auth_header.split(" ", 1)[1].strip()
        try:
            decoded = firebase_admin.auth.verify_id_token(id_token)
        except Exception:
            return {"error": "Invalid or expired Firebase token"}, 401

        firebase_uid = decoded["uid"]
        email = decoded.get("email", "")
        if not email:
            return {"error": "Firebase account must have an email address"}, 400

        repo = CustomerRepository()

        # Idempotent — return existing profile if already registered
        existing = repo.get_by_firebase_uid(firebase_uid)
        if existing:
            return {"message": "Profile already exists", "customer": repo.to_public_dict(existing)}, 200

        data = api.payload or {}

        required = ["first_name", "last_name", "phone_number"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        if not _validate_phone(data["phone_number"]):
            return {"error": "Invalid phone number format"}, 400

        if repo.exists_by_field("email", email):
            return {"error": "Email already registered"}, 400
        if repo.exists_by_field("phone_number", data["phone_number"]):
            return {"error": "Phone number already registered"}, 400

        try:
            customer_data = repo.create_customer(
                {
                    "firebase_uid": firebase_uid,
                    "email": email,
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone_number": data["phone_number"],
                    "address": data.get("address"),
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "zip_code": data.get("zip_code"),
                }
            )
            # Tag the Firebase Auth user with role so tokens carry the claim
            try:
                firebase_admin.auth.set_custom_user_claims(firebase_uid, {"role": "customer"})
            except Exception:
                pass  # Non-fatal — claim will be set on next token refresh

            return {"message": "Registration successful", "customer": customer_data}, 201
        except Exception as e:
            print(f"❌ Error in customer registration: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Registration failed", "details": str(e)}, 500


@api.route("/profile")
class CustomerProfile(Resource):
    @api.doc(security="Bearer Auth")
    @api.response(200, "Success", customer_model)
    @api.response(401, "Unauthorized")
    @api.response(404, "Not found")
    @firebase_customer_required
    def get(self):
        """Get the authenticated customer's profile."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503
        return CustomerRepository().to_public_dict(g.customer), 200

    @api.doc(security="Bearer Auth")
    @api.response(200, "Updated")
    @api.response(401, "Unauthorized")
    @firebase_customer_required
    def put(self):
        """Update the authenticated customer's profile."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        data = api.payload or {}
        update: dict = {}

        for field in ("first_name", "last_name", "address", "city", "state", "zip_code"):
            if field in data:
                update[field] = data[field]

        if "phone_number" in data:
            if not _validate_phone(data["phone_number"]):
                return {"error": "Invalid phone number format"}, 400
            existing = CustomerRepository().get_by_phone(data["phone_number"])
            if existing and existing.get("id") != g.customer_id:
                return {"error": "Phone number already in use"}, 400
            update["phone_number"] = data["phone_number"]

        # Handle password update
        if "password" in data and data["password"]:
            new_password = data["password"].strip()
            if len(new_password) < 6:
                return {"error": "Password must be at least 6 characters"}, 400

            try:
                # Update password in Firebase Auth using admin SDK
                firebase_admin.auth.update_user(
                    g.firebase_uid,
                    password=new_password
                )
                print(f"✅ Password updated for customer: {g.firebase_uid}")
            except Exception as e:
                print(f"❌ Error updating password for customer {g.firebase_uid}: {str(e)}")
                return {"error": "Failed to update password", "details": str(e)}, 500

        if not update and "password" not in data:
            return {"error": "No fields to update"}, 400

        try:
            if update:  # Only update Firestore fields if there are any
                CustomerRepository().update_fields(g.customer_id, update)
            updated = CustomerRepository().get_by_id(g.customer_id)
            return {
                "message": "Profile updated successfully",
                "customer": CustomerRepository().to_public_dict(updated),
            }, 200
        except Exception as e:
            return {"error": "Failed to update profile", "details": str(e)}, 500


@api.route("/me")
class CustomerMe(Resource):
    """Alias for /profile — called right after Firebase sign-in to hydrate local state."""

    @api.doc(security="Bearer Auth")
    @api.response(200, "Success", customer_model)
    @api.response(401, "Unauthorized")
    @api.response(404, "Not found")
    @firebase_customer_required
    def get(self):
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503
        repo = CustomerRepository()
        repo.update_last_login(g.customer_id)
        return repo.to_public_dict(g.customer), 200


@api.route("/reset-password")
class ResetPassword(Resource):
    """Reset customer password after phone OTP verification."""

    @api.response(200, "Password reset successfully")
    @api.response(400, "Invalid request")
    @api.response(401, "Unauthorized")
    @firebase_token_required
    def post(self):
        """Reset password for user (verified via phone OTP)."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        data = api.payload or {}
        new_password = data.get("new_password", "").strip()
        email = data.get("email", "").strip()

        if not new_password or len(new_password) < 6:
            return {"error": "Password must be at least 6 characters"}, 400

        if not email:
            return {"error": "Email address is required"}, 400

        try:
            print(f"🔐 Attempting password reset for: {email}")

            # Get user by email from Firebase Auth
            user = firebase_admin.auth.get_user_by_email(email)
            print(f"✅ Found user: {user.uid} for email: {email}")

            # Update Firebase Auth password using admin SDK
            firebase_admin.auth.update_user(
                user.uid,
                password=new_password
            )
            print(f"✅ Password reset successful for user: {user.uid} ({email})")
            return {"message": "Password reset successfully"}, 200
        except firebase_admin.auth.UserNotFoundError:
            print(f"❌ User not found for email: {email}")
            return {"error": "User not found with that email"}, 404
        except Exception as e:
            print(f"❌ Error resetting password for {email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to reset password", "details": str(e)}, 500
