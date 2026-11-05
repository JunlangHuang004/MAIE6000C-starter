"""Record daily exercise calories for an approximate energy balance."""

import sqlalchemy as sa
from alembic import op

revision = "20261030_0009"
down_revision = "20261027_0008"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("daily_records") as batch:
        batch.add_column(sa.Column("exercise_calories", sa.Float(), nullable=True))
        batch.create_check_constraint(
            "ck_daily_records_exercise", "exercise_calories BETWEEN 0 AND 10000",
        )


def downgrade():
    with op.batch_alter_table("daily_records") as batch:
        batch.drop_constraint("ck_daily_records_exercise", type_="check")
        batch.drop_column("exercise_calories")
