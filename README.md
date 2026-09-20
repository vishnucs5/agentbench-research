# AgentBench-Research

Evidence-grounded autonomous research-paper analysis agent for network intrusion detection literature.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- NVIDIA GPU (optional, for Ollama acceleration)

### Environment Setup

```bash
# Copy example env and configure
cp .env.example .env

# Edit .env with your API keys
# Required: SECRET_KEY (32+ chars)
# Optional: OPENROUTER_API_KEY for cloud LLM
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/healthz

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI REST API |
| Web UI | 8501 | Streamlit dashboard |
| PostgreSQL | 5432 | Primary database |
| Qdrant | 6333 | Vector store |
| MinIO | 9000/9001 | Object storage |
| Ollama | 11434 | Local LLM (qwen3-coder:30b) |

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start API with hot reload
uvicorn apps.api.main:app --reload

# Run tests
pytest tests/unit -v
pytest tests/integration -v
```

## Architecture

```
agentbench-research/
├── apps/
│   ├── api/          # FastAPI application
│   ├── worker/       # Background jobs
│   └── web/          # Streamlit dashboard
├── packages/
│   ├── domain/       # Core models, config, database
│   ├── agent/        # LLM providers, planner, tools
│   ├── retrieval/    # Chunking, embeddings, search
│   ├── ingestion/    # PDF upload, parsing, OCR
│   ├── extraction/   # Structured claim extraction
│   ├── synthesis/    # Comparison, gap analysis
│   ├── evaluation/   # Benchmark runners, scorers
│   ├── observability/# Tracing, metrics, logging
│   └── security/     # Auth, RBAC, validators
├── migrations/       # Alembic database migrations
├── tests/            # Unit, integration, evaluation, security
└── infra/            # Docker, compose
```

## LLM Providers

Supports dual providers with automatic fallback:

- **OpenRouter** (cloud): `anthropic/claude-3.5-sonnet` - primary for production
- **Ollama** (local): `qwen3-coder:30b` - primary for development
- **Mock** - deterministic for testing

Configure via `DEFAULT_MODEL_PROVIDER` and `MODEL_PROFILE` in `.env`.

## Development Phases

Per the blueprint, implementation follows 10 vertical slices:

1. **Phase 0**: Repository foundation ✓ (this setup)
2. **Phase 1**: Paper ingestion
3. **Phase 2**: Retrieval & evidence store
4. **Phase 3**: Structured extraction
5. **Phase 4**: Agent planner & tools
6. **Phase 5**: Comparison & gap analysis
7. **Phase 6**: Citation verification & reports
8. **Phase 7**: Evaluation benchmark
9. **Phase 8**: Dashboard & trace replay
10. **Phase 9**: Security hardening

## Testing

```bash
# Unit tests (fast, no external deps)
pytest tests/unit -v

# Integration tests (requires Docker services)
docker-compose up -d postgres qdrant minio
pytest tests/integration -v

# Lint & typecheck
ruff check .
ruff format --check .
mypy apps packages
```

## Configuration

Key settings in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (32+ chars) | *required* |
| `OPENROUTER_API_KEY` | OpenRouter API key | *optional* |
| `DEFAULT_MODEL_PROVIDER` | `openrouter`, `ollama`, or `mock` | `ollama` |
| `MODEL_PROFILE` | `balanced`, `fast`, `local` | `balanced` |
| `DATABASE_URL` | PostgreSQL connection string | local docker |
| `QDRANT_URL` | Vector store URL | local docker |
| `MINIO_ENDPOINT` | Object storage endpoint | local docker |

## License

MIT