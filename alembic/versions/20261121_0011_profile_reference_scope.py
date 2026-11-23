"""Record explicit adult scope and strength-training answers for goal references."""

import sqlalchemy as sa
from alembic import op

revision = "20261121_0011"
down_revision = "20261030_0010"
branch_labels = None
depends_on = None


def upgrade():
    # No default or backfill: existing profiles must explicitly confirm scope.
    with op.batch_alter_table("user_profiles") as batch:
        batch.add_column(sa.Column("strength_training", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("reference_scope", sa.String(24), nullable=True))
        batch.create_check_constraint(
            "ck_user_profiles_reference_scope",
            "reference_scope IN ('general_adult', 'professional_guidance')",
        )


def downgrade():
    with op.batch_alter_table("user_profiles") as batch:
        batch.drop_constraint("ck_user_profiles_reference_scope", type_="check")
        batch.drop_column("reference_scope")
        batch.drop_column("strength_training")
