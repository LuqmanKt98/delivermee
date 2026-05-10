"""Add driver document and vehicle fields

Revision ID: add_driver_document_fields
Revises: add_verification_tables
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_driver_document_fields'
down_revision = 'add_verification_tables'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to drivers table
    op.add_column('drivers', sa.Column('driving_license_image', sa.String(500), nullable=True))
    op.add_column('drivers', sa.Column('id_card_image', sa.String(500), nullable=True))
    op.add_column('drivers', sa.Column('vehicle_year', sa.String(4), nullable=False, server_default='2024'))
    op.add_column('drivers', sa.Column('is_available', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('drivers', sa.Column('has_payment_method', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    # Remove the added columns
    op.drop_column('drivers', 'has_payment_method')
    op.drop_column('drivers', 'is_available')
    op.drop_column('drivers', 'vehicle_year')
    op.drop_column('drivers', 'id_card_image')
    op.drop_column('drivers', 'driving_license_image') 