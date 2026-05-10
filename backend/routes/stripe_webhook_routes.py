from flask import request
from flask_restx import Namespace, Resource
import stripe
import os
from settings import USE_FIREBASE_DB
from repositories.payment_repository import PaymentRepository
from repositories.delivery_repository import DeliveryRepository

stripe_webhook_api = Namespace('stripe-webhooks', description='Stripe webhook handlers')

# Get Stripe keys from environment
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

@stripe_webhook_api.route('/payment')
class StripePaymentWebhook(Resource):
    def post(self):
        """Handle Stripe payment webhooks"""
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')

        if not STRIPE_WEBHOOK_SECRET:
            print('⚠️ STRIPE_WEBHOOK_SECRET not configured')
            return {'error': 'Webhook secret not configured'}, 500

        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            print(f'✅ Webhook verified: {event["type"]}')
        except ValueError as e:
            # Invalid payload
            print(f'❌ Invalid payload: {e}')
            return {'error': 'Invalid payload'}, 400
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            print(f'❌ Invalid signature: {e}')
            return {'error': 'Invalid signature'}, 400

        # Handle the event
        event_type = event['type']
        event_data = event['data']['object']

        print(f'📨 Processing webhook event: {event_type}')
        print(f'📨 Event ID: {event["id"]}')

        if not USE_FIREBASE_DB:
            print('⚠️ Firebase DB not enabled, skipping webhook processing')
            return {'status': 'success', 'message': 'Webhook received but not processed'}, 200

        # Payment Intent Events
        if event_type == 'payment_intent.succeeded':
            handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            handle_payment_intent_failed(event_data)
        elif event_type == 'payment_intent.canceled':
            handle_payment_intent_canceled(event_data)
        
        # Charge Events
        elif event_type == 'charge.succeeded':
            handle_charge_succeeded(event_data)
        elif event_type == 'charge.failed':
            handle_charge_failed(event_data)
        elif event_type == 'charge.refunded':
            handle_charge_refunded(event_data)
        
        # Refund Events
        elif event_type == 'refund.created':
            handle_refund_created(event_data)
        elif event_type == 'refund.updated':
            handle_refund_updated(event_data)
        
        # Customer Events
        elif event_type == 'customer.created':
            handle_customer_created(event_data)
        elif event_type == 'customer.updated':
            handle_customer_updated(event_data)
        elif event_type == 'customer.deleted':
            handle_customer_deleted(event_data)
        
        else:
            print(f'ℹ️ Unhandled event type: {event_type}')

        return {'status': 'success'}, 200


def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent"""
    print(f'✅ Payment Intent Succeeded: {payment_intent["id"]}')
    print(f'💰 Amount: {payment_intent["amount"]} {payment_intent["currency"]}')
    
    try:
        payment_repo = PaymentRepository()
        delivery_repo = DeliveryRepository()
        
        # Get payment by Stripe payment intent ID
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        delivery_id = payment_intent.get('metadata', {}).get('delivery_id')
        
        if payment_id:
            # Update payment status
            payment_repo.update_fields(int(payment_id), {
                'status': 'completed',
                'stripe_payment_intent_id': payment_intent['id'],
                'payment_method': payment_intent.get('payment_method'),
            })
            print(f'✅ Updated payment {payment_id} to completed')
        
        if delivery_id:
            # Mark delivery payment as completed
            delivery_repo.mark_payment_completed(
                int(delivery_id),
                actual_cost=payment_intent['amount'] / 100  # Convert cents to dollars
            )
            # Update delivery status to confirmed
            delivery_repo.update_fields(int(delivery_id), {'status': 'confirmed'})
            print(f'✅ Marked delivery {delivery_id} payment as completed and status as confirmed')
            
    except Exception as e:
        print(f'❌ Error handling payment_intent.succeeded: {e}')


def handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent"""
    print(f'❌ Payment Intent Failed: {payment_intent["id"]}')
    
    try:
        payment_repo = PaymentRepository()
        
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        if payment_id:
            payment_repo.update_fields(int(payment_id), {
                'status': 'failed',
                'stripe_payment_intent_id': payment_intent['id'],
                'failure_reason': payment_intent.get('last_payment_error', {}).get('message'),
            })
            print(f'✅ Updated payment {payment_id} to failed')
            
    except Exception as e:
        print(f'❌ Error handling payment_intent.failed: {e}')


def handle_payment_intent_canceled(payment_intent):
    """Handle canceled payment intent"""
    print(f'⚠️ Payment Intent Canceled: {payment_intent["id"]}')
    
    try:
        payment_repo = PaymentRepository()
        
        payment_id = payment_intent.get('metadata', {}).get('payment_id')
        if payment_id:
            payment_repo.update_fields(int(payment_id), {
                'status': 'cancelled',
                'stripe_payment_intent_id': payment_intent['id'],
            })
            print(f'✅ Updated payment {payment_id} to cancelled')
            
    except Exception as e:
        print(f'❌ Error handling payment_intent.canceled: {e}')


def handle_charge_succeeded(charge):
    """Handle successful charge"""
    print(f'✅ Charge Succeeded: {charge["id"]}')
    print(f'💰 Amount: {charge["amount"]} {charge["currency"]}')


def handle_charge_failed(charge):
    """Handle failed charge"""
    print(f'❌ Charge Failed: {charge["id"]}')
    print(f'❌ Failure message: {charge.get("failure_message")}')


def handle_charge_refunded(charge):
    """Handle refunded charge"""
    print(f'💸 Charge Refunded: {charge["id"]}')
    print(f'💰 Refund amount: {charge["amount_refunded"]} {charge["currency"]}')
    
    try:
        payment_repo = PaymentRepository()
        
        payment_intent_id = charge.get('payment_intent')
        if payment_intent_id:
            # Find payment by payment intent ID and update status
            # Note: You may need to add a method to find payment by stripe_payment_intent_id
            print(f'ℹ️ Refund for payment intent: {payment_intent_id}')
            
    except Exception as e:
        print(f'❌ Error handling charge.refunded: {e}')


def handle_refund_created(refund):
    """Handle refund created"""
    print(f'💸 Refund Created: {refund["id"]}')
    print(f'💰 Amount: {refund["amount"]} {refund["currency"]}')


def handle_refund_updated(refund):
    """Handle refund updated"""
    print(f'💸 Refund Updated: {refund["id"]}')
    print(f'📊 Status: {refund["status"]}')


def handle_customer_created(customer):
    """Handle customer created"""
    print(f'👤 Customer Created: {customer["id"]}')
    print(f'📧 Email: {customer.get("email")}')


def handle_customer_updated(customer):
    """Handle customer updated"""
    print(f'👤 Customer Updated: {customer["id"]}')


def handle_customer_deleted(customer):
    """Handle customer deleted"""
    print(f'👤 Customer Deleted: {customer["id"]}')
