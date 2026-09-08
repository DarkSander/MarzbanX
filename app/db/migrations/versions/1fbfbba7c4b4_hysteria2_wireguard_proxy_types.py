"""hysteria2 wireguard proxy types

Revision ID: 1fbfbba7c4b4
Revises: 2b231de97dc3
Create Date: 2026-09-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1fbfbba7c4b4'
down_revision = '2b231de97dc3'
branch_labels = None
depends_on = None

old_values = ('VMess', 'VLESS', 'Trojan', 'Shadowsocks')
new_values = old_values + ('Hysteria', 'WireGuard')


def upgrade() -> None:
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum(*old_values, name='proxytypes'),
            type_=sa.Enum(*new_values, name='proxytypes'),
        )


def downgrade() -> None:
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum(*new_values, name='proxytypes'),
            type_=sa.Enum(*old_values, name='proxytypes'),
        )
