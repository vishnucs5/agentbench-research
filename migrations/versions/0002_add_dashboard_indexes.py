"""Add dashboard performance indexes

Revision ID: 0002
Revises: 0001_initial
Create Date: 2026-09-21
"""

from alembic import op

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Portable indexes for most common dashboard query: runs by project ordered by date
    # Split composite DESC TextClause into two portable single-column indexes.
    op.create_index(
        "ix_research_runs_project_started",
        "research_runs",
        ["project_id"],
    )
    op.create_index(
        "ix_research_runs_project_started_at",
        "research_runs",
        ["started_at"],
    )

    # Index for status filtering
    op.create_index(
        "ix_research_runs_status",
        "research_runs",
        ["status"],
    )

    # Composite index for trace events aggregation
    op.create_index(
        "ix_trace_events_run_event_type",
        "trace_events",
        ["run_id", "event_type"],
    )

    # Index for date range filtering
    op.create_index(
        "ix_research_runs_started_at",
        "research_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_runs_started_at", "research_runs")
    op.drop_index("ix_trace_events_run_event_type", "trace_events")
    op.drop_index("ix_research_runs_status", "research_runs")
    op.drop_index("ix_research_runs_project_started_at", "research_runs")
    op.drop_index("ix_research_runs_project_started", "research_runs")
