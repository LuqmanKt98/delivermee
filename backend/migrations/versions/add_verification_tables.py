"""Add verification tables

Revision ID: add_verification_tables
Revises: ac58b5c79924
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_verification_tables'
down_revision = 'ac58b5c79924'
branch_labels = None
depends_on = None

def upgrade():
    # Create verification_codes table
    op.create_table('verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('verification_type', sa.String(length=20), nullable=False),
        sa.Column('user_type', sa.String(length=20), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create password_reset_tokens table
    op.create_table('password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('user_type', sa.String(length=20), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

def downgrade():
    op.drop_table('password_reset_tokens')
    op.drop_table('verification_codes') 