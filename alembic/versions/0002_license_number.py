"""add license_number column, make mobile_number optional

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-10 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("license_number", sa.String(50), nullable=True))
    op.alter_column("submissions", "mobile_number", existing_type=sa.String(15), nullable=True)


def downgrade() -> None:
    op.alter_column("submissions", "mobile_number", existing_type=sa.String(15), nullable=False)
    op.drop_column("submissions", "license_number")
