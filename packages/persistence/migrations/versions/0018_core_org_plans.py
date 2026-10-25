"""Remember the plan NEXORA Core last told us for a Clerk organisation, so it
still applies when that organisation reaches Vigilo for the first time (Core
can bill an organisation before any member has opened Vigilo).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-12 15:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "core_org_plans",
        sa.Column("clerk_org_id", sa.String(128), primary_key=True),
        sa.Column("plan_id", sa.String(32), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("core_org_plans")
