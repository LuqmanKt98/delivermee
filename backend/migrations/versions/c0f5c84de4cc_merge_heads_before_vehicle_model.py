"""merge heads before vehicle model

Revision ID: c0f5c84de4cc
Revises: 14e088523029, add_customer_fields
Create Date: 2025-07-10 16:35:36.160963

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0f5c84de4cc'
down_revision = ('14e088523029', 'add_customer_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
