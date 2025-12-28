"""add investor voice_guide

Revision ID: 0002_add_investor_voice_guide
Revises: 0001_create_tables
Create Date: 2025-12-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_investor_voice_guide"
down_revision: Union[str, None] = "0001_create_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investors", sa.Column("voice_guide", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("investors", "voice_guide")
