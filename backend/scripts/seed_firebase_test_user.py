"""
Create a test customer in Firestore (same data model as POST /api/customers/register).

This backend stores customers in the `customers` collection with hashed passwords.
It does not create Firebase Authentication users.

Usage (PowerShell, Firestore emulator):

    $env:USE_FIREBASE_DB = "true"
    $env:FIRESTORE_EMULATOR_HOST = "127.0.0.1:8080"
    $env:GCP_PROJECT = "demo-project"
    python scripts/seed_firebase_test_user.py

Usage (cloud Firestore): set GOOGLE_APPLICATION_CREDENTIALS and GCP_PROJECT, then run.

Optional flags: --email, --phone, --password, --first-name, --last-name
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a test customer in Firestore.")
    parser.add_argument(
        "--email",
        default="test.customer@example.com",
        help="Unique email (default: test.customer@example.com)",
    )
    parser.add_argument(
        "--phone",
        default="+15551234567",
        help="Unique phone E.164 style (default: +15551234567)",
    )
    parser.add_argument("--password", default="TestPass123", help="Password (min 6 chars)")
    parser.add_argument("--first-name", default="Test", dest="first_name")
    parser.add_argument("--last-name", default="Customer", dest="last_name")
    args = parser.parse_args()

    from settings import USE_FIREBASE_DB

    if not USE_FIREBASE_DB:
        print("Error: USE_FIREBASE_DB must be true. Set it in the environment or .env", file=sys.stderr)
        return 1

    if len(args.password) < 6:
        print("Error: password must be at least 6 characters", file=sys.stderr)
        return 1

    from repositories.customer_repository import CustomerRepository

    repo = CustomerRepository()

    if repo.exists_by_field("email", args.email):
        print(f"Customer already exists: {args.email}")
        print("Login with POST /api/customers/login using that email and password.")
        return 0

    if repo.exists_by_field("phone_number", args.phone):
        print(f"Phone already registered: {args.phone}", file=sys.stderr)
        return 1

    customer = repo.create_customer(
        {
            "email": args.email,
            "phone_number": args.phone,
            "password": args.password,
            "first_name": args.first_name,
            "last_name": args.last_name,
            "is_verified": True,
        }
    )

    print("Created test customer in Firestore:")
    print(f"  id:            {customer.get('id')}")
    print(f"  email:         {args.email}")
    print(f"  phone_number:  {args.phone}")
    print("  password:      (hidden; use the value you passed)")
    print()
    print("Try login:")
    print('  POST /api/customers/login  JSON: {"email": "...", "password": "..."}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
