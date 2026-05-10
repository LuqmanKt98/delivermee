# DeliverMee

Cross-platform delivery marketplace connecting customers with independent driver-contractors. The repo is a monorepo containing the Flask API and the Flutter client.

```
deliver/
├── backend/   # Flask + Firestore + Stripe API (Python 3.11)
└── app/       # Flutter app — Android, iOS, Web, Desktop
```

---

## Stack

| Layer        | Technology                                                              |
| ------------ | ----------------------------------------------------------------------- |
| Mobile       | Flutter 3.5+, GetX, google_maps_flutter, flutter_stripe, firebase_*     |
| API          | Flask 2.3, Flask-RESTX (Swagger), Flask-SocketIO                        |
| Database     | Firebase Cloud Firestore (live), PostgreSQL/Alembic (legacy, disabled)  |
| Auth         | Firebase Auth (ID-token verified server-side)                           |
| Payments     | Stripe (PaymentIntents + webhooks)                                      |
| Storage      | Firebase Storage / Google Cloud Storage                                 |
| Maps/Geo     | Google Maps Platform (Maps SDK, Directions, Geocoding)                  |
| Realtime     | WebSockets (Socket.IO) for live driver tracking                         |
| Deploy       | Backend → Cloud Run / Vercel · Mobile → Play Store / App Store / Web    |

---

## Backend (`backend/`)

Flask app exposing a REST + WebSocket API. Firestore is the active datastore; the SQLAlchemy/Alembic plumbing is retained but disabled (`ORM_DISABLED` in `app.py`).

**Layout**

```
backend/
├── app.py                 # Flask factory + route wiring
├── extensions.py          # Flask-RESTX api, db, migrate
├── settings.py            # Env-driven config
├── wsgi.py                # Gunicorn / Cloud Run entrypoint
├── routes/                # HTTP namespaces (drivers, deliveries, payments, ...)
├── services/              # Business logic (pricing, routing, Stripe, FCM, Maps)
├── repositories/          # Firestore data access
├── models/                # SQLAlchemy models (legacy reference)
├── migrations/            # Alembic migrations (legacy reference)
├── utils/                 # Firebase auth middleware, password helpers
├── tests/                 # Smoke tests
├── firebase.json          # Firebase Hosting/Emulators config
├── firestore.rules        # Firestore security rules
├── firestore.indexes.json # Composite indexes
├── storage.rules          # Cloud Storage rules
├── Dockerfile             # Cloud Run image
├── cloudbuild.yaml        # Cloud Build pipeline
├── vercel.json            # Vercel serverless config
└── API_DOCUMENTATION.md   # Full API reference
└── SYSTEM_ARCHITECTURE.md # End-to-end architecture
```

**Run locally**

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate    # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                 # then fill in real values
python app.py                                        # http://localhost:5000
```

`GET /` returns the route map. Swagger UI is at `/api/swagger`.

**Required environment** — see `backend/.env.example`. Mandatory keys:

- `USE_FIREBASE_DB=true`
- `GCP_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS` (path to a Firebase Admin SDK JSON)
- `SECRET_KEY`, `JWT_SECRET_KEY`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `GOOGLE_MAPS_API_KEY`

---

## App (`app/`)

Flutter client targeting Android, iOS, Web, and Desktop. Uses GetX for state, Firebase for auth/data/storage, Stripe for in-app payments, and Google Maps for the live map.

**Layout**

```
app/lib/
├── main.dart
├── firebase_options.dart       # Generated; contains public Firebase config
└── src/
    ├── common/
    │   ├── constant/           # App-wide colors, validators, API base URL, Stripe public key
    │   ├── services/           # API client, payment, location, Firestore tracking, ...
    │   ├── utils/              # Reusable widgets and helpers
    │   └── widgets/
    ├── feature/
    │   ├── auth/               # Sign in / sign up / reset / role select
    │   ├── onboarding_screen/
    │   ├── user/               # Customer-side flows
    │   └── driver/             # Driver-side flows
    └── models/
```

**Run locally**

```bash
cd app
flutter pub get
flutter run              # picks the connected device
# or:
flutter run -d chrome
flutter run -d windows
```

**API base URL** — `app/lib/src/common/constant/api_config.dart` points to the Vercel backend. Switch to a local IP for dev (the constant has the commented template).

**Platform configs** committed in this repo (`google-services.json`, `GoogleService-Info.plist`, `firebase_options.dart`) contain only **public** Firebase keys; security is enforced by Firestore/Storage rules and bundle-ID restrictions. See [Firebase docs on API keys](https://firebase.google.com/docs/projects/api-keys).

---

## Security model

- **Server-side secrets** (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, service-account JSON, `JWT_SECRET_KEY`) live only in `.env` files locally and in Cloud Run / Vercel environment variables in production. They are gitignored and never committed.
- **Client-side keys** (Firebase web/Android/iOS API keys, Stripe publishable key, Maps API key) ship inside the app by necessity. Lock them down in Google Cloud Console → API restrictions:
  - Firebase API keys → restrict by app bundle ID / SHA-1 / HTTP referrer
  - Maps API keys → restrict to specific Maps APIs + bundle IDs / referrers
- **Auth** — Mobile clients send a Firebase ID token in the `Authorization: Bearer <token>` header. The backend verifies it via `firebase_admin.auth.verify_id_token()` (`backend/utils/firebase_auth_middleware.py`).
- **Firestore rules** — `backend/firestore.rules` is the source of truth for read/write authorization. Deploy with `firebase deploy --only firestore:rules`.

---

## Deployment

**Backend → Cloud Run**

```bash
cd backend
gcloud builds submit --config cloudbuild.yaml
gcloud run deploy delivermee-api --image gcr.io/<project>/delivermee-api --region <region>
```

Set runtime env vars from a `.env.production` you keep locally — pass them with `--set-env-vars` or via Secret Manager.

**Backend → Vercel**

`backend/vercel.json` already maps the Flask app. Push to a Vercel-connected branch, or `vercel --prod` from the `backend/` directory. Configure the same env vars in the Vercel dashboard.

**Firestore & Storage rules**

```bash
cd backend
firebase deploy --only firestore:rules,firestore:indexes,storage
```

**App → Stores / Web**

```bash
cd app
flutter build appbundle --release   # Android — upload to Play Console
flutter build ios --release         # iOS — archive in Xcode for App Store Connect
flutter build web --release         # Web — deploy build/web/
```

---

## API reference

Swagger UI: `<host>/api/swagger`. Detailed reference: [`backend/API_DOCUMENTATION.md`](backend/API_DOCUMENTATION.md). Architecture deep-dive: [`backend/SYSTEM_ARCHITECTURE.md`](backend/SYSTEM_ARCHITECTURE.md).

---

## License

Proprietary — all rights reserved.
