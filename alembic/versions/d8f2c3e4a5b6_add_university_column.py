"""add university column to faculty and publication

Revision ID: d8f2c3e4a5b6
Revises: c7e9a1b2d4f0
Create Date: 2026-11-26 22:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8f2c3e4a5b6"
down_revision: str | None = "c7e9a1b2d4f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable university columns to faculty and publication."""
    op.add_column("faculty", sa.Column("university", sa.String(length=255), nullable=True))
    op.add_column("publication", sa.Column("university", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove university columns from publication and faculty."""
    op.drop_column("publication", "university")
    op.drop_column("faculty", "university")
