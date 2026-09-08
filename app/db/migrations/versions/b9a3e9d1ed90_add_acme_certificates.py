"""add acme certificates

Revision ID: b9a3e9d1ed90
Revises: 1fbfbba7c4b4
Create Date: 2026-09-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b9a3e9d1ed90'
down_revision = '1fbfbba7c4b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'acme_account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('private_key', sa.Text(), nullable=False),
        sa.Column('account_url', sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'certificates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(length=256), nullable=False),
        sa.Column('certificate', sa.Text(), nullable=True),
        sa.Column('private_key', sa.Text(), nullable=True),
        sa.Column('inbound_tags', sa.JSON(), nullable=False),
        sa.Column('auto_renew', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('last_error', sa.String(length=1024), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_certificates_domain'), 'certificates', ['domain'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_certificates_domain'), table_name='certificates')
    op.drop_table('certificates')
    op.drop_table('acme_account')
