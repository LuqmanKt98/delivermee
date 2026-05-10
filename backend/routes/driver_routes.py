import re
from datetime import datetime

import firebase_admin.auth
from flask import g, request
from flask_restx import Namespace, Resource, fields

from models.user import DriverStatus
from models.ride import RideStatus
from repositories.driver_repository import DriverRepository
from repositories.ride_repository import RideRepository
from services.notification_service import notification_service
from services.storage_service import get_storage_service
from settings import USE_FIREBASE_DB
from utils.firebase_auth_middleware import firebase_driver_required

# ORM_DISABLED: PostgreSQL/SQLAlchemy imports kept commented for reference
# from models.user import Driver
# from models.ride import Ride
# from models.notification import Notification
# from extensions import db, api

driver_api = Namespace("drivers", description="Driver operations")

# ── Swagger models ────────────────────────────────────────────────────────────

driver_model = driver_api.model(
    "Driver",
    {
        "id": fields.Integer(readonly=True),
        "firebase_uid": fields.String(readonly=True),
        "email": fields.String(description="Driver email"),
        "phone_number": fields.String(description="Driver phone number"),
        "first_name": fields.String(description="Driver first name"),
        "last_name": fields.String(description="Driver last name"),
        "license_number": fields.String(description="Driver license number"),
        "driving_license_image": fields.String(description="Object key for driving license image"),
        "id_card_image": fields.String(description="Object key for ID card image"),
        "vehicle_type": fields.String(description="Vehicle type"),
        "vehicle_make": fields.String(description="Vehicle make"),
        "vehicle_model": fields.String(description="Vehicle model"),
        "vehicle_year": fields.Integer(description="Vehicle year"),
        "vehicle_plate_number": fields.String(description="Vehicle plate number"),
        "is_available": fields.Boolean(description="Driver availability status"),
        "has_payment_method": fields.Boolean(description="Payment method added status"),
        "status": fields.String(enum=["available", "busy", "offline"], description="Driver status"),
        "current_latitude": fields.Float(description="Current latitude"),
        "current_longitude": fields.Float(description="Current longitude"),
        "rating": fields.Float(description="Driver rating"),
        "total_deliveries": fields.Integer(description="Total deliveries completed"),
        "is_active": fields.Boolean(description="Driver active status"),
        "created_at": fields.DateTime(readonly=True),
        "updated_at": fields.DateTime(readonly=True),
    },
)

driver_registration_model = driver_api.model(
    "DriverRegistration",
    {
        "phone_number": fields.String(required=True, description="Driver phone number"),
        "first_name": fields.String(required=True, description="Driver first name"),
        "last_name": fields.String(required=True, description="Driver last name"),
        "license_number": fields.String(required=True, description="Driver license number"),
        "vehicle_type": fields.String(required=True, description="Vehicle type"),
        "vehicle_make": fields.String(required=True, description="Vehicle make"),
        "vehicle_model": fields.String(required=True, description="Vehicle model"),
        "vehicle_year": fields.Integer(required=True, description="Vehicle year"),
        "vehicle_plate_number": fields.String(required=True, description="Vehicle plate number"),
        "driving_license_image": fields.String(description="GCS object key for driving license image"),
        "id_card_image": fields.String(description="GCS object key for ID card image"),
        "insurance_image": fields.String(description="GCS object key for insurance image"),
    },
)

update_location_model = driver_api.model(
    "UpdateLocation",
    {
        "latitude": fields.Float(required=True, description="Current latitude"),
        "longitude": fields.Float(required=True, description="Current longitude"),
    },
)

update_push_token_model = driver_api.model(
    "UpdatePushToken",
    {
        "push_token": fields.String(required=True, description="FCM push token"),
        "device_id": fields.String(description="Device identifier"),
    },
)

document_upload_model = driver_api.model(
    "DocumentUpload",
    {
        "doc_type": fields.String(
            required=True,
            enum=["driver_license", "id_card", "insurance"],
            description="Type of document",
        ),
        "filename": fields.String(required=True, description="Original filename"),
        "content_type": fields.String(required=True, description="MIME type of the file"),
    },
)

