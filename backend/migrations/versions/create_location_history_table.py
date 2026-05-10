"""Create location history table for live tracking

Revision ID: create_location_history_table
Revises: 
Create Date: 2025-08-14 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_location_history_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create location_history table"""
    op.create_table('location_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_type', sa.String(length=20), nullable=False),  # 'driver' or 'customer'
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),  # Speed in m/s
        sa.Column('heading', sa.Float(), nullable=True),  # Heading in degrees
        sa.Column('altitude', sa.Float(), nullable=True),  # Altitude in meters
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_location_history_user', 'location_history', ['user_id', 'user_type'])
    op.create_index('idx_location_history_timestamp', 'location_history', ['timestamp'])
    op.create_index('idx_location_history_coordinates', 'location_history', ['latitude', 'longitude'])

def downgrade():
    """Drop location_history table"""
    op.drop_index('idx_location_history_coordinates', 'location_history')
    op.drop_index('idx_location_history_timestamp', 'location_history')
    op.drop_index('idx_location_history_user', 'location_history')
    op.drop_table('location_history')

