"""add reengagement events

Revision ID: 0003_add_reengagement_events
Revises: 0002_add_investor_voice_guide
Create Date: 2025-12-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0003_add_reengagement_events"
down_revision: Union[str, None] = "0002_add_investor_voice_guide"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reengagement_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "startup_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("draft_id", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'drafted'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["startup_id"],
            ["startups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["investor_id"],
            ["investors.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_reengagement_events_startup_id",
        "reengagement_events",
        ["startup_id"],
    )
    op.create_index(
        "ix_reengagement_events_investor_id",
        "reengagement_events",
        ["investor_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reengagement_events_investor_id",
        table_name="reengagement_events",
    )
    op.drop_index(
        "ix_reengagement_events_startup_id",
        table_name="reengagement_events",
    )
    op.drop_table("reengagement_events")
