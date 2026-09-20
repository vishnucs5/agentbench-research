"""Initial migration

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-20 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('viewer', 'researcher', 'supervisor', 'admin', name='userrole'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='userstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_hash')
    )
    op.create_index('ix_users_email_hash', 'users', ['email_hash'], unique=True)

    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=False, server_default='network-intrusion-detection'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'], unique=False)

    # Papers table
    op.create_table(
        'papers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('authors_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('parser_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.Enum('uploaded', 'parsing', 'parsed', 'indexed', 'failed', name='paperstatus'), nullable=False, server_default='uploaded'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha256')
    )
    op.create_index('ix_papers_project_id', 'papers', ['project_id'], unique=False)
    op.create_index('ix_papers_sha256', 'papers', ['sha256'], unique=True)

    # Paper Pages table
    op.create_table(
        'paper_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('section_label', sa.String(length=255), nullable=True),
        sa.Column('ocr_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parser_version', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('paper_id', 'page_number', name='uq_paper_page_number')
    )
    op.create_index('ix_paper_pages_paper_id', 'paper_pages', ['paper_id'], unique=False)

    # Chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding_ref', sa.String(length=255), nullable=True),
        sa.Column('chunk_version', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['page_id'], ['paper_pages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chunks_paper_id', 'chunks', ['paper_id'], unique=False)

    # Claims table
    op.create_table(
        'claims',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('paper_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_type', sa.String(length=100), nullable=False),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('normalized_value_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.Enum('extracted', 'verified', 'partially_verified', 'unsupported', 'opinion', 'not_reported', name='claimstatus'), nullable=False, server_default='extracted'),
        sa.Column('created_by_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_run_id'], ['research_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['paper_id'], ['papers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_claims_paper_id', 'claims', ['paper_id'], unique=False)

    # Evidence Links table
    op.create_table(
        'evidence_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('support_type', sa.Enum('supports', 'partially_supports', 'contradicts', 'unrelated', name='supporttype'), nullable=False, server_default='supports'),
        sa.Column('match_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chunk_id'], ['chunks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evidence_links_claim_id', 'evidence_links', ['claim_id'], unique=False)

    # Research Runs table
    op.create_table(
        'research_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_text', sa.Text(), nullable=False),
        sa.Column('plan_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.Enum('created', 'planning', 'retrieving', 'extracting', 'synthesizing', 'verifying', 'completed', 'paused', 'failed', 'needs_review', 'cancelled', name='runstatus'), nullable=False, server_default='created'),
        sa.Column('model_profile', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_runs_project_id', 'research_runs', ['project_id'], unique=False)

    # Trace Events table
    op.create_table(
        'trace_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_no', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.Enum('state_transition', 'tool_call', 'tool_result', 'evidence_retrieved', 'claim_extracted', 'claim_verified', 'error', 'budget_warning', 'loop_detected', name='eventtype'), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('input_summary', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('output_summary', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('evidence_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('model_profile', sa.String(length=50), nullable=True),
        sa.Column('redaction_version', sa.String(length=50), nullable=False, server_default='redact-v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'sequence_no', name='uq_trace_sequence')
    )
    op.create_index('ix_trace_events_run_id', 'trace_events', ['run_id'], unique=False)

    # Benchmark Tasks table
    op.create_table(
        'benchmark_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('benchmark_version', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('gold_answer_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('gold_evidence_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_benchmark_tasks_version', 'benchmark_tasks', ['benchmark_version'], unique=False)

    # Evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('scorer_version', sa.String(length=50), nullable=False),
        sa.Column('details_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['benchmark_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluations_run_id', 'evaluations', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_table('evaluations')
    op.drop_table('benchmark_tasks')
    op.drop_table('trace_events')
    op.drop_table('research_runs')
    op.drop_table('evidence_links')
    op.drop_table('claims')
    op.drop_table('chunks')
    op.drop_table('paper_pages')
    op.drop_table('papers')
    op.drop_table('projects')
    op.drop_table('users')
