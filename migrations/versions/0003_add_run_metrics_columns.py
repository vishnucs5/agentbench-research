"""Add denormalized metric columns to research_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_runs",
        sa.Column("total_latency_ms", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("tool_call_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("trace_event_count", sa.Integer(), server_default="0", nullable=False),
    )

    # Populate existing runs with computed values
    op.execute("""
        UPDATE research_runs
        SET
            total_latency_ms = COALESCE((SELECT SUM(latency_ms) FROM trace_events WHERE run_id = research_runs.id), 0),
            tool_call_count = COALESCE((SELECT COUNT(*) FROM trace_events WHERE run_id = research_runs.id AND event_type = 'tool_call'), 0),
            evidence_count = COALESCE((SELECT SUM(json_array_length(evidence_ids)) FROM trace_events WHERE run_id = research_runs.id), 0),
            trace_event_count = COALESCE((SELECT COUNT(*) FROM trace_events WHERE run_id = research_runs.id), 0)
    """)


def downgrade() -> None:
    op.drop_column("research_runs", "trace_event_count")
    op.drop_column("research_runs", "evidence_count")
    op.drop_column("research_runs", "tool_call_count")
    op.drop_column("research_runs", "total_latency_ms")
