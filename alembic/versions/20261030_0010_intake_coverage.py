"""Store self-reported completion of each daily intake category."""

import sqlalchemy as sa
from alembic import op

revision = "20261030_0010"
down_revision = "20261030_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("daily_records", sa.Column("intake_coverage", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("daily_records", "intake_coverage")