document_upload_response_model = driver_api.model(
    "DocumentUploadResponse",
    {
        "upload_url": fields.String(description="Signed URL for uploading the document"),
        "object_key": fields.String(description="Object key to store in database"),
        "expires_in": fields.Integer(description="URL expiration time in seconds"),
    },
)


def _validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?1?\d{9,15}$", phone))


def _attach_signed_urls(driver_data: dict) -> dict:
    """Attach GCS signed download URLs to a driver dict (best-effort)."""
    try:
        svc = get_storage_service()
        driver_data["driving_license_url"] = (
            svc.get_download_url(driver_data["driving_license_image"], expires_seconds=300)
            if driver_data.get("driving_license_image")
            else None
        )
        driver_data["id_card_url"] = (
            svc.get_download_url(driver_data["id_card_image"], expires_seconds=300)
            if driver_data.get("id_card_image")
            else None
        )
        driver_data["insurance_url"] = (
            svc.get_download_url(driver_data["insurance_image"], expires_seconds=300)
            if driver_data.get("insurance_image")
            else None
        )
    except Exception:
        driver_data.setdefault("driving_license_url", None)
        driver_data.setdefault("id_card_url", None)
        driver_data.setdefault("insurance_url", None)
    return driver_data


# ── Routes ────────────────────────────────────────────────────────────────────


