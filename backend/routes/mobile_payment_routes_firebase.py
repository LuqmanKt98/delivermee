from flask import request, g
from flask_restx import Namespace, Resource, fields
from datetime import datetime
import logging

from repositories.delivery_repository import DeliveryRepository
from repositories.payment_repository import PaymentRepository
from services.stripe_payment_service import stripe_payment_service
from settings import USE_FIREBASE_DB
from utils.firebase_auth_middleware import firebase_customer_required


logger = logging.getLogger(__name__)

mobile_payment_api = Namespace("mobile-payments", description="Mobile payment operations (Stripe + Firestore)")


mobile_payment_intent_model = mobile_payment_api.model(
    "MobilePaymentIntent",
    {
        "delivery_id": fields.Integer(required=True, description="Delivery ID"),
        "amount": fields.Integer(required=True, description="Payment amount in cents"),
        "tip_amount": fields.Integer(description="Tip amount in cents", default=0),
        "currency": fields.String(description="Currency code", default="usd"),
        "save_payment_method": fields.Boolean(default=False),
    },
)

mobile_payment_confirm_model = mobile_payment_api.model(
    "MobilePaymentConfirm",
    {
        "payment_intent_id": fields.String(required=True, description="Stripe payment intent ID"),
        "payment_method_id": fields.String(required=True, description="Stripe payment method ID"),
    },
)


