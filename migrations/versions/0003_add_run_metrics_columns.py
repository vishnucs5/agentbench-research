"""Add denormalized metric columns to research_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_runs",
        sa.Column("total_latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("tool_call_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("evidence_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "research_runs",
        sa.Column("trace_event_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    # Populate existing runs with computed values (portable across dialects).
    connection = op.get_bind()
    if connection is None:
        return
    dialect_name = connection.dialect.name
    if dialect_name == "postgresql":
        connection.execute(
            sa.text(
                """
                UPDATE research_runs
                SET
                    total_latency_ms = COALESCE(
                        (SELECT SUM(latency_ms) FROM trace_events
                         WHERE run_id = research_runs.id), 0),
                    tool_call_count = COALESCE(
                        (SELECT COUNT(*) FROM trace_events
                         WHERE run_id = research_runs.id
                         AND event_type = 'tool_call'), 0),
                    evidence_count = COALESCE(
                        (SELECT SUM(COALESCE(json_array_length(evidence_ids), 0))
                         FROM trace_events
                         WHERE run_id = research_runs.id), 0),
                    trace_event_count = COALESCE(
                        (SELECT COUNT(*) FROM trace_events
                         WHERE run_id = research_runs.id), 0)
                """
            )
        )
        return

    # Portable Python-side backfill for sqlite and other dialects
    # (avoids json_array_length portability issues).
    import json

    run_rows = connection.execute(sa.text("SELECT id FROM research_runs")).fetchall()
    for (run_id,) in run_rows:
        total = (
            connection.execute(
                sa.text(
                    "SELECT COALESCE(SUM(latency_ms), 0) FROM trace_events WHERE run_id = :rid"
                ),
                {"rid": run_id},
            ).scalar()
            or 0
        )
        tool_calls = (
            connection.execute(
                sa.text(
                    "SELECT COUNT(*) FROM trace_events "
                    "WHERE run_id = :rid AND event_type = 'tool_call'"
                ),
                {"rid": run_id},
            ).scalar()
            or 0
        )
        trace_count = (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM trace_events WHERE run_id = :rid"),
                {"rid": run_id},
            ).scalar()
            or 0
        )
        ev_rows = connection.execute(
            sa.text("SELECT evidence_ids FROM trace_events WHERE run_id = :rid"),
            {"rid": run_id},
        ).fetchall()
        evidence_total = 0
        for (ev,) in ev_rows:
            if ev is None:
                continue
            if isinstance(ev, list):
                evidence_total += len(ev)
            elif isinstance(ev, str):
                try:
                    parsed = json.loads(ev)
                except Exception:
                    continue
                if isinstance(parsed, list):
                    evidence_total += len(parsed)
        connection.execute(
            sa.text(
                "UPDATE research_runs SET total_latency_ms = :t, "
                "tool_call_count = :c, evidence_count = :e, "
                "trace_event_count = :n WHERE id = :rid"
            ),
            {
                "t": int(total),
                "c": int(tool_calls),
                "e": int(evidence_total),
                "n": int(trace_count),
                "rid": run_id,
            },
        )


def downgrade() -> None:
    op.drop_column("research_runs", "trace_event_count")
    op.drop_column("research_runs", "evidence_count")
    op.drop_column("research_runs", "tool_call_count")
    op.drop_column("research_runs", "total_latency_ms")
