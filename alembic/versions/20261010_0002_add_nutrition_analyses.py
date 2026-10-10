"""add nutrition analyses

Revision ID: 20261010_0002
Revises: 20260713_0001
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from alembic import op

revision = "20261010_0002"
down_revision = "20260713_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("food_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyses_status", "analyses", ["status"], unique=False)

    op.alter_column("jobs", "case_id", existing_type=sa.String(length=36), nullable=True)
    op.add_column("jobs", sa.Column("analysis_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_jobs_analysis_id_analyses",
        "jobs",
        "analyses",
        ["analysis_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_jobs_analysis_id", "jobs", ["analysis_id"], unique=False)


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE analysis_id IS NOT NULL")
    op.drop_index("ix_jobs_analysis_id", table_name="jobs")
    op.drop_constraint("fk_jobs_analysis_id_analyses", "jobs", type_="foreignkey")
    op.drop_column("jobs", "analysis_id")
    op.alter_column("jobs", "case_id", existing_type=sa.String(length=36), nullable=False)

    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_table("analyses")
