"""add users.device_limit

Revision ID: d7e1f3a9b2c4
Revises: c4d2a9f81e37
Create Date: 2026-10-25 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd7e1f3a9b2c4'
down_revision = 'c4d2a9f81e37'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('device_limit', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('device_limit')
