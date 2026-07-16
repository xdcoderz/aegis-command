"""Add persisted analyst responses and risk policy.

Revision ID: 20260716_0003
Revises: 20260716_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260716_0003"
down_revision = "20260716_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_actions",
        sa.Column("action_id", sa.String(length=36), nullable=False),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["assessments.assessment_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("action_id"),
    )
    op.create_index(
        "ix_session_actions_assessment_id", "session_actions", ["assessment_id"]
    )
    op.create_index("ix_session_actions_session_id", "session_actions", ["session_id"])
    op.create_index("ix_session_actions_actor", "session_actions", ["actor"])
    op.create_index("ix_session_actions_action", "session_actions", ["action"])
    op.create_index("ix_session_actions_acted_at", "session_actions", ["acted_at"])

    op.create_table(
        "security_policy",
        sa.Column("policy_key", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("policy_key"),
    )


def downgrade() -> None:
    op.drop_table("security_policy")
    op.drop_table("session_actions")
