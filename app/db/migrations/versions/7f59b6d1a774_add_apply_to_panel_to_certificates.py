"""add apply_to_panel to certificates

Revision ID: 7f59b6d1a774
Revises: 606d7eb380ce
Create Date: 2026-09-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7f59b6d1a774'
down_revision = '606d7eb380ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'certificates',
        sa.Column('apply_to_panel', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('certificates', 'apply_to_panel')
