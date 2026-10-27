"""Private profile inputs and optimistic concurrency for daily references."""

import sqlalchemy as sa
from alembic import op

revision = "20261027_0007"
down_revision = "20261027_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("age_years", sa.Integer(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("goal", sa.String(20), nullable=False),
        sa.Column("activity_level", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("age_years BETWEEN 18 AND 80", name="ck_user_profiles_age"),
        sa.CheckConstraint("height_cm BETWEEN 120 AND 220", name="ck_user_profiles_height"),
        sa.CheckConstraint("weight_kg BETWEEN 30 AND 250", name="ck_user_profiles_weight"),
        sa.CheckConstraint("sex IN ('male', 'female')", name="ck_user_profiles_sex"),
        sa.CheckConstraint("goal IN ('gain_muscle', 'lose_fat')", name="ck_user_profiles_goal"),
        sa.CheckConstraint(
            "activity_level IN ('sedentary', 'light', 'moderate', 'high')",
            name="ck_user_profiles_activity",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_user_profiles_revision"),
    )


def downgrade():
    op.drop_table("user_profiles")
