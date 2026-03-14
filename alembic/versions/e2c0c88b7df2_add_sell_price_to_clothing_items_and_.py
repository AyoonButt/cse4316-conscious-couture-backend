"""Add sell_price to clothing_items and sales table

Revision ID: e2c0c88b7df2
Revises: f9c07f51ef7f
Create Date: 2026-02-09 03:52:41.673984

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2c0c88b7df2'
down_revision = 'f9c07f51ef7f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the sales table
    op.create_table('sales',
    sa.Column('sale_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('seller_id', sa.Integer(), nullable=False),
    sa.Column('buyer_id', sa.Integer(), nullable=False),
    sa.Column('clothing_id', sa.Integer(), nullable=False),
    sa.Column('sale_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('original_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('shipping_address', sa.Text(), nullable=True),
    sa.Column('tracking_number', sa.String(length=100), nullable=True),
    sa.Column('payment_date', sa.DateTime(), nullable=True),
    sa.Column('shipped_date', sa.DateTime(), nullable=True),
    sa.Column('completed_date', sa.Date(), nullable=True),
    sa.Column('cancelled_date', sa.DateTime(), nullable=True),
    sa.Column('seller_notes', sa.Text(), nullable=True),
    sa.Column('buyer_notes', sa.Text(), nullable=True),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('sale_price > 0', name='positive_sale_price'),
    sa.CheckConstraint('seller_id != buyer_id', name='different_sale_users'),
    sa.ForeignKeyConstraint(['buyer_id'], ['users.user_id'], ),
    sa.ForeignKeyConstraint(['clothing_id'], ['clothing_items.clothing_id'], ),
    sa.ForeignKeyConstraint(['seller_id'], ['users.user_id'], ),
    sa.PrimaryKeyConstraint('sale_id')
    )
    op.create_index('ix_sales_buyer_id', 'sales', ['buyer_id'], unique=False)
    op.create_index('ix_sales_clothing_id', 'sales', ['clothing_id'], unique=False)
    op.create_index('ix_sales_seller_id', 'sales', ['seller_id'], unique=False)
    op.create_index(op.f('ix_sales_status'), 'sales', ['status'], unique=False)

    # Add sell_price to clothing_items
    op.add_column('clothing_items', sa.Column('sell_price', sa.Numeric(precision=10, scale=2), nullable=True))

    # Add total_sales and total_purchases to users
    op.add_column('users', sa.Column('total_sales', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('total_purchases', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'total_purchases')
    op.drop_column('users', 'total_sales')
    op.drop_column('clothing_items', 'sell_price')
    op.drop_index(op.f('ix_sales_status'), table_name='sales')
    op.drop_index('ix_sales_seller_id', table_name='sales')
    op.drop_index('ix_sales_clothing_id', table_name='sales')
    op.drop_index('ix_sales_buyer_id', table_name='sales')
    op.drop_table('sales')
