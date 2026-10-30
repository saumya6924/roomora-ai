"""row level security: deny-all for Supabase's anon/authenticated roles

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from app.db.rls import disable_rls_everywhere, enable_rls_everywhere

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    enable_rls_everywhere()


def downgrade() -> None:
    disable_rls_everywhere()