@driver_api.route("/register")
class DriverRegistration(Resource):
    @driver_api.expect(driver_registration_model)
    @driver_api.response(201, "Registered", driver_model)
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Invalid Firebase token")
    def post(self):
        """Create driver profile after Firebase Auth sign-up.
        Requires a valid Firebase ID token in the Authorization header."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

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

        repo = DriverRepository()

        # Idempotent — return existing profile if already registered
        existing = repo.get_by_firebase_uid(firebase_uid)
        if existing:
            return {"message": "Profile already exists", "driver": _attach_signed_urls(repo.to_public_dict(existing))}, 200

        data = driver_api.payload or {}

        required = ["first_name", "last_name", "phone_number", "license_number",
                    "vehicle_type", "vehicle_make", "vehicle_model", "vehicle_year", "vehicle_plate_number"]
        missing = [f for f in required if not data.get(f)]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        if not _validate_phone(data["phone_number"]):
            return {"error": "Invalid phone number format"}, 400

        if "vehicle_year" in data and data["vehicle_year"] is not None:
            current_year = datetime.now().year
            if not isinstance(data["vehicle_year"], int) or not (1900 <= data["vehicle_year"] <= current_year + 1):
                return {"error": f"vehicle_year must be an integer between 1900 and {current_year + 1}"}, 400

        if repo.exists_by_field("email", email):
            return {"error": "Email already registered"}, 400
        if repo.exists_by_field("phone_number", data["phone_number"]):
            return {"error": "Phone number already registered"}, 400
        if repo.exists_by_field("license_number", data["license_number"]):
            return {"error": "License number already registered"}, 400

        try:
            driver_data = repo.create_driver(
                {
                    "firebase_uid": firebase_uid,
                    "email": email,
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone_number": data["phone_number"],
                    "license_number": data["license_number"],
                    "vehicle_type": data["vehicle_type"],
                    "vehicle_make": data["vehicle_make"],
                    "vehicle_model": data["vehicle_model"],
                    "vehicle_year": data["vehicle_year"],
                    "vehicle_plate_number": data["vehicle_plate_number"],
                    "driving_license_image": data.get("driving_license_image"),
                    "id_card_image": data.get("id_card_image"),
                    "insurance_image": data.get("insurance_image"),
                }
            )
            try:
                firebase_admin.auth.set_custom_user_claims(firebase_uid, {"role": "driver"})
            except Exception:
                pass  # Non-fatal

            _attach_signed_urls(driver_data)
            return {"message": "Driver registration successful", "driver": driver_data}, 201
        except Exception as e:
            return {"error": "Registration failed", "details": str(e)}, 500


@driver_api.route("/register/document-urls")
class DriverRegistrationDocumentUrls(Resource):
    @driver_api.response(200, "Document upload URLs generated successfully")
    @driver_api.response(400, "Validation Error")
    def post(self):
        """Get signed URLs for uploading Driving License and Insurance documents during registration."""
        data = driver_api.payload or {}
        required_fields = ["driver_id", "driving_license_filename", "insurance_filename"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        try:
            driver_id = int(data["driver_id"])
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            driver = DriverRepository().get_by_id(driver_id)
            if not driver:
                return {"error": "Driver not found"}, 404

            svc = get_storage_service()
            dl_url, dl_key = svc.get_upload_url(driver_id=driver_id, doc_type="driver_license",
                                                  filename=data["driving_license_filename"], content_type="image/jpeg")
            ins_url, ins_key = svc.get_upload_url(driver_id=driver_id, doc_type="insurance",
                                                    filename=data["insurance_filename"], content_type="image/jpeg")
            return {
                "upload_urls": {
                    "driving_license": {"upload_url": dl_url, "object_key": dl_key, "expires_in": 600},
                    "insurance": {"upload_url": ins_url, "object_key": ins_key, "expires_in": 600},
                },
                "driver_id": driver_id,
                "message": "Document upload URLs generated successfully",
            }, 200

        except ValueError:
            return {"error": "driver_id must be a valid integer"}, 400
        except Exception as e:
            return {"error": "Failed to generate document upload URLs", "details": str(e)}, 500


@driver_api.route("/register/upload-urls")
class DriverRegistrationUploadUrls(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model(
            "RegistrationUploadUrls",
            {
                "documents": fields.List(
                    fields.Nested(
                        driver_api.model(
                            "DocumentInfo",
                            {
                                "doc_type": fields.String(required=True, enum=["driver_license", "id_card"]),
                                "filename": fields.String(required=True),
                                "content_type": fields.String(required=True),
                            },
                        )
                    ),
                    required=True,
                )
            },
        )
    )
    @driver_api.response(200, "Upload URLs generated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Get signed URLs for uploading documents during registration."""
        driver_id = g.driver_id
        data = driver_api.payload or {}

        if "documents" not in data or not isinstance(data["documents"], list):
            return {"error": "documents array is required"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            driver = DriverRepository().get_by_id(driver_id)
            if not driver:
                return {"error": "Driver not found"}, 404

            svc = get_storage_service()
            upload_urls = []
            for doc_info in data["documents"]:
                if not all(k in doc_info for k in ["doc_type", "filename", "content_type"]):
                    return {"error": "Each document must have doc_type, filename, and content_type"}, 400
                if doc_info["doc_type"] not in ["driver_license", "id_card"]:
                    return {"error": "Invalid document type. Must be driver_license or id_card"}, 400

                upload_url, object_key = svc.get_upload_url(
                    driver_id=driver_id,
                    doc_type=doc_info["doc_type"],
                    filename=doc_info["filename"],
                    content_type=doc_info["content_type"],
                )
                upload_urls.append({
                    "doc_type": doc_info["doc_type"],
                    "filename": doc_info["filename"],
                    "upload_url": upload_url,
                    "object_key": object_key,
                    "expires_in": 600,
                })

            return {"upload_urls": upload_urls, "driver_id": driver_id}, 200

        except Exception as e:
            return {"error": "Failed to generate upload URLs", "details": str(e)}, 500


@driver_api.route("/profile")
class DriverProfile(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Success", driver_model)
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Driver not found")
    @firebase_driver_required
    def get(self):
        """Get driver profile with signed URLs for documents."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        repo = DriverRepository()
        driver_doc = repo.get_by_id(g.driver_id)
        if not driver_doc:
            return {"error": "Driver not found"}, 404

        return _attach_signed_urls(repo.to_public_dict(driver_doc)), 200

    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model(
            "UpdateDriverProfile",
            {
                "first_name": fields.String(description="Driver first name"),
                "last_name": fields.String(description="Driver last name"),
                "phone_number": fields.String(description="Driver phone number"),
                "password": fields.String(description="New password (optional)"),
            },
        )
    )
    @driver_api.response(200, "Profile updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def put(self):
        """Update driver profile."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        data = driver_api.payload or {}
        update: dict = {}

        for field in ("first_name", "last_name"):
            if field in data:
                update[field] = data[field]

        if "phone_number" in data:
            if not _validate_phone(data["phone_number"]):
                return {"error": "Invalid phone number format"}, 400
            existing = DriverRepository().get_by_phone(data["phone_number"])
            if existing and existing.get("id") != g.driver_id:
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
                print(f"✅ Password updated for driver: {g.firebase_uid}")
            except Exception as e:
                print(f"❌ Error updating password for driver {g.firebase_uid}: {str(e)}")
                return {"error": "Failed to update password", "details": str(e)}, 500

        if not update and "password" not in data:
            return {"error": "No fields to update"}, 400

        try:
            repo = DriverRepository()
            if update:  # Only update Firestore fields if there are any
                ok = repo.update_fields(g.driver_id, update)
                if not ok:
                    return {"error": "Failed to update profile"}, 500

            updated = repo.get_by_id(g.driver_id)
            return {
                "message": "Profile updated successfully",
                "driver": repo.to_public_dict(updated),
            }, 200
        except Exception as e:
            return {"error": "Failed to update profile", "details": str(e)}, 500


@driver_api.route("/location")
class UpdateLocation(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(update_location_model)
    @driver_api.response(200, "Location updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver's current location."""
        data = driver_api.payload or {}

        if not all(k in data for k in ["latitude", "longitude"]):
            return {"error": "Missing latitude or longitude"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ok = DriverRepository().update_location(g.driver_id, data["latitude"], data["longitude"])
            if not ok:
                return {"error": "Driver not found"}, 404

            return {"message": "Location updated successfully", "latitude": data["latitude"], "longitude": data["longitude"]}, 200
        except Exception as e:
            return {"error": "Failed to update location", "details": str(e)}, 500


@driver_api.route("/push-token")
class UpdatePushToken(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(update_push_token_model)
    @driver_api.response(200, "Push token updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver's push notification token."""
        data = driver_api.payload or {}

        if "push_token" not in data:
            return {"error": "Missing push token"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ok = DriverRepository().update_push_token(g.driver_id, data["push_token"], data.get("device_id"))
            if not ok:
                return {"error": "Driver not found"}, 404

            return {"message": "Push token updated successfully", "push_token": data["push_token"]}, 200
        except Exception as e:
            return {"error": "Failed to update push token", "details": str(e)}, 500


@driver_api.route("/status")
class UpdateStatus(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model("StatusUpdate", {
            "status": fields.String(enum=["available", "busy", "offline"], description="Driver status")
        })
    )
    @driver_api.response(200, "Status updated successfully")
    @driver_api.response(400, "Invalid status")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver's status (available/busy/offline)."""
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict() or {}

        status = data.get("status", "available")
        status_mapping = {
            "available": DriverStatus.AVAILABLE,
            "busy": DriverStatus.BUSY,
            "offline": DriverStatus.OFFLINE,
        }

        if status not in status_mapping:
            return {"error": "Invalid status. Must be: available, busy, or offline"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            is_available = status == "available"
            ok = DriverRepository().set_status(
                g.driver_id,
                status_value=status_mapping[status].value,
                is_available=is_available,
            )
            if not ok:
                return {"error": "Driver not found"}, 404

            return {"message": "Status updated successfully", "status": status}, 200
        except Exception as e:
            return {"error": "Failed to update status", "details": str(e)}, 500


@driver_api.route("/availability")
class DriverAvailability(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model("UpdateAvailability", {
            "is_available": fields.Boolean(required=True, description="Driver availability status")
        })
    )
    @driver_api.response(200, "Availability updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver availability."""
        data = driver_api.payload or {}

        if "is_available" not in data:
            return {"error": "is_available field is required"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ok = DriverRepository().set_availability(g.driver_id, bool(data["is_available"]))
            if not ok:
                return {"error": "Driver not found"}, 404

            return {
                "message": "Availability updated successfully",
                "is_available": bool(data["is_available"]),
                "status": DriverStatus.AVAILABLE.value if data["is_available"] else DriverStatus.OFFLINE.value,
            }, 200
        except Exception as e:
            return {"error": "Failed to update availability", "details": str(e)}, 500


@driver_api.route("/payment-method")
class DriverPaymentMethod(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model("UpdatePaymentMethod", {
            "has_payment_method": fields.Boolean(required=True, description="Payment method added status")
        })
    )
    @driver_api.response(200, "Payment method status updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver payment method status."""
        data = driver_api.payload or {}

        if "has_payment_method" not in data:
            return {"error": "has_payment_method field is required"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ok = DriverRepository().set_has_payment_method(g.driver_id, bool(data["has_payment_method"]))
            if not ok:
                return {"error": "Driver not found"}, 404

            return {
                "message": "Payment method status updated successfully",
                "has_payment_method": bool(data["has_payment_method"]),
            }, 200
        except Exception as e:
            return {"error": "Failed to update payment method status", "details": str(e)}, 500


@driver_api.route("/notifications")
class DriverNotifications(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Success")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def get(self):
        """Get driver's notifications."""
        status = request.args.get("status")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        try:
            notifications = notification_service.get_driver_notifications(g.driver_id, limit, offset)
            if status:
                notifications = [n for n in notifications if n["status"] == status]

            return {"notifications": notifications, "total": len(notifications), "limit": limit, "offset": offset}, 200
        except Exception as e:
            return {"error": "Failed to get notifications", "details": str(e)}, 500


@driver_api.route("/notifications/<int:notification_id>/read")
class MarkNotificationRead(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Notification marked as read")
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Notification not found")
    @firebase_driver_required
    def post(self, notification_id):
        """Mark a notification as read."""
        try:
            success = notification_service.mark_notification_as_read(notification_id, g.driver_id)
            if success:
                return {"message": "Notification marked as read"}, 200
            return {"error": "Notification not found"}, 404
        except Exception as e:
            return {"error": "Failed to mark notification as read", "details": str(e)}, 500


@driver_api.route("/rides/<int:ride_id>/accept")
class AcceptRide(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Ride accepted successfully")
    @driver_api.response(400, "Cannot accept ride")
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Ride not found")
    @firebase_driver_required
    def post(self, ride_id):
        """Accept a ride assignment."""
        driver_id = g.driver_id

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ride_repo = RideRepository()
            driver_repo = DriverRepository()

            ride_doc = ride_repo.get_by_id(ride_id)
            if not ride_doc:
                return {"error": "Ride not found"}, 404

            driver_doc = driver_repo.get_by_id(driver_id)
            if not driver_doc:
                return {"error": "Driver not found"}, 404

            if (driver_doc.get("status") or DriverStatus.AVAILABLE.value) != DriverStatus.AVAILABLE.value:
                return {"error": "Driver must be available to accept rides"}, 400

            if not ride_doc.get("driver_id") and ride_doc.get("status") == RideStatus.REQUESTED.value:
                ride_repo.update_for_assignment(ride_id, driver_id, status=RideStatus.ASSIGNED.value)
                driver_repo.set_status(driver_id, DriverStatus.BUSY.value, is_available=False)
                ride_doc = ride_repo.get_by_id(ride_id) or ride_doc
            elif (ride_doc.get("driver_id") and int(ride_doc.get("driver_id")) != driver_id
                  and ride_doc.get("status") == RideStatus.ASSIGNED.value):
                ride_repo.update_for_assignment(ride_id, driver_id, status=RideStatus.ASSIGNED.value)
                driver_repo.set_status(driver_id, DriverStatus.BUSY.value, is_available=False)
                ride_doc = ride_repo.get_by_id(ride_id) or ride_doc

            if int(ride_doc.get("driver_id") or 0) != driver_id:
                return {"error": "Ride not assigned to this driver"}, 400

            if ride_doc.get("status") != RideStatus.ASSIGNED.value:
                return {"error": "Ride cannot be accepted in its current status"}, 400

            ok = ride_repo.accept(ride_id, driver_id)
            if not ok:
                return {"error": "Failed to accept ride"}, 500

            driver_repo.set_status(driver_id, DriverStatus.BUSY.value, is_available=False)
            ride_doc = ride_repo.get_by_id(ride_id) or ride_doc
            return {"message": "Ride accepted successfully", "ride": ride_repo.to_public_dict(ride_doc)}, 200

        except Exception as e:
            return {"error": "Failed to accept ride", "details": str(e)}, 500


@driver_api.route("/rides/<int:ride_id>/reject")
class RejectRide(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Ride rejected successfully")
    @driver_api.response(400, "Cannot reject ride")
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Ride not found")
    @firebase_driver_required
    def post(self, ride_id):
        """Reject a ride assignment."""
        driver_id = g.driver_id

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            ride_repo = RideRepository()
            driver_repo = DriverRepository()

            ride_doc = ride_repo.get_by_id(ride_id)
            if not ride_doc:
                return {"error": "Ride not found"}, 404

            if not ride_doc.get("driver_id") and ride_doc.get("status") == RideStatus.REQUESTED.value:
                driver_doc = driver_repo.get_by_id(driver_id)
                if not driver_doc:
                    return {"error": "Driver not found"}, 404
                ride_repo.update_for_assignment(ride_id, driver_id, status=RideStatus.ASSIGNED.value)
                ride_doc = ride_repo.get_by_id(ride_id) or ride_doc

            if int(ride_doc.get("driver_id") or 0) != driver_id:
                return {"error": "Ride not assigned to this driver"}, 400

            if ride_doc.get("status") != RideStatus.ASSIGNED.value:
                return {"error": "Ride cannot be rejected in its current status"}, 400

            ok = ride_repo.reject(ride_id, driver_id)
            if not ok:
                return {"error": "Failed to reject ride"}, 500

            driver_repo.set_status(driver_id, DriverStatus.AVAILABLE.value, is_available=True)
            ride_doc = ride_repo.get_by_id(ride_id) or ride_doc
            return {"message": "Ride rejected successfully", "ride": ride_repo.to_public_dict(ride_doc)}, 200

        except Exception as e:
            return {"error": "Failed to reject ride", "details": str(e)}, 500


@driver_api.route("/documents/upload-url")
class GetDocumentUploadUrl(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(document_upload_model)
    @driver_api.response(200, "Upload URL generated successfully", document_upload_response_model)
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Get signed URL for uploading a driver document."""
        data = driver_api.payload or {}

        required_fields = ["doc_type", "filename", "content_type"]
        if not all(k in data for k in required_fields):
            return {"error": "Missing required fields: doc_type, filename, content_type"}, 400

        if data["doc_type"] not in ["driver_license", "id_card", "insurance"]:
            return {"error": "Invalid document type. Must be driver_license, id_card, or insurance"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            driver = DriverRepository().get_by_id(g.driver_id)
            if not driver:
                return {"error": "Driver not found"}, 404

            upload_url, object_key = get_storage_service().get_upload_url(
                driver_id=g.driver_id,
                doc_type=data["doc_type"],
                filename=data["filename"],
                content_type=data["content_type"],
            )
            return {
                "upload_url": upload_url,
                "object_key": object_key,
                "expires_in": 600,
                "message": f"Upload URL generated for {data['doc_type']}. Call confirm-upload after upload.",
            }, 200
        except Exception as e:
            return {"error": "Failed to generate upload URL", "details": str(e)}, 500


@driver_api.route("/documents/upload-url/public")
class GetPublicDocumentUploadUrl(Resource):
    @driver_api.expect(
        driver_api.model(
            "PublicDocumentUpload",
            {
                "driver_id": fields.Integer(required=True, description="Driver ID"),
                "doc_type": fields.String(required=True, enum=["driver_license", "id_card", "insurance"]),
                "filename": fields.String(required=True),
                "content_type": fields.String(required=True),
            },
        )
    )
    @driver_api.response(200, "Upload URL generated successfully", document_upload_response_model)
    @driver_api.response(400, "Validation Error")
    @driver_api.response(404, "Driver not found")
    def post(self):
        """Get signed URL for uploading a driver document (no auth — for registration flow)."""
        data = driver_api.payload or {}
        required_fields = ["driver_id", "doc_type", "filename", "content_type"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return {"error": f"Missing required fields: {', '.join(missing)}"}, 400

        if data["doc_type"] not in ["driver_license", "id_card", "insurance"]:
            return {"error": "Invalid document type. Must be driver_license, id_card, or insurance"}, 400

        try:
            driver_id = int(data["driver_id"])
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            driver = DriverRepository().get_by_id(driver_id)
            if not driver:
                return {"error": "Driver not found"}, 404

            upload_url, object_key = get_storage_service().get_upload_url(
                driver_id=driver_id,
                doc_type=data["doc_type"],
                filename=data["filename"],
                content_type=data["content_type"],
            )
            return {
                "upload_url": upload_url,
                "object_key": object_key,
                "expires_in": 600,
                "message": f"Upload URL generated for {data['doc_type']}. Call confirm-upload after upload.",
            }, 200
        except ValueError:
            return {"error": "driver_id must be a valid integer"}, 400
        except Exception as e:
            return {"error": "Failed to generate upload URL", "details": str(e)}, 500


@driver_api.route("/documents/confirm-upload")
class ConfirmDocumentUpload(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model(
            "ConfirmUpload",
            {
                "doc_type": fields.String(required=True, enum=["driver_license", "id_card", "insurance"]),
                "object_key": fields.String(required=True, description="Object key from upload URL response"),
            },
        )
    )
    @driver_api.response(200, "Document upload confirmed successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Confirm document upload and update driver record."""
        data = driver_api.payload or {}

        if not all(k in data for k in ["doc_type", "object_key"]):
            return {"error": "Missing required fields: doc_type, object_key"}, 400

        if data["doc_type"] not in ["driver_license", "id_card", "insurance"]:
            return {"error": "Invalid document type. Must be driver_license, id_card, or insurance"}, 400

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            svc = get_storage_service()
            repo = DriverRepository()
            driver_doc = repo.get_by_id(g.driver_id)
            if not driver_doc:
                return {"error": "Driver not found"}, 404

            if not svc.object_exists(svc.bucket_name, data["object_key"]):
                return {"error": "Document not found in storage"}, 400

            field_map = {"driver_license": "driving_license_image", "id_card": "id_card_image", "insurance": "insurance_image"}
            old_key = driver_doc.get(field_map[data["doc_type"]])
            if old_key:
                svc.cleanup_old_document(g.driver_id, data["doc_type"], old_key)

            ok = repo.update_document_key(g.driver_id, data["doc_type"], data["object_key"])
            if not ok:
                return {"error": "Failed to update driver document reference"}, 500

            return {
                "message": "Document upload confirmed successfully",
                "doc_type": data["doc_type"],
                "object_key": data["object_key"],
            }, 200
        except Exception as e:
            return {"error": "Failed to confirm document upload", "details": str(e)}, 500


@driver_api.route("/documents")
class DriverDocuments(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.expect(
        driver_api.model(
            "UpdateDocuments",
            {
                "driving_license_image": fields.String(description="Object key for driving license image"),
                "id_card_image": fields.String(description="Object key for ID card image"),
            },
        )
    )
    @driver_api.response(200, "Documents updated successfully")
    @driver_api.response(400, "Validation Error")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Update driver documents (legacy — prefer upload-url + confirm-upload)."""
        data = driver_api.payload or {}

        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            repo = DriverRepository()
            svc = get_storage_service()
            driver_doc = repo.get_by_id(g.driver_id)
            if not driver_doc:
                return {"error": "Driver not found"}, 404

            if "driving_license_image" in data:
                if driver_doc.get("driving_license_image"):
                    svc.cleanup_old_document(g.driver_id, "driver_license", driver_doc["driving_license_image"])
                repo.update_document_key(g.driver_id, "driver_license", data["driving_license_image"])

            if "id_card_image" in data:
                if driver_doc.get("id_card_image"):
                    svc.cleanup_old_document(g.driver_id, "id_card", driver_doc["id_card_image"])
                repo.update_document_key(g.driver_id, "id_card", data["id_card_image"])

            updated = repo.get_by_id(g.driver_id) or driver_doc
            return {"message": "Documents updated successfully", "driver": repo.to_public_dict(updated)}, 200
        except Exception as e:
            return {"error": "Failed to update documents", "details": str(e)}, 500


@driver_api.route("/check/<int:driver_id>")
class CheckDriver(Resource):
    @driver_api.response(200, "Driver found")
    @driver_api.response(404, "Driver not found")
    def get(self, driver_id):
        """Check if driver exists (debug endpoint)."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        driver = DriverRepository().get_by_id(driver_id)
        if not driver:
            return {"error": "Driver not found", "driver_id": driver_id}, 404

        return {
            "message": "Driver found",
            "driver_id": driver.get("id"),
            "email": driver.get("email"),
            "first_name": driver.get("first_name"),
            "last_name": driver.get("last_name"),
            "created_at": driver.get("created_at").isoformat() if driver.get("created_at") else None,
        }, 200


@driver_api.route("/<int:driver_id>")
class GetDriver(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Driver retrieved successfully", driver_model)
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Driver not found")
    @firebase_driver_required
    def get(self, driver_id):
        """Get a specific driver by ID."""
        try:
            if not USE_FIREBASE_DB:
                return {"error": "Service unavailable"}, 503

            repo = DriverRepository()
            driver_doc = repo.get_by_id(driver_id)
            if not driver_doc:
                return {"error": "Driver not found"}, 404

            driver_data = repo.to_public_dict(driver_doc)
            driver_data["full_name"] = f"{driver_data.get('first_name', '')} {driver_data.get('last_name', '')}".strip()
            return driver_data, 200
        except Exception as e:
            return {"error": "Failed to retrieve driver", "details": str(e)}, 500


@driver_api.route("/reset-password")
class ResetPassword(Resource):
    """Reset driver password after phone OTP verification."""

    @driver_api.response(200, "Password reset successfully")
    @driver_api.response(400, "Invalid request")
    @driver_api.response(401, "Unauthorized")
    @firebase_driver_required
    def post(self):
        """Reset password for driver (verified via phone OTP)."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        data = driver_api.payload or {}
        new_password = data.get("new_password", "").strip()
        email = data.get("email", "").strip()

        if not new_password or len(new_password) < 6:
            return {"error": "Password must be at least 6 characters"}, 400

        if not email:
            return {"error": "Email address is required"}, 400

        try:
            print(f"🔐 Attempting password reset for driver: {email}")

            # Get user by email from Firebase Auth
            user = firebase_admin.auth.get_user_by_email(email)
            print(f"✅ Found driver: {user.uid} for email: {email}")

            # Update Firebase Auth password using admin SDK
            firebase_admin.auth.update_user(
                user.uid,
                password=new_password
            )
            print(f"✅ Password reset successful for driver: {user.uid} ({email})")
            return {"message": "Password reset successfully"}, 200
        except firebase_admin.auth.UserNotFoundError:
            print(f"❌ Driver not found for email: {email}")
            return {"error": "User not found with that email"}, 404
        except Exception as e:
            print(f"❌ Error resetting password for driver {email}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": "Failed to reset password", "details": str(e)}, 500


@driver_api.route("/<int:driver_id>/documents")
class AdminDriverDocuments(Resource):
    @driver_api.doc(security="Bearer Auth")
    @driver_api.response(200, "Success")
    @driver_api.response(401, "Unauthorized")
    @driver_api.response(404, "Driver not found")
    @firebase_driver_required
    def get(self, driver_id):
        """Get driver documents with signed URLs (admin endpoint)."""
        if not USE_FIREBASE_DB:
            return {"error": "Service unavailable"}, 503

        repo = DriverRepository()
        driver_doc = repo.get_by_id(driver_id)
        if not driver_doc:
            return {"error": "Driver not found"}, 404

        return _attach_signed_urls(repo.to_public_dict(driver_doc)), 200
