from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os
import json
from enum import Enum
from dotenv import load_dotenv
from settings import USE_FIREBASE_DB, SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, DEBUG
from extensions import db, migrate, api


class EnumJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


load_dotenv()


def setup_environment():
    if not os.environ.get("GCS_BUCKET"):
        os.environ["GCS_BUCKET"] = "delivermee_bucket"


def create_app():
    app = Flask(__name__)
    app.json_encoder = EnumJSONEncoder

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Accept"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["Content-Type", "Authorization"],
    )

    @app.after_request
    def after_request(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,Accept")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

    api.init_app(app)
    # ORM_DISABLED: db/migrate not active in Firebase mode
    # db.init_app(app)
    # migrate.init_app(app, db)

    try:
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
        try:
            from services.live_tracking_service import init_live_tracking_service
            from services.websocket_service import init_websocket_service
            init_live_tracking_service(socketio)
            init_websocket_service(socketio)
        except ImportError:
            print("⚠️  WebSocket services not available")
    except Exception as e:
        print(f"⚠️  WebSocket initialization skipped: {e}")

    @app.errorhandler(401)
    def unauthorized(error):
        return {"error": "Unauthorized access"}, 401

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500

    @app.route("/")
    def index():
        return {
            "message": "DeliverMee Backend API",
            "version": "1.0",
            "status": "running",
            "auth": "Firebase Auth",
            "endpoints": {
                "health": "/api/health",
                "swagger": "/api/swagger",
                "customers": "/api/customers",
                "drivers": "/api/drivers",
                "deliveries": "/api/deliveries",
                "payments": "/api/payments",
                "mobile_payments": "/api/mobile-payments",
                "webhooks": "/api/webhooks/stripe/payment",
            },
        }, 200

    if USE_FIREBASE_DB:
        from routes.driver_routes import driver_api
        from routes.health_routes import health_api
        from routes.user_routes import api as customer_api
        from routes.pricing_routes import pricing_api
        from routes.delivery_routes_firebase import delivery_api
        from routes.payment_routes_firebase import payment_api
        from routes.mobile_payment_routes_firebase import mobile_payment_api
        from routes.stripe_webhook_routes import stripe_webhook_api

        api.add_namespace(driver_api)
        api.add_namespace(customer_api)
        api.add_namespace(pricing_api)
        api.add_namespace(delivery_api)
        api.add_namespace(payment_api, path="/payments")
        api.add_namespace(mobile_payment_api, path="/mobile-payments")
        api.add_namespace(health_api, path="/health")
        api.add_namespace(stripe_webhook_api, path="/webhooks/stripe")
    else:
        return app

    return app


setup_environment()
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
