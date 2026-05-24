"""fix organization member uniqueness for soft deletes

Revision ID: 003
Revises: 002
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY organization_id, user_id
                       ORDER BY created_at DESC
                   ) AS rn
            FROM organization_members
            WHERE deleted_at IS NULL
        )
        UPDATE organization_members
        SET deleted_at = now()
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.drop_constraint("uq_org_user", "organization_members", type_="unique")
    op.create_index(
        "uq_org_user_active",
        "organization_members",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_org_user_active", table_name="organization_members")
    op.create_unique_constraint(
        "uq_org_user",
        "organization_members",
        ["organization_id", "user_id"],
    )
