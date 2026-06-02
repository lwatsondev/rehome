# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

"""Add expires_at to uploads

Revision ID: f8a3c2e1b7d5
Revises: e4f5a2b9c1d3
Create Date: 2026-05-28

"""

import sqlalchemy as sa
from alembic import op

revision = "f8a3c2e1b7d5"
down_revision = "e4f5a2b9c1d3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "uploads", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("uploads", "expires_at")
