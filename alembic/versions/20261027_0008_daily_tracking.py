"""Private daily records and explicit dates for confirmed meal history."""

from datetime import timezone
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op

revision = "20261027_0008"
down_revision = "20261027_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analyses", sa.Column("consumed_on", sa.Date(), nullable=True))
    op.create_index("ix_analyses_user_consumed", "analyses", ["user_id", "consumed_on"])
    # Existing confirmed meals predate an explicit meal date. Assign their HK
    # confirmation date; only legacy rows without confirmed_at use created_at.
    # Ownership is untouched, so ownerless records stay inaccessible.
    analyses = sa.table(
        "analyses", sa.column("id", sa.String), sa.column("status", sa.String),
        sa.column("confirmed_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("consumed_on", sa.Date),
    )
    connection = op.get_bind()
    rows = connection.execute(sa.select(
        analyses.c.id, analyses.c.confirmed_at, analyses.c.created_at,
    ).where(analyses.c.status == "confirmed"))
    for analysis_id, confirmed_at, created_at in rows:
        timestamp = confirmed_at if confirmed_at is not None else created_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        connection.execute(analyses.update().where(analyses.c.id == analysis_id).values(
            consumed_on=timestamp.astimezone(ZoneInfo("Asia/Hong_Kong")).date(),
        ))
    op.create_table(
        "daily_records",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("record_date", sa.Date(), primary_key=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("manual_calories", sa.Float(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("record_date >= '2000-01-01'", name="ck_daily_records_date"),
        sa.CheckConstraint("weight_kg BETWEEN 30 AND 250", name="ck_daily_records_weight"),
        sa.CheckConstraint("manual_calories BETWEEN 0 AND 20000", name="ck_daily_records_calories"),
        sa.CheckConstraint("revision >= 1", name="ck_daily_records_revision"),
    )


def downgrade():
    op.drop_table("daily_records")
    op.drop_index("ix_analyses_user_consumed", table_name="analyses")
    op.drop_column("analyses", "consumed_on")
