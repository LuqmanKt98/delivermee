from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime
import logging

from repositories.delivery_repository import DeliveryRepository
from repositories.payment_repository import PaymentRepository
from services.payment_service import payment_service
from settings import USE_FIREBASE_DB
from utils.firebase_auth_middleware import firebase_customer_required


logger = logging.getLogger(__name__)

payment_api = Namespace("payments", description="Payment operations (Firestore mode)")


payment_intent_model = payment_api.model(
    "PaymentIntent",
    {
        "delivery_id": fields.Integer(required=True, description="Delivery ID"),
        "amount": fields.Integer(required=True, description="Payment amount in cents"),
        "tip_amount": fields.Integer(description="Tip amount in cents", default=0),
        "currency": fields.String(description="Currency code", default="usd"),
        "save_payment_method": fields.Boolean(default=False),
    },
)

payment_confirm_model = payment_api.model(
    "PaymentConfirm",
    {
        "payment_intent_id": fields.String(required=True),
        "payment_method_id": fields.String(required=True),
    },
)


@payment_api.route("/create-payment-intent")
class CreatePaymentIntent(Resource):
    @payment_api.doc(security="Bearer Auth")
    @payment_api.expect(payment_intent_model)
    @firebase_customer_required
    def post(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        customer_id = g.customer_id
        data = request.get_json() or {}

        for field in ["delivery_id", "amount"]:
            if field not in data:
                return {"success": False, "error": f"Missing required field: {field}"}, 400

        delivery_id = int(data["delivery_id"])
        amount_cents = int(data["amount"])
        tip_cents = int(data.get("tip_amount", 0) or 0)
        currency = (data.get("currency") or "usd").lower()
        save_payment_method = bool(data.get("save_payment_method", False))

        if amount_cents < 50:
            return {"success": False, "error": "Amount too small (minimum $0.50)"}, 400

        delivery_repo = DeliveryRepository()
        delivery = delivery_repo.get_by_id(delivery_id)
        if not delivery or int(delivery.get("customer_id") or 0) != int(customer_id):
            return {"success": False, "error": "Delivery not found or access denied"}, 404

        breakdown = payment_service.calculate_delivery_payment_breakdown(
            base_amount=amount_cents / 100.0,
            tip_amount=tip_cents / 100.0,
            currency=currency.upper(),
        )

        payment_doc = PaymentRepository().create(
            {
                "payment_type": "delivery_fee",
                "amount": breakdown["total_amount"],
                "currency": currency.upper(),
                "status": "pending",
                "direction": "inbound",
                "payer_id": customer_id,
                "payer_type": "customer",
                "receiver_type": "platform",
                "payment_method": "credit_card",
                "delivery_id": delivery_id,
                "base_amount": breakdown["base_amount"],
                "platform_fee": breakdown["platform_fee"],
                "payment_processing_fee": breakdown["payment_processing_fee"],
                "driver_payout": breakdown["driver_payout"],
                "tip_amount": breakdown["tip_amount"],
                "description": f"Delivery payment for delivery {delivery_id}",
                "payment_metadata": {
                    "save_payment_method": save_payment_method,
                    "creation_time": datetime.utcnow().isoformat(),
                    "note": "Stripe integration handled by mobile payment system",
                },
            }
        )

        payment_intent_id = f"pi_{payment_doc['payment_id']}_{int(datetime.utcnow().timestamp())}"
        return {
            "success": True,
            "payment_intent_id": payment_intent_id,
            "amount": breakdown["total_amount_cents"],
            "payment_id": payment_doc["payment_id"],
            "delivery_id": delivery_id,
            "fee_breakdown": {
                "base_amount": breakdown["base_amount"],
                "tip_amount": breakdown["tip_amount"],
                "platform_fee": breakdown["platform_fee"],
                "payment_processing_fee": breakdown["payment_processing_fee"],
                "total_amount": breakdown["total_amount"],
                "driver_earnings": breakdown["driver_payout"],
            },
            "estimated_completion_time": "2-3",
            "note": "Firestore mode: simplified (no Stripe) payments",
        }, 201


@payment_api.route("/confirm-payment")
class ConfirmPayment(Resource):
    @payment_api.doc(security="Bearer Auth")
    @payment_api.expect(payment_confirm_model)
    @firebase_customer_required
    def post(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503

        customer_id = g.customer_id
        data = request.get_json() or {}
        payment_intent_id = data.get("payment_intent_id")
        payment_method_id = data.get("payment_method_id")
        if not payment_intent_id or not payment_method_id:
            return {"success": False, "error": "Missing payment intent ID or payment method ID"}, 400

        # We generate payment_intent_id as: pi_{payment_id}_{timestamp}
        parts = str(payment_intent_id).split("_")
        if len(parts) < 3:
            return {"success": False, "error": "Invalid payment_intent_id format"}, 400
        payment_id = parts[1]

        pay_repo = PaymentRepository()
        payment = pay_repo.get_by_id(payment_id)
        if not payment or int(payment.get("payer_id") or 0) != int(customer_id):
            return {"success": False, "error": "Payment not found or access denied"}, 404

        ok = pay_repo.mark_completed(payment_id, payment_method_id=str(payment_method_id))
        if not ok:
            return {"success": False, "error": "Failed to confirm payment"}, 500

        # Update delivery payment status and set it ready for driver assignment visibility
        delivery_id = payment.get("delivery_id")
        if delivery_id is not None:
            DeliveryRepository().mark_payment_completed(delivery_id, actual_cost=payment.get("amount"))
            DeliveryRepository().update_fields(delivery_id, {"status": "assigned"})

        logger.info(f"Payment confirmed for payment {payment_id}")
        return {
            "success": True,
            "payment_id": payment_id,
            "delivery_id": delivery_id,
            "amount": payment.get("amount"),
            "status": "completed",
            "note": "Firestore mode: payment confirmed (no Stripe)",
        }, 200

