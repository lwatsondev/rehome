# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

"""Make name the sole primary key of uploads. file_hash becomes a unique constraint.

Revision ID: d1e1f6b8fd04784c
Revises: 7c221e1bf861
Create Date: 2026-05-03

"""

import sqlalchemy as sa
from alembic import op

revision = "d1e1f6b8fd04784c"
down_revision = "7c221e1bf861"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "_uploads_new",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("mimetype", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("name"),
        sa.UniqueConstraint("file_hash"),
    )
    op.execute(
        "INSERT INTO _uploads_new SELECT name, original_name, size, mimetype, file_hash, created_at FROM uploads"
    )
    op.drop_table("uploads")
    op.rename_table("_uploads_new", "uploads")


def downgrade():
    op.create_table(
        "_uploads_old",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("mimetype", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("name", "file_hash"),
    )
    op.execute(
        "INSERT INTO _uploads_old SELECT name, original_name, size, mimetype, file_hash, created_at FROM uploads"
    )
    op.drop_table("uploads")
    op.rename_table("_uploads_old", "uploads")
