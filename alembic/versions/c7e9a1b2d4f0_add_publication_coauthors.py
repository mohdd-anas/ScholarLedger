"""add publication coauthors

Revision ID: c7e9a1b2d4f0
Revises: ba142937f706
Create Date: 2026-11-26 14:48:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e9a1b2d4f0"
down_revision: str | None = "ba142937f706"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create publication_coauthor association table."""
    op.create_table(
        "publication_coauthor",
        sa.Column("publication_id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["publication.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("publication_id", "faculty_id"),
    )
    op.create_index(
        op.f("ix_publication_coauthor_faculty_id"),
        "publication_coauthor",
        ["faculty_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop publication_coauthor association table."""
    op.drop_index(op.f("ix_publication_coauthor_faculty_id"), table_name="publication_coauthor")
    op.drop_table("publication_coauthor")
