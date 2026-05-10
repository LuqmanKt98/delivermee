"""
Create sample Firestore data by calling the Flask API in-process (same as real HTTP).

Prerequisites:
  - USE_FIREBASE_DB=true
  - Cloud: GOOGLE_APPLICATION_CREDENTIALS + GCP_PROJECT=backend-deliver-mee (or your project id)
  - Local emulator: FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 and GCP_PROJECT=demo-project

Usage (PowerShell, emulator in another terminal):

    $env:USE_FIREBASE_DB="true"
    $env:FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"
    $env:GCP_PROJECT="demo-project"
    python scripts/seed_firebase_sample_data.py

Usage (cloud Firestore): set credentials in .env, then:

    python scripts/seed_firebase_sample_data.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def main() -> int:
    _load_env()

    from settings import USE_FIREBASE_DB

    if not USE_FIREBASE_DB:
        print(
            "USE_FIREBASE_DB must be true. Set it in .env or the environment.",
            file=sys.stderr,
        )
        return 1

    # Unique-ish identities so re-runs do not collide with old docs
    suffix = str(int(time.time()))[-8:]

    from app import app

    client = app.test_client()

    customer_body = {
        "email": f"sample.customer.{suffix}@example.com",
        "phone_number": f"+1555{suffix[-7:]}",
        "password": "SamplePass123",
        "first_name": "Sample",
        "last_name": "Customer",
    }
    r = client.post("/api/customers/register", json=customer_body)
    cust_data = r.get_json()
    if r.status_code != 201:
        print(json.dumps(cust_data, indent=2))
        return 1
    customer_token = cust_data["access_token"]
    customer_id = cust_data["customer"]["id"]

    driver_body = {
        "email": f"sample.driver.{suffix}@example.com",
        "phone_number": f"+1666{suffix[-7:]}",
        "password": "SamplePass123",
        "first_name": "Sample",
        "last_name": "Driver",
        "license_number": f"LIC-{suffix}",
        "vehicle_type": "car",
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "vehicle_year": 2022,
        "vehicle_plate_number": f"SMP{suffix[-4:]}",
    }
    r = client.post("/api/drivers/register", json=driver_body)
    drv_data = r.get_json()
    if r.status_code != 201:
        print(json.dumps(drv_data, indent=2))
        return 1
    driver_token = drv_data["access_token"]
    driver_id = drv_data["driver"]["id"]

    delivery_body = {
        "pickup_address": "123 Sample St, Austin, TX",
        "dropoff_address": "456 Demo Ave, Austin, TX",
        "pickup_latitude": 30.2672,
        "pickup_longitude": -97.7431,
        "dropoff_latitude": 30.3072,
        "dropoff_longitude": -97.7551,
        "item_name": "Sample parcel",
        "item_description": "Seeded by scripts/seed_firebase_sample_data.py",
        "vehicle_type": "car",
        "weight": 2.5,
        "item_count": 1,
        "schedule_type": "immediate",
        "delivery_type": "standard",
    }
    r = client.post(
        "/api/deliveries/create",
        json=delivery_body,
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    del_json = r.get_json()
    if r.status_code != 201:
        print(json.dumps(del_json, indent=2))
        return 1
    delivery = del_json.get("delivery") or {}
    delivery_id = delivery.get("id")
    tracking_number = delivery.get("tracking_number")

    r = client.post(f"/api/deliveries/{delivery_id}/assign-driver/{driver_id}")
    assign_json = r.get_json()
    if r.status_code != 200:
        print(json.dumps(assign_json, indent=2))
        return 1

    r = client.post(
        f"/api/deliveries/{delivery_id}/accept",
        headers={"Authorization": f"Bearer {driver_token}"},
    )
    accept_json = r.get_json()
    if r.status_code != 200:
        print(json.dumps(accept_json, indent=2))
        return 1

    out = {
        "suffix": suffix,
        "customer": {
            "id": customer_id,
            "email": customer_body["email"],
            "password": customer_body["password"],
        },
        "driver": {
            "id": driver_id,
            "email": driver_body["email"],
            "password": driver_body["password"],
        },
        "delivery": {
            "id": delivery_id,
            "tracking_number": tracking_number,
            "status_after_seed": delivery.get("status"),
        },
        "messages": {
            "assign": assign_json,
            "accept": accept_json,
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
