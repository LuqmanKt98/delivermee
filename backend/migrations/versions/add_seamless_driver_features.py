"""Add seamless driver features

Revision ID: add_seamless_driver_features
Revises: d3842d3656bf
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_seamless_driver_features'
down_revision = 'd3842d3656bf'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to drivers table for intelligent features
    op.add_column('drivers', sa.Column('total_deliveries', sa.Integer(), nullable=True, default=0))
    op.add_column('drivers', sa.Column('intelligent_mode_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('drivers', sa.Column('auto_accept_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('drivers', sa.Column('max_delivery_radius', sa.Float(), nullable=True, default=15.0))
    op.add_column('drivers', sa.Column('preferred_delivery_types', sa.JSON(), nullable=True))
    op.add_column('drivers', sa.Column('batch_deliveries_enabled', sa.Boolean(), nullable=True, default=True))
    
    # Update existing drivers with default values
    op.execute("UPDATE drivers SET total_deliveries = 0 WHERE total_deliveries IS NULL")
    op.execute("UPDATE drivers SET intelligent_mode_enabled = false WHERE intelligent_mode_enabled IS NULL")
    op.execute("UPDATE drivers SET auto_accept_enabled = false WHERE auto_accept_enabled IS NULL")
    op.execute("UPDATE drivers SET max_delivery_radius = 15.0 WHERE max_delivery_radius IS NULL")
    op.execute("UPDATE drivers SET preferred_delivery_types = '[\"standard\"]' WHERE preferred_delivery_types IS NULL")
    op.execute("UPDATE drivers SET batch_deliveries_enabled = true WHERE batch_deliveries_enabled IS NULL")
    
    # Add notification system enhancements to notifications table
    # Add priority column for enhanced notifications
    op.add_column('notifications', sa.Column('priority', sa.String(20), nullable=True, default='normal'))
    op.add_column('notifications', sa.Column('metadata', sa.JSON(), nullable=True))
    
    # Update existing notifications with default priority
    op.execute("UPDATE notifications SET priority = 'normal' WHERE priority IS NULL")


def downgrade():
    # Remove added columns from drivers table
    op.drop_column('drivers', 'batch_deliveries_enabled')
    op.drop_column('drivers', 'preferred_delivery_types')
    op.drop_column('drivers', 'max_delivery_radius')
    op.drop_column('drivers', 'auto_accept_enabled')
    op.drop_column('drivers', 'intelligent_mode_enabled')
    op.drop_column('drivers', 'total_deliveries')
    
    # Remove notification enhancements
    op.drop_column('notifications', 'metadata')
    op.drop_column('notifications', 'priority')
