#!/usr/bin/env python3
"""
Enhanced Stripe Payment Service for DeliverMe
Handles all Stripe payment operations including:
- Payment intents for customer payments
- Driver payouts and transfers
- Customer management
- Payment processing
- Refunds
- Webhook handling
"""

import stripe
import os
from datetime import datetime
from typing import Dict, Optional, List
from flask import current_app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StripePaymentService:
    """Enhanced Stripe payment service for DeliverMe with driver payout support"""
    
    def __init__(self):
        """Initialize Stripe with API key"""
        self.stripe = stripe
        self.stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        if not self.stripe.api_key:
            logger.error("STRIPE_SECRET_KEY not found in environment variables")
            logger.error("Available env vars: " + ", ".join([k for k in os.environ.keys() if 'STRIPE' in k]))
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
        
        # Log masked key for verification (security-safe)
        masked_key = f"{self.stripe.api_key[:7]}...{self.stripe.api_key[-4:]}"
        logger.info(f"Enhanced Stripe Payment Service initialized with key: {masked_key}")
        
        # Skip API verification during initialization to prevent startup timeout
        # The API key will be verified on first actual use
        logger.info("Stripe Payment Service ready (API key will be verified on first use)")
    
    def create_payment_intent(self, 
                             amount: int, 
                             currency: str = 'usd',
                             customer_id: Optional[str] = None,
                             metadata: Optional[Dict] = None) -> Dict:
        """
        Create a Stripe Payment Intent (customer is charged on platform account)
        
        Args:
            amount: Amount in cents (e.g., 1500 = $15.00)
            currency: Currency code (default: 'usd')
            customer_id: Stripe customer ID (optional)
            metadata: Additional metadata for the payment
            
        Returns:
            Dict containing payment intent details
        """
        try:
            payment_intent_data = {
                'amount': amount,
                'currency': currency,
                'automatic_payment_methods': {
                    'enabled': True,
                },
                'metadata': metadata or {}
            }
            
            if customer_id:
                payment_intent_data['customer'] = customer_id
            
            payment_intent = self.stripe.PaymentIntent.create(**payment_intent_data)
            
            logger.info(f"Payment intent created: {payment_intent.id}")
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'status': payment_intent.status,
                'customer_id': payment_intent.customer
            }
        
        except stripe.InvalidRequestError as e:
            # Common production issue: stored customer id was created in a different Stripe mode
            # (test vs live) or the customer was deleted, resulting in:
            # "No such customer: 'cus_...'"
            code = getattr(e, 'code', None)
            param = getattr(e, 'param', None)
            message = str(e)
            missing_customer = (
                (code == 'resource_missing' and param == 'customer')
                or ("No such customer" in message and "cus_" in message)
            )
            
            if customer_id and missing_customer:
                logger.warning(
                    f"Stripe customer missing ({customer_id}); attempting to recreate and retry payment intent"
                )
                
                md = metadata or {}
                email = md.get('customer_email') or md.get('email')
                
                # Prefer recreating the customer to preserve customer-based flows (saved payment methods, etc.)
                if email:
                    recreate = self.create_customer(
                        email=email,
                        metadata={
                            **(md or {}),
                            'recreated_due_to_missing_customer': 'true',
                            'previous_customer_id': customer_id,
                        }
                    )
                    
                    if recreate.get('success') and recreate.get('customer_id'):
                        new_customer_id = recreate['customer_id']
                        payment_intent_data = {
                            'amount': amount,
                            'currency': currency,
                            'automatic_payment_methods': {'enabled': True},
                            'metadata': md,
                            'customer': new_customer_id,
                        }
                        
                        payment_intent = self.stripe.PaymentIntent.create(**payment_intent_data)
                        logger.info(
                            f"Payment intent created after customer recreation: {payment_intent.id} (customer {new_customer_id})"
                        )
                        return {
                            'success': True,
                            'payment_intent_id': payment_intent.id,
                            'client_secret': payment_intent.client_secret,
                            'amount': payment_intent.amount,
                            'currency': payment_intent.currency,
                            'status': payment_intent.status,
                            'customer_id': payment_intent.customer,
                            'customer_recreated': True,
                            'previous_customer_id': customer_id,
                        }
                
                # Fallback: create payment intent without a customer (still allows charging)
                logger.warning("Retrying payment intent creation without a Stripe customer")
                payment_intent_data.pop('customer', None)
                payment_intent = self.stripe.PaymentIntent.create(**payment_intent_data)
                logger.info(f"Payment intent created without customer: {payment_intent.id}")
                return {
                    'success': True,
                    'payment_intent_id': payment_intent.id,
                    'client_secret': payment_intent.client_secret,
                    'amount': payment_intent.amount,
                    'currency': payment_intent.currency,
                    'status': payment_intent.status,
                    'customer_id': payment_intent.customer,
                    'customer_recreated': False,
                    'previous_customer_id': customer_id,
                }
            
            logger.error(f"Stripe invalid request creating payment intent: {message}")
            return {
                'success': False,
                'error': message,
                'error_type': 'invalid_request_error'
            }
        
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def create_payment_intent_simple(self, 
                                   amount: int, 
                                   currency: str = 'usd',
                                   metadata: Optional[Dict] = None) -> Dict:
        """
        Create a SIMPLIFIED Stripe Payment Intent - NO CUSTOMER DEPENDENCY
        This is optimized for mobile apps where customer creation is not required
        
        Args:
            amount: Amount in cents (e.g., 1500 = $15.00)
            currency: Currency code (default: 'usd')
            metadata: Additional metadata for the payment
            
        Returns:
            Dict containing payment intent details
        """
        try:
            payment_intent_data = {
                'amount': amount,
                'currency': currency,
                'automatic_payment_methods': {
                    'enabled': True,
                },
                'metadata': metadata or {}
            }
            
            payment_intent = self.stripe.PaymentIntent.create(**payment_intent_data)
            
            logger.info(f"Simple payment intent created: {payment_intent.id}")
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'status': payment_intent.status
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating simple payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating simple payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def process_delivery_payment_with_transfer(self,
                                            payment_intent_id: str,
                                            driver_stripe_account_id: str,
                                            driver_amount_cents: int,
                                            platform_fee_cents: int,
                                            currency: str = 'usd',
                                            delivery_id: Optional[str] = None) -> Dict:
        """
        Process a successful payment by transferring driver amount and keeping platform fee
        
        Args:
            payment_intent_id: Stripe payment intent ID
            driver_stripe_account_id: Driver's Stripe Connect account ID
            driver_amount_cents: Amount in cents to transfer to driver (fare + tip)
            platform_fee_cents: Platform fee amount in cents
            currency: Currency code (default: 'usd')
            delivery_id: Associated delivery ID
            
        Returns:
            Dict containing transfer details and payment summary
        """
        try:
            # Verify payment intent is successful
            payment_intent = self.stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status != 'succeeded':
                return {
                    'success': False,
                    'error': f'Payment intent {payment_intent_id} is not succeeded (status: {payment_intent.status})',
                    'error_type': 'payment_not_succeeded'
                }
            
            # Create transfer to driver
            transfer_metadata = {
                'delivery_id': delivery_id or '',
                'payment_intent_id': payment_intent_id,
                'platform_fee_cents': str(platform_fee_cents),
                'transfer_type': 'driver_payout'
            }
            
            transfer_result = self.create_driver_payout(
                amount=driver_amount_cents,
                currency=currency,
                driver_stripe_account_id=driver_stripe_account_id,
                delivery_id=delivery_id,
                metadata=transfer_metadata
            )
            
            if not transfer_result['success']:
                return transfer_result
            
            logger.info(f"Payment processed successfully: {payment_intent_id} -> Transfer: {transfer_result['transfer_id']}")
            
            return {
                'success': True,
                'payment_intent_id': payment_intent_id,
                'transfer_id': transfer_result['transfer_id'],
                'driver_amount_cents': driver_amount_cents,
                'platform_fee_cents': platform_fee_cents,
                'total_amount_cents': driver_amount_cents + platform_fee_cents,
                'currency': currency,
                'payment_status': payment_intent.status,
                'transfer_status': transfer_result['status']
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error processing delivery payment: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error processing delivery payment: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }

    def create_driver_payout(self, 
                            amount: int,
                            currency: str,
                            driver_stripe_account_id: str,
                            delivery_id: Optional[str] = None,
                            metadata: Optional[Dict] = None) -> Dict:
        """
        Create a payout to a driver's Stripe account
        
        Args:
            amount: Amount in cents to transfer to driver
            currency: Currency code (default: 'usd')
            driver_stripe_account_id: Driver's Stripe Connect account ID
            delivery_id: Associated delivery ID
            metadata: Additional metadata
            
        Returns:
            Dict containing transfer details
        """
        try:
            transfer_data = {
                'amount': amount,
                'currency': currency,
                'destination': driver_stripe_account_id,
                'metadata': metadata or {}
            }
            
            if delivery_id:
                transfer_data['metadata']['delivery_id'] = delivery_id
            
            transfer = self.stripe.Transfer.create(**transfer_data)
            
            logger.info(f"Driver payout created: {transfer.id} for amount {amount} {currency}")
            
            return {
                'success': True,
                'transfer_id': transfer.id,
                'amount': transfer.amount,
                'currency': transfer.currency,
                'status': transfer.status,
                'destination': transfer.destination
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating driver payout: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating driver payout: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def create_driver_account(self, 
                             email: str,
                             country: str = 'US',
                             business_type: str = 'individual',
                             metadata: Optional[Dict] = None) -> Dict:
        """
        Create a Stripe Connect account for a driver
        
        Args:
            email: Driver's email address
            country: Country code (default: 'US')
            business_type: Business type (default: 'individual')
            metadata: Additional metadata
            
        Returns:
            Dict containing account details
        """
        try:
            account_data = {
                'type': 'express',
                'country': country,
                'email': email,
                'business_type': business_type,
                'metadata': metadata or {}
            }
            
            account = self.stripe.Account.create(**account_data)
            
            logger.info(f"Driver Stripe account created: {account.id}")
            
            return {
                'success': True,
                'account_id': account.id,
                'email': account.email,
                'country': account.country,
                'business_type': account.business_type
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating driver account: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating driver account: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def get_driver_account(self, account_id: str) -> Dict:
        """
        Retrieve a driver's Stripe Connect account
        
        Args:
            account_id: Stripe account ID
            
        Returns:
            Dict containing account details
        """
        try:
            account = self.stripe.Account.retrieve(account_id)
            
            return {
                'success': True,
                'account_id': account.id,
                'email': account.email,
                'country': account.country,
                'business_type': account.business_type,
                'charges_enabled': account.charges_enabled,
                'payouts_enabled': account.payouts_enabled,
                'details_submitted': account.details_submitted
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error retrieving driver account: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error retrieving driver account: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def create_customer(self, 
                       email: str, 
                       name: Optional[str] = None,
                       phone: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict:
        """
        Create a Stripe customer
        
        Args:
            email: Customer email
            name: Customer name (optional)
            phone: Customer phone (optional)
            metadata: Additional metadata
            
        Returns:
            Dict containing customer details
        """
        try:
            # Validate email
            if not email or not isinstance(email, str) or '@' not in email:
                logger.error(f"Invalid email provided: {email}")
                return {
                    'success': False,
                    'error': 'Invalid email address',
                    'error_type': 'validation_error'
                }
            
            # Log API key status (first and last 4 chars only for security)
            api_key = self.stripe.api_key
            if api_key:
                masked_key = f"{api_key[:7]}...{api_key[-4:]}"
                logger.info(f"Using Stripe API key: {masked_key}")
            else:
                logger.error("Stripe API key is None!")
                return {
                    'success': False,
                    'error': 'Stripe API key not configured',
                    'error_type': 'config_error'
                }
            
            customer_data = {
                'email': email,
                'metadata': metadata or {}
            }
            
            if name:
                customer_data['name'] = name
            if phone:
                customer_data['phone'] = phone
            
            logger.info(f"Creating Stripe customer with email: {email}")
            customer = self.stripe.Customer.create(**customer_data)
            
            logger.info(f"Customer created successfully: {customer.id}")
            
            return {
                'success': True,
                'customer_id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
            
        except stripe.AuthenticationError as e:
            logger.error(f"Stripe authentication error: {str(e)} - Check your API key")
            return {
                'success': False,
                'error': f'Stripe authentication failed: {str(e)}',
                'error_type': 'authentication_error'
            }
        except stripe.InvalidRequestError as e:
            logger.error(f"Stripe invalid request error: {str(e)}")
            return {
                'success': False,
                'error': f'Invalid request to Stripe: {str(e)}',
                'error_type': 'invalid_request_error'
            }
        except stripe.APIConnectionError as e:
            logger.error(f"Stripe API connection error: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to connect to Stripe: {str(e)}',
                'error_type': 'connection_error'
            }
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating customer: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def get_customer(self, customer_id: str) -> Dict:
        """
        Retrieve a Stripe customer
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Dict containing customer details
        """
        try:
            customer = self.stripe.Customer.retrieve(customer_id)
            
            return {
                'success': True,
                'customer_id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'phone': customer.phone,
                'created': customer.created
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error retrieving customer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error retrieving customer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def update_customer(self, 
                       customer_id: str, 
                       email: Optional[str] = None,
                       name: Optional[str] = None,
                       phone: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict:
        """
        Update a Stripe customer
        
        Args:
            customer_id: Stripe customer ID
            email: New email (optional)
            name: New name (optional)
            phone: New phone (optional)
            metadata: New metadata (optional)
            
        Returns:
            Dict containing updated customer details
        """
        try:
            update_data = {}
            
            if email is not None:
                update_data['email'] = email
            if name is not None:
                update_data['name'] = name
            if phone is not None:
                update_data['phone'] = phone
            if metadata is not None:
                update_data['metadata'] = metadata
            
            customer = self.stripe.Customer.modify(customer_id, **update_data)
            
            logger.info(f"Customer updated: {customer.id}")
            
            return {
                'success': True,
                'customer_id': customer.id,
                'email': customer.email,
                'name': customer.name,
                'phone': customer.phone
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error updating customer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error updating customer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def get_payment_intent(self, payment_intent_id: str) -> Dict:
        """
        Retrieve a payment intent
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Dict containing payment intent details
        """
        try:
            payment_intent = self.stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'status': payment_intent.status,
                'client_secret': payment_intent.client_secret,
                'customer_id': payment_intent.customer,
                'created': payment_intent.created,
                'metadata': payment_intent.metadata,
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error retrieving payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def confirm_payment_intent(self, payment_intent_id: str, payment_method_id: str) -> Dict:
        """
        Confirm a payment intent with a payment method
        
        Args:
            payment_intent_id: Stripe payment intent ID
            payment_method_id: Stripe payment method ID
            
        Returns:
            Dict containing confirmation result
        """
        try:
            payment_intent = self.stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )
            
            logger.info(f"Payment intent confirmed: {payment_intent.id}")
            
            return {
                'success': True,
                'payment_intent_id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error confirming payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error confirming payment intent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def create_refund(self, 
                      payment_intent_id: str, 
                      amount: Optional[int] = None,
                      reason: Optional[str] = None) -> Dict:
        """
        Create a refund for a payment
        
        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Refund amount in cents (optional, defaults to full amount)
            reason: Refund reason (optional)
            
        Returns:
            Dict containing refund details
        """
        try:
            refund_data = {
                'payment_intent': payment_intent_id
            }
            
            if amount:
                refund_data['amount'] = amount
            if reason:
                refund_data['reason'] = reason
            
            refund = self.stripe.Refund.create(**refund_data)
            
            logger.info(f"Refund created: {refund.id}")
            
            return {
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount,
                'currency': refund.currency,
                'status': refund.status,
                'reason': refund.reason
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating refund: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating refund: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def get_payment_methods(self, customer_id: str) -> Dict:
        try:
            payment_methods = self.stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )
            
            methods = []
            for method in payment_methods.data:
                card = getattr(method, 'card', None)
                if card:
                    methods.append({
                        'id': method.id,
                        'type': method.type,
                        'card': {
                            'brand': card.brand,
                            'last4': card.last4,
                            'exp_month': card.exp_month,
                            'exp_year': card.exp_year
                        }
                    })
            
            return {
                'success': True,
                'payment_methods': methods,
                'count': len(methods)
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error getting payment methods: {str(e)}")
            return {'success': False, 'error': str(e), 'error_type': 'stripe_error'}
        except Exception as e:
            logger.error(f"Unexpected error getting payment methods: {str(e)}")
            return {'success': False, 'error': str(e), 'error_type': 'unexpected_error'}
    
    def attach_payment_method(self, payment_method_id: str, customer_id: str) -> Dict:
        """
        Attach a payment method to a customer
        
        Args:
            payment_method_id: Stripe payment method ID
            customer_id: Stripe customer ID
            
        Returns:
            Dict containing attachment result
        """
        try:
            payment_method = self.stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            logger.info(f"Payment method attached: {payment_method.id}")
            
            return {
                'success': True,
                'payment_method_id': payment_method.id,
                'customer_id': payment_method.customer
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error attaching payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error attaching payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def create_payment_method_from_card(self, 
                                       card_number: str,
                                       exp_month: int,
                                       exp_year: int,
                                       cvc: str,
                                       cardholder_name: Optional[str] = None) -> Dict:
        """
        Create a payment method from card details (server-side)
        
        Args:
            card_number: Card number
            exp_month: Expiration month
            exp_year: Expiration year
            cvc: Card CVC
            cardholder_name: Cardholder name (optional)
            
        Returns:
            Dict containing payment method details
        """
        try:
            payment_method_data = {
                'type': 'card',
                'card': {
                    'number': card_number,
                    'exp_month': exp_month,
                    'exp_year': exp_year,
                    'cvc': cvc
                }
            }
            
            if cardholder_name:
                payment_method_data['billing_details'] = {'name': cardholder_name}
            
            payment_method = self.stripe.PaymentMethod.create(**payment_method_data)
            
            logger.info(f"Payment method created from card: {payment_method.id}")
            
            return {
                'success': True,
                'payment_method_id': payment_method.id,
                'card': {
                    'brand': payment_method.card.brand,
                    'last4': payment_method.card.last4,
                    'exp_month': payment_method.card.exp_month,
                    'exp_year': payment_method.card.exp_year
                }
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error creating payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def detach_payment_method(self, payment_method_id: str) -> Dict:
        """
        Detach a payment method from a customer
        
        Args:
            payment_method_id: Stripe payment method ID
            
        Returns:
            Dict containing detachment result
        """
        try:
            payment_method = self.stripe.PaymentMethod.detach(payment_method_id)
            
            logger.info(f"Payment method detached: {payment_method.id}")
            
            return {
                'success': True,
                'payment_method_id': payment_method.id
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error detaching payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error detaching payment method: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }
    
    def get_transfer(self, transfer_id: str) -> Dict:
        """
        Retrieve a transfer (driver payout)
        
        Args:
            transfer_id: Stripe transfer ID
            
        Returns:
            Dict containing transfer details
        """
        try:
            transfer = self.stripe.Transfer.retrieve(transfer_id)
            
            return {
                'success': True,
                'transfer_id': transfer.id,
                'amount': transfer.amount,
                'currency': transfer.currency,
                'status': transfer.status,
                'destination': transfer.destination,
                'created': transfer.created
            }
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error retrieving transfer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'stripe_error'
            }
        except Exception as e:
            logger.error(f"Unexpected error retrieving transfer: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'unexpected_error'
            }

# Global instance (lazy-safe):
# In Firebase/Firestore mode we still want the backend to boot even if Stripe isn't configured.
try:
    stripe_payment_service = StripePaymentService()
except Exception as e:
    logger.error(f"StripePaymentService not initialized: {str(e)}")
    stripe_payment_service = None

