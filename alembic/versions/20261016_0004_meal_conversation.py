"""Persist clarification dialogue, structured draft and calculation evidence."""
import sqlalchemy as sa
from alembic import op

revision = '20261016_0004'
down_revision = '20261016_0003'
branch_labels = None
depends_on = None


def upgrade():
    for name in ('conversation', 'draft', 'questions', 'details'):
        op.add_column('analyses', sa.Column(name, sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('analyses', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade():
    for name in ('conversation', 'draft', 'questions', 'details', 'error_message'):
        op.drop_column('analyses', name)
