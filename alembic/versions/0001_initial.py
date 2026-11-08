"""initial schema: locations, submissions, submission_files

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level", "parent_id", "name", name="uq_locations_level_parent_name"),
    )
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tracking_code", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("national_code", sa.String(length=10), nullable=False),
        sa.Column("gender", sa.String(length=10), nullable=False),
        sa.Column("birth_date_jalali", sa.String(length=10), nullable=True),
        sa.Column("birth_date_gregorian", sa.Date(), nullable=True),
        sa.Column("military_status", sa.String(length=40), nullable=True),
        sa.Column("education_degree", sa.String(length=30), nullable=True),
        sa.Column("education_field", sa.String(length=120), nullable=True),
        sa.Column("license_status", sa.String(length=20), nullable=False),
        sa.Column("license_description", sa.Text(), nullable=True),
        sa.Column("center_ownership", sa.String(length=20), nullable=False),
        sa.Column("province_id", sa.Integer(), nullable=False),
        sa.Column("county_id", sa.Integer(), nullable=False),
        sa.Column("province_name", sa.String(length=100), nullable=False),
        sa.Column("county_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=True),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("mobile_number", sa.String(length=15), nullable=False),
        sa.Column("individual_rooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("group_rooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("child_rooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("counselors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_waiting_space", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("accepts_company_pattern", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_accessibility", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["province_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["county_id"], ["locations.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_submissions_tracking_code", "submissions", ["tracking_code"], unique=True
    )
    op.create_index("ix_submissions_national_code", "submissions", ["national_code"])
    op.create_index("ix_submissions_province_id", "submissions", ["province_id"])
    op.create_index("ix_submissions_county_id", "submissions", ["county_id"])
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])

    op.create_table(
        "submission_files",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_submission_files_submission_id", "submission_files", ["submission_id"])


def downgrade() -> None:
    op.drop_index("ix_submission_files_submission_id", table_name="submission_files")
    op.drop_table("submission_files")
    op.drop_index("ix_submissions_created_at", table_name="submissions")
    op.drop_index("ix_submissions_county_id", table_name="submissions")
    op.drop_index("ix_submissions_province_id", table_name="submissions")
    op.drop_index("ix_submissions_national_code", table_name="submissions")
    op.drop_index("ix_submissions_tracking_code", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_table("locations")
