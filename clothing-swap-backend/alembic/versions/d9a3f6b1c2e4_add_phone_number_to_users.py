"""Add phone_number to users

Revision ID: d9a3f6b1c2e4
Revises: c7f1d9e2a4b6
Create Date: 2026-04-19 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9a3f6b1c2e4'
down_revision = 'c7f1d9e2a4b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'phone_number')
