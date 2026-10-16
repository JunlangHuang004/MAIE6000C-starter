"""Add review revision and confirmation timestamp."""
import sqlalchemy as sa
from alembic import op

revision = "20261016_0003"
down_revision = "20261010_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analyses", sa.Column("interpreted_food_text", sa.Text(), nullable=True))
    op.add_column(
        "analyses", sa.Column("revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("analyses", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("analyses", "interpreted_food_text")
    op.drop_column("analyses", "confirmed_at")
    op.drop_column("analyses", "revision")
