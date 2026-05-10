"""Create Payment table for robust payment handling

Revision ID: create_payment_table
Revises: add_payment_fields
Create Date: 2024-01-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_payment_table'
down_revision = 'add_payment_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Create PaymentType enum
    payment_type_enum = postgresql.ENUM('delivery_fee', 'driver_payout', 'platform_fee', 'tip', 'refund', 'adjustment', name='paymenttype')
    payment_type_enum.create(op.get_bind())
    
    # Create PaymentStatus enum
    payment_status_enum = postgresql.ENUM('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', 'partially_refunded', 'disputed', 'expired', name='paymentstatus')
    payment_status_enum.create(op.get_bind())
    
    # Create PaymentMethod enum
    payment_method_enum = postgresql.ENUM('credit_card', 'debit_card', 'bank_transfer', 'digital_wallet', 'cash', 'platform_credit', name='paymentmethod')
    payment_method_enum.create(op.get_bind())
    
    # Create PaymentDirection enum
    payment_direction_enum = postgresql.ENUM('inbound', 'outbound', name='paymentdirection')
    payment_direction_enum.create(op.get_bind())
    
    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.String(length=50), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('payment_type', payment_type_enum, nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', payment_status_enum, nullable=True),
        sa.Column('direction', payment_direction_enum, nullable=False),
        sa.Column('payer_id', sa.Integer(), nullable=False),
        sa.Column('payer_type', sa.String(length=20), nullable=True),
        sa.Column('payer_stripe_id', sa.String(length=255), nullable=True),
        sa.Column('receiver_id', sa.Integer(), nullable=True),
        sa.Column('receiver_type', sa.String(length=20), nullable=True),
        sa.Column('receiver_stripe_id', sa.String(length=255), nullable=True),
        sa.Column('payment_method', payment_method_enum, nullable=False),
        sa.Column('payment_method_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_charge_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_transfer_id', sa.String(length=255), nullable=True),
        sa.Column('delivery_id', sa.Integer(), nullable=True),
        sa.Column('driver_id', sa.Integer(), nullable=True),
        sa.Column('base_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('platform_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('payment_processing_fee', sa.Numeric(precision=10, scale=2), nullable=True),  # Payment processing fee (3%)
        sa.Column('driver_payout', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tip_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('insurance_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('payment_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['delivery_id'], ['deliveries.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('idx_payments_payment_id', 'payments', ['payment_id'])
    op.create_index('idx_payments_transaction_id', 'payments', ['transaction_id'])
    op.create_index('idx_payments_payer_id', 'payments', ['payer_id'])
    op.create_index('idx_payments_receiver_id', 'payments', ['receiver_id'])
    op.create_index('idx_payments_delivery_id', 'payments', ['delivery_id'])
    op.create_index('idx_payments_driver_id', 'payments', ['driver_id'])
    op.create_index('idx_payments_status', 'payments', ['status'])
    op.create_index('idx_payments_payment_type', 'payments', ['payment_type'])
    op.create_index('idx_payments_created_at', 'payments', ['created_at'])
    op.create_index('idx_payments_stripe_payment_intent_id', 'payments', ['stripe_payment_intent_id'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_payments_stripe_payment_intent_id', 'payments')
    op.drop_index('idx_payments_created_at', 'payments')
    op.drop_index('idx_payments_payment_type', 'payments')
    op.drop_index('idx_payments_status', 'payments')
    op.drop_index('idx_payments_driver_id', 'payments')
    op.drop_index('idx_payments_delivery_id', 'payments')
    op.drop_index('idx_payments_receiver_id', 'payments')
    op.drop_index('idx_payments_payer_id', 'payments')
    op.drop_index('idx_payments_transaction_id', 'payments')
    op.drop_index('idx_payments_payment_id', 'payments')
    
    # Drop payments table
    op.drop_table('payments')
    
    # Drop enums
    op.execute('DROP TYPE paymentdirection')
    op.execute('DROP TYPE paymentmethod')
    op.execute('DROP TYPE paymentstatus')
    op.execute('DROP TYPE paymenttype')
