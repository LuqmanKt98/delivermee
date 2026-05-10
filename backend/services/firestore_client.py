import os
import json
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore

_firestore_client: Optional["firestore.Client"] = None


def _init_firebase_app():
    """
    Initialize Firebase Admin SDK once.

    Notes:
    - If `FIREBASE_SERVICE_ACCOUNT` env var is set, use it (for Vercel deployment)
    - If `GOOGLE_APPLICATION_CREDENTIALS` is set, we use the service account JSON file.
    - If you're using the Firestore Emulator, the Admin SDK will route to it when
      `FIRESTORE_EMULATOR_HOST` is set (no cloud writes).
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # If using the Firestore emulator, avoid requiring ADC/service-account creds.
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        project_id = (
            os.getenv("GCP_PROJECT")
            or os.getenv("GCLOUD_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or "demo-project"
        )
        return firebase_admin.initialize_app(options={"projectId": project_id})

    # Get storage bucket name (just project ID for Firebase Admin SDK)
    storage_bucket = (
        os.getenv("FIREBASE_STORAGE_BUCKET")
        or os.getenv("GCS_BUCKET")
        or "delivermee-12c26.firebasestorage.app"
    )

    # Check for service account JSON in environment variable (Vercel deployment)
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if service_account_json:
        try:
            service_account_dict = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_dict)
            return firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket
            })
        except json.JSONDecodeError:
            pass

    # Check for service account file path
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
        return firebase_admin.initialize_app(cred, {
            'storageBucket': storage_bucket
        })

    # Fall back to Application Default Credentials (GCP env, etc.)
    cred = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(cred, {
        'storageBucket': storage_bucket
    })


def get_firestore():
    """Return a singleton Firestore client."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    _init_firebase_app()
    _firestore_client = firestore.client()
    return _firestore_client

