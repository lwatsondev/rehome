"""use Text instead of varchar thanks bean

Revision ID: 4b921713d879
Revises: 3b5782edf9fd
Create Date: 2025-04-15 21:25:40.670967

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4b921713d879"
down_revision = "3b5782edf9fd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.alter_column(
            "file_hash",
            existing_type=sa.String(64),
            type_=sa.Text,
            existing_nullable=False,
        )
        batch_op.alter_column(
            "mimetype",
            existing_type=sa.String(128),
            type_=sa.Text,
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("uploads") as batch_op:
        batch_op.alter_column(
            "file_hash",
            existing_type=sa.Text,
            type_=sa.String(64),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "mimetype",
            existing_type=sa.Text,
            type_=sa.String(128),
            existing_nullable=False,
        )
