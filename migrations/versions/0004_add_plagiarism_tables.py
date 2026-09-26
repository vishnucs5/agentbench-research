"""Add plagiarism detection tables

Revision ID: 0004_add_plagiarism_tables
Revises: 0003_add_run_metrics_columns
Create Date: 2026-09-24 17:50:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create plagiarism_checks table
    op.create_table(
        "plagiarism_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("source_mime_type", sa.String(length=100), nullable=True),
        sa.Column("source_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", name="plagiarismcheckstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("overall_similarity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("originality_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_used", sa.String(length=50), nullable=False, server_default="internal"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("consented_to_store", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plagiarism_checks_user_id", "plagiarism_checks", ["user_id"], unique=False)
    op.create_index(
        "ix_plagiarism_checks_project_id", "plagiarism_checks", ["project_id"], unique=False
    )
    op.create_index("ix_plagiarism_checks_status", "plagiarism_checks", ["status"], unique=False)
    op.create_index(
        "ix_plagiarism_checks_created_at", "plagiarism_checks", ["created_at"], unique=False
    )

    # Create plagiarism_matches table
    op.create_table(
        "plagiarism_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("internal", "external_api", name="plagiarismsourcetype"),
            nullable=False,
        ),
        sa.Column("matched_text", sa.Text(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_document_title", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_location", sa.String(length=255), nullable=True),
        sa.Column("match_start_offset", sa.Integer(), nullable=True),
        sa.Column("match_end_offset", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["check_id"], ["plagiarism_checks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plagiarism_matches_check_id", "plagiarism_matches", ["check_id"], unique=False
    )
    op.create_index(
        "ix_plagiarism_matches_source_type", "plagiarism_matches", ["source_type"], unique=False
    )
    op.create_index(
        "ix_plagiarism_matches_source_document_id",
        "plagiarism_matches",
        ["source_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("plagiarism_matches")
    op.drop_table("plagiarism_checks")
    # Drop Postgres enum types (postgres-only; skip on sqlite for portability).
    _conn = op.get_bind()
    if _conn is None or _conn.dialect.name == "postgresql":
        op.execute(
            "DROP TYPE IF EXISTS plagiarismcheckstatus; DROP TYPE IF EXISTS plagiarismsourcetype;"
        )
