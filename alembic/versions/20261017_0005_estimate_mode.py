"""Separate basic assumptions from advanced clarification."""
import sqlalchemy as sa
from alembic import op

revision = '20261017_0005'
down_revision = '20261016_0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('analyses', sa.Column('mode', sa.String(20), nullable=False,
                                       server_default='advanced'))


def downgrade():
    op.drop_column('analyses', 'mode')
