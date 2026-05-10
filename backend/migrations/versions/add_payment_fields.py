"""Add payment fields for Stripe integration

Revision ID: add_payment_fields
Revises: 34cb666f5c18
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_payment_fields'
down_revision = '34cb666f5c18'
branch_labels = None
depends_on = None

def upgrade():
    # Add payment fields to deliveries table
    op.add_column('deliveries', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('deliveries', sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True))
    op.add_column('deliveries', sa.Column('payment_amount', sa.Float(), nullable=True))
    op.add_column('deliveries', sa.Column('payment_currency', sa.String(10), nullable=True))
    op.add_column('deliveries', sa.Column('payment_status', sa.String(50), nullable=True, default='pending'))
    op.add_column('deliveries', sa.Column('payment_created_at', sa.DateTime(), nullable=True))
    op.add_column('deliveries', sa.Column('payment_completed_at', sa.DateTime(), nullable=True))
    op.add_column('deliveries', sa.Column('refund_amount', sa.Float(), nullable=True))
    op.add_column('deliveries', sa.Column('refund_reason', sa.String(255), nullable=True))
    op.add_column('deliveries', sa.Column('refunded_at', sa.DateTime(), nullable=True))
    
    # Add Stripe customer ID to customers table
    op.add_column('customers', sa.Column('stripe_customer_id', sa.String(255), nullable=True, unique=True))
    
    # Create indexes for better performance
    op.create_index('idx_deliveries_stripe_customer_id', 'deliveries', ['stripe_customer_id'])
    op.create_index('idx_deliveries_stripe_payment_intent_id', 'deliveries', ['stripe_payment_intent_id'])
    op.create_index('idx_deliveries_payment_status', 'deliveries', ['payment_status'])
    op.create_index('idx_customers_stripe_customer_id', 'customers', ['stripe_customer_id'])

def downgrade():
    # Remove indexes
    op.drop_index('idx_customers_stripe_customer_id', 'customers')
    op.drop_index('idx_deliveries_payment_status', 'deliveries')
    op.drop_index('idx_deliveries_stripe_payment_intent_id', 'deliveries')
    op.drop_index('idx_deliveries_stripe_customer_id', 'deliveries')
    
    # Remove payment fields from deliveries table
    op.drop_column('deliveries', 'refunded_at')
    op.drop_column('deliveries', 'refund_reason')
    op.drop_column('deliveries', 'refund_amount')
    op.drop_column('deliveries', 'payment_completed_at')
    op.drop_column('deliveries', 'payment_created_at')
    op.drop_column('deliveries', 'payment_status')
    op.drop_column('deliveries', 'payment_currency')
    op.drop_column('deliveries', 'payment_amount')
    op.drop_column('deliveries', 'stripe_payment_intent_id')
    op.drop_column('deliveries', 'stripe_customer_id')
    
    # Remove Stripe customer ID from customers table
    op.drop_column('customers', 'stripe_customer_id')

