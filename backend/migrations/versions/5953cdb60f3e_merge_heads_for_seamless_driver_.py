"""merge heads for seamless driver features and delivery scheduling

Revision ID: 5953cdb60f3e
Revises: 05bf839f2b1b, add_seamless_driver_features
Create Date: 2025-08-14 14:51:28.764998

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5953cdb60f3e'
down_revision = ('05bf839f2b1b', 'add_seamless_driver_features')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
