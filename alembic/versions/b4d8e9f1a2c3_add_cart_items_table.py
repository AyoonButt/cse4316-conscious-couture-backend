"""Add cart_items table

Revision ID: b4d8e9f1a2c3
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4d8e9f1a2c3'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('cart_items',
        sa.Column('cart_item_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('clothing_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['clothing_id'], ['clothing_items.clothing_id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('cart_item_id'),
        sa.UniqueConstraint('user_id', 'clothing_id', name='uq_cart_user_clothing'),
    )
    op.create_index('ix_cart_items_user_id', 'cart_items', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_cart_items_user_id', table_name='cart_items')
    op.drop_table('cart_items')