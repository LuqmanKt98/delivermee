"""add_missing_delivery_status_values

Revision ID: 7b93a007270b
Revises: 269d9a54584c
Create Date: 2025-09-28 12:36:29.986500

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7b93a007270b'
down_revision = '269d9a54584c'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing values to the deliverystatus enum using ALTER TYPE
    # This is safer than recreating the enum
    
    # Add the missing enum values one by one
    op.execute("ALTER TYPE deliverystatus ADD VALUE 'PENDING'")
    op.execute("ALTER TYPE deliverystatus ADD VALUE 'PAID'")
    op.execute("ALTER TYPE deliverystatus ADD VALUE 'IN_PROGRESS'")
    op.execute("ALTER TYPE deliverystatus ADD VALUE 'COMPLETED'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This migration cannot be easily reverted
    pass
