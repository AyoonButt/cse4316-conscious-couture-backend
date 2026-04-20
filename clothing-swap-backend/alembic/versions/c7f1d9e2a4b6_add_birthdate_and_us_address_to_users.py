"""Add birth date and US address fields to users

Revision ID: c7f1d9e2a4b6
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f1d9e2a4b6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('birth_date', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('address_line2', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('state', sa.String(length=2), nullable=True))
    op.add_column('users', sa.Column('postal_code', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('country', sa.String(length=2), nullable=True))

    # Default existing and new records to USA unless explicitly set otherwise.
    op.execute("UPDATE users SET country = 'US' WHERE country IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'country')
    op.drop_column('users', 'postal_code')
    op.drop_column('users', 'state')
    op.drop_column('users', 'city')
    op.drop_column('users', 'address_line2')
    op.drop_column('users', 'address_line1')
    op.drop_column('users', 'birth_date')
