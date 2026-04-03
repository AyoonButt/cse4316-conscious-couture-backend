"""Add notifications table

Revision ID: d3e4f5a6b7c8
Revises: b4d8e9f1a2c3
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = 'd3e4f5a6b7c8'
down_revision = 'b4d8e9f1a2c3'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if 'notifications' not in inspector.get_table_names():
        op.create_table(
            'notifications',
            sa.Column('notification_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('message', sa.String(500), nullable=False),
            sa.Column('swap_id', sa.Integer(), nullable=True),
            sa.Column('read', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('notification_id'),
            sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
            sa.ForeignKeyConstraint(['swap_id'], ['swaps.swap_id']),
        )
        op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade():
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
