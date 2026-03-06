"""Add sale_id to payments table

Revision ID: a1b2c3d4e5f6
Revises: e2c0c88b7df2
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e2c0c88b7df2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sale_id column to payments table
    op.add_column('payments', sa.Column('sale_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_payments_sale_id'), 'payments', ['sale_id'], unique=False)
    op.create_foreign_key(
        'fk_payments_sale_id',
        'payments',
        'sales',
        ['sale_id'],
        ['sale_id']
    )

    # Make transaction_id nullable (it's now deprecated in favor of sale_id)
    op.alter_column('payments', 'transaction_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Make transaction_id non-nullable again
    op.alter_column('payments', 'transaction_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    op.drop_constraint('fk_payments_sale_id', 'payments', type_='foreignkey')
    op.drop_index(op.f('ix_payments_sale_id'), table_name='payments')
    op.drop_column('payments', 'sale_id')
