"""Merge migration heads

Revision ID: 269d9a54584c
Revises: 5953cdb60f3e, add_stripe_account_to_drivers, create_location_history_table
Create Date: 2025-09-23 15:51:38.735481

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '269d9a54584c'
down_revision = ('5953cdb60f3e', 'add_stripe_account_to_drivers', 'create_location_history_table')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