@mobile_payment_api.route("/create-payment-intent")
class CreateMobilePaymentIntent(Resource):
    @mobile_payment_api.doc(security="Bearer Auth")
    @mobile_payment_api.expect(mobile_payment_intent_model)
    @firebase_customer_required
    def post(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        if stripe_payment_service is None:
            return {"success": False, "error": "Stripe is not configured (missing STRIPE_SECRET_KEY)"}, 503

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

        total_cents = int(amount_cents + tip_cents)
        metadata = {
            "delivery_id": str(delivery_id),
            "customer_id": str(customer_id),
            "customer_email": str(data.get("customer_email") or ""),
            "save_payment_method": "true" if save_payment_method else "false",
        }

        stripe_result = stripe_payment_service.create_payment_intent_simple(
            amount=total_cents,
            currency=currency,
            metadata=metadata,
        )
        if not stripe_result.get("success"):
            return {"success": False, "error": stripe_result.get("error") or "Stripe error"}, 502

        payment_intent_id = stripe_result.get("payment_intent_id")

        pay_doc = PaymentRepository().create(
            {
                "payment_type": "delivery_fee",
                "amount": total_cents / 100.0,
                "currency": currency.upper(),
                "status": "processing",
                "direction": "inbound",
                "payer_id": customer_id,
                "payer_type": "customer",
                "receiver_type": "platform",
                "payment_method": "credit_card",
                "delivery_id": delivery_id,
                "stripe_payment_intent_id": payment_intent_id,
                "payment_metadata": {
                    "tip_amount_cents": tip_cents,
                    "base_amount_cents": amount_cents,
                },
            }
        )

        payment_id = pay_doc.get("payment_id")

        # Update Stripe metadata with payment_id so the webhook handler can
        # look up the correct Firestore payment document on payment_intent.succeeded
        import stripe as _stripe
        try:
            _stripe.PaymentIntent.modify(
                payment_intent_id,
                metadata={**metadata, "payment_id": str(payment_id)},
            )
        except Exception as e:
            logger.warning(f"Could not update payment_intent metadata with payment_id: {e}")

        return {
            "success": True,
            "payment_intent_id": payment_intent_id,
            "client_secret": stripe_result.get("client_secret"),
            "amount": total_cents,
            "payment_id": payment_id,
            "delivery_id": delivery_id,
        }, 201


@mobile_payment_api.route("/confirm-payment")
class ConfirmMobilePayment(Resource):
    @mobile_payment_api.doc(security="Bearer Auth")
    @mobile_payment_api.expect(mobile_payment_confirm_model)
    @firebase_customer_required
    def post(self):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        if stripe_payment_service is None:
            return {"success": False, "error": "Stripe is not configured (missing STRIPE_SECRET_KEY)"}, 503

        customer_id = g.customer_id
        data = request.get_json() or {}
        payment_intent_id = data.get("payment_intent_id")
        payment_method_id = data.get("payment_method_id")
        if not payment_intent_id or not payment_method_id:
            return {"success": False, "error": "Missing payment_intent_id or payment_method_id"}, 400

        # Payment is already confirmed by Stripe SDK on mobile
        # Just verify the payment intent status and update our database
        payment_status = stripe_payment_service.get_payment_intent(payment_intent_id)
        if not payment_status.get("success"):
            return {"success": False, "error": payment_status.get("error") or "Failed to verify payment"}, 502

        # Check if payment was successful
        if payment_status.get("status") != "succeeded":
            return {"success": False, "error": f"Payment not successful. Status: {payment_status.get('status')}"}, 400

        # Find Firestore payment by payment_intent_id
        payment_id = data.get("payment_id")
        pay_repo = PaymentRepository()

        if payment_id:
            payment = pay_repo.get_by_id(str(payment_id))
        else:
            payment = None

        if payment and int(payment.get("payer_id") or 0) != int(customer_id):
            return {"success": False, "error": "Payment not found or access denied"}, 404

        if payment:
            pay_repo.update_fields(
                payment["payment_id"],
                {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "payment_method_id": str(payment_method_id),
                },
            )

            delivery_id = payment.get("delivery_id")
            if delivery_id is not None:
                delivery_repo = DeliveryRepository()
                delivery_repo.mark_payment_completed(delivery_id, actual_cost=payment.get("amount"))
                delivery_repo.update_fields(delivery_id, {"status": "confirmed", "payment_status": "paid"})

        return {
            "success": True,
            "payment_intent_id": payment_intent_id,
            "status": payment_status.get("status"),
            "amount": payment_status.get("amount"),
            "currency": payment_status.get("currency"),
        }, 200


@mobile_payment_api.route("/payment-status/<string:payment_intent_id>")
class MobilePaymentStatus(Resource):
    @mobile_payment_api.doc(security="Bearer Auth")
    def get(self, payment_intent_id: str):
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        if stripe_payment_service is None:
            return {"success": False, "error": "Stripe is not configured (missing STRIPE_SECRET_KEY)"}, 503

        status = stripe_payment_service.get_payment_intent(payment_intent_id)
        if not status.get("success"):
            return {"success": False, "error": status.get("error")}, 502
        return status, 200


@mobile_payment_api.route("/payment-methods")
class MobilePaymentMethods(Resource):
    @mobile_payment_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def get(self):
        """Get saved payment methods"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        if stripe_payment_service is None:
            return {"success": False, "error": "Stripe is not configured"}, 503

        try:
            customer_id = g.customer_id
            from repositories.customer_repository import CustomerRepository
            customer = CustomerRepository().get_by_id(customer_id)

            if not customer or not customer.get("stripe_customer_id"):
                return {"success": True, "payment_methods": [], "count": 0}, 200

            methods_result = stripe_payment_service.get_payment_methods(customer["stripe_customer_id"])
            if methods_result.get("success"):
                methods = methods_result.get("payment_methods", [])
                mobile_methods = []
                for method in methods:
                    card = method.get("card")
                    if card:
                        mobile_methods.append({
                            "id": method["id"],
                            "type": "card",
                            "brand": card["brand"],
                            "last4": card["last4"],
                            "exp_month": card["exp_month"],
                            "exp_year": card["exp_year"],
                            "display_name": f"{card['brand'].upper()} •••• {card['last4']}"
                        })
                return {"success": True, "payment_methods": mobile_methods, "count": len(mobile_methods)}, 200
            else:
                logger.error(f"get_payment_methods failed: {methods_result.get('error')}")
                return {"success": True, "payment_methods": [], "count": 0}, 200
        except Exception as e:
            logger.error(f"Payment methods retrieval failed: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

    @mobile_payment_api.doc(security="Bearer Auth")
    @firebase_customer_required
    def post(self):
        """Attach payment method"""
        if not USE_FIREBASE_DB:
            return {"error": "PostgreSQL mode disabled. Set USE_FIREBASE_DB=true."}, 503
        if stripe_payment_service is None:
            return {"success": False, "error": "Stripe is not configured"}, 503

        try:
            customer_id = g.customer_id
            data = request.get_json() or {}
            payment_method_id = data.get("payment_method_id")

            if not payment_method_id:
                return {"success": False, "error": "payment_method_id is required. Tokenize the card using the Stripe SDK on the client first."}, 400

            from repositories.customer_repository import CustomerRepository
            repo = CustomerRepository()
            customer = repo.get_by_id(customer_id)

            if not customer:
                return {"success": False, "error": "Customer not found"}, 404

            stripe_customer_id = customer.get("stripe_customer_id")
            if not stripe_customer_id:
                stripe_result = stripe_payment_service.create_customer(
                    email=customer["email"],
                    name=f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
                    phone=customer.get("phone_number"),
                    metadata={"customer_id": str(customer_id)}
                )
                if stripe_result.get("success"):
                    stripe_customer_id = stripe_result["customer_id"]
                    repo._doc_ref(customer_id).set({"stripe_customer_id": stripe_customer_id}, merge=True)
                else:
                    logger.error(f"Failed to create Stripe customer: {stripe_result.get('error')}")
                    return {"success": False, "error": f"Failed to create Stripe customer: {stripe_result.get('error')}"}, 500

            attach_result = stripe_payment_service.attach_payment_method(
                payment_method_id=payment_method_id,
                customer_id=stripe_customer_id
            )

            if not attach_result.get("success"):
                return {"success": False, "error": attach_result.get("error")}, 400

            return {"success": True, "payment_method_id": payment_method_id}, 201
        except Exception as e:
            logger.error(f"Payment method attachment failed: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}, 500

