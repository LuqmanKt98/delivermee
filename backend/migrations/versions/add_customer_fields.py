"""
Add first_name and last_name to customers, update notificationtype enum
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_customer_fields'
down_revision = '0aeec81a50cb'
branch_labels = None
depends_on = None

def upgrade():
    # Add first_name and last_name columns to customers
    op.add_column('customers', sa.Column('first_name', sa.String(length=50), nullable=True))
    op.add_column('customers', sa.Column('last_name', sa.String(length=50), nullable=True))

    # Update notificationtype enum (PostgreSQL-specific)
    # 1. Create new enum type
    new_enum = postgresql.ENUM('ride_assignment', 'ride_cancellation', 'ride_update', 'ride_reminder', name='notificationtype_new')
    new_enum.create(op.get_bind())
    # 2. Alter column to use new enum
    op.execute('ALTER TABLE notifications ALTER COLUMN type TYPE notificationtype_new USING type::text::notificationtype_new')
    # 3. Drop old enum type and rename new one
    op.execute('DROP TYPE notificationtype')
    op.execute('ALTER TYPE notificationtype_new RENAME TO notificationtype')

def downgrade():
    # Remove first_name and last_name columns from customers
    op.drop_column('customers', 'first_name')
    op.drop_column('customers', 'last_name')
    # Downgrade for enum is not implemented 