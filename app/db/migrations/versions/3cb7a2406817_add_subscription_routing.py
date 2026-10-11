"""add subscription routing

Revision ID: 3cb7a2406817
Revises: 7f59b6d1a774
Create Date: 2026-10-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3cb7a2406817'
down_revision = '7f59b6d1a774'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'subscription_routing',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('source', sa.String(length=32), nullable=False, server_default='roscomvpn_default'),
        sa.Column('custom_value', sa.Text(), nullable=True),
        sa.Column('happ_only', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('cached_source', sa.String(length=32), nullable=True),
        sa.Column('cached_link', sa.Text(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.String(length=1024), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('subscription_routing')
