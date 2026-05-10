"""Add Stripe account ID to drivers table for payouts

Revision ID: add_stripe_account_to_drivers
Revises: create_payment_table
Create Date: 2024-01-20 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_stripe_account_to_drivers'
down_revision = 'create_payment_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add Stripe account ID to drivers table
    op.add_column('drivers', sa.Column('stripe_account_id', sa.String(255), nullable=True))
    
    # Create index for better performance
    op.create_index('idx_drivers_stripe_account_id', 'drivers', ['stripe_account_id'])

def downgrade():
    # Remove index
    op.drop_index('idx_drivers_stripe_account_id', 'drivers')
    
    # Remove Stripe account ID column
    op.drop_column('drivers', 'stripe_account_id')
