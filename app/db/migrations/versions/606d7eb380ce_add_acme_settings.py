"""add acme settings

Revision ID: 606d7eb380ce
Revises: b9a3e9d1ed90
Create Date: 2026-09-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '606d7eb380ce'
down_revision = 'b9a3e9d1ed90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'acme_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=True),
        sa.Column('cloudflare_api_token', sa.String(length=512), nullable=True),
        sa.Column('directory_url', sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('acme_settings')
