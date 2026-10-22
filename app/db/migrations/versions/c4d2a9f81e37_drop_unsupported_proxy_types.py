"""drop VMess, Trojan, Hysteria and WireGuard proxy types

MarzbanX only keeps VLESS and Shadowsocks. Proxies of the removed types are
deleted; users that are left without any proxy get a fresh VLESS one, so
they keep working as soon as their subscription is refreshed.

Revision ID: c4d2a9f81e37
Revises: 3cb7a2406817
Create Date: 2026-10-22 00:00:00.000000

"""
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c4d2a9f81e37'
down_revision = '3cb7a2406817'
branch_labels = None
depends_on = None

removed_values = ('VMess', 'Trojan', 'Hysteria', 'WireGuard')
old_values = ('VMess', 'VLESS', 'Trojan', 'Shadowsocks', 'Hysteria', 'WireGuard')
new_values = ('VLESS', 'Shadowsocks')

proxies = sa.table(
    'proxies',
    sa.column('id', sa.Integer),
    sa.column('user_id', sa.Integer),
    sa.column('type', sa.String),
    sa.column('settings', sa.JSON),
)
excluded_inbounds = sa.table(
    'exclude_inbounds_association',
    sa.column('proxy_id', sa.Integer),
)


def upgrade() -> None:
    conn = op.get_bind()

    removed = proxies.c.type.in_(removed_values)
    affected_users = set(conn.execute(
        sa.select(proxies.c.user_id).where(removed).distinct()
    ).scalars())

    conn.execute(excluded_inbounds.delete().where(
        excluded_inbounds.c.proxy_id.in_(sa.select(proxies.c.id).where(removed))
    ))
    conn.execute(proxies.delete().where(removed))

    still_have_proxies = set(conn.execute(
        sa.select(proxies.c.user_id).where(proxies.c.user_id.in_(affected_users)).distinct()
    ).scalars()) if affected_users else set()

    for user_id in sorted(affected_users - still_have_proxies):
        conn.execute(proxies.insert().values(
            user_id=user_id,
            type='VLESS',
            settings={"id": str(uuid4()), "flow": ""},
        ))

    with op.batch_alter_table('proxies') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum(*old_values, name='proxytypes'),
            type_=sa.Enum(*new_values, name='proxytypes'),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Deleted proxies can't be brought back, only the column type is restored.
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum(*new_values, name='proxytypes'),
            type_=sa.Enum(*old_values, name='proxytypes'),
            existing_nullable=False,
        )
