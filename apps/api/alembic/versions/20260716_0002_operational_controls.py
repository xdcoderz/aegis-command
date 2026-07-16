"""Add idempotency and analyst review records.

Revision ID: 20260716_0002
Revises: 20260715_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260716_0002"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("event_id", sa.String(length=36), nullable=True))
    op.execute(sa.text("UPDATE assessments SET event_id = assessment_id WHERE event_id IS NULL"))
    with op.batch_alter_table("assessments") as batch:
        batch.alter_column("event_id", existing_type=sa.String(length=36), nullable=False)
    op.create_index("ix_assessments_event_id", "assessments", ["event_id"], unique=True)

    op.create_table(
        "assessment_reviews",
        sa.Column("review_id", sa.String(length=36), nullable=False),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer", sa.String(length=128), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"], ["assessments.assessment_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index(
        "ix_assessment_reviews_assessment_id", "assessment_reviews", ["assessment_id"]
    )
    op.create_index(
        "ix_assessment_reviews_disposition", "assessment_reviews", ["disposition"]
    )
    op.create_index("ix_assessment_reviews_reviewer", "assessment_reviews", ["reviewer"])
    op.create_index(
        "ix_assessment_reviews_reviewed_at", "assessment_reviews", ["reviewed_at"]
    )


def downgrade() -> None:
    op.drop_table("assessment_reviews")
    op.drop_index("ix_assessments_event_id", table_name="assessments")
    with op.batch_alter_table("assessments") as batch:
        batch.drop_column("event_id")
