"""Create assessment decision ledger.

Revision ID: 20260715_0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "20260715_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("assessment_id"),
    )
    op.create_index("ix_assessments_assessed_at", "assessments", ["assessed_at"])
    op.create_index("ix_assessments_decision", "assessments", ["decision"])
    op.create_index("ix_assessments_session_id", "assessments", ["session_id"])
    op.create_index("ix_assessments_user_id", "assessments", ["user_id"])


def downgrade() -> None:
    op.drop_table("assessments")
