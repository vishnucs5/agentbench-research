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
│   ├── api/          # FastAPI application (includes /v1/plagiarism & /plagiarism UI)
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
│   ├── security/     # Auth, RBAC, validators
│   └── plagiarism/   # Text extraction, normalization, TF-IDF/Jaccard/MinHash, providers, reports
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

## Plagiarism Checker

Evidence-grounded similarity detection for submitted text and documents.

### Features
- Paste text or upload `.txt`, `.pdf`, `.docx` (max 10 MB configurable)
- Extracts readable text (`pymupdf` for PDFs, `python-docx` for docx, plain text)
- Normalizes whitespace, punctuation, preserves paragraph structure
- Segments into sentences/paragraphs for granular matching
- Compares against:
  - Internal corpus: existing `chunks`/`papers` in the database (optionally scoped to a `project_id`)
  - External API if `PLAGIARISM_API_KEY` + `PLAGIARISM_API_URL` configured (combined provider merges results)
- Similarity algorithms: **TF-IDF cosine**, **Jaccard (shingling)**, **MinHash** (modular, replaceable via `create_similarity_calculator`)
- Calculates overall similarity, originality score, per-match confidence, and source attribution
- **Integrated into main dashboard** (`apps/api/templates/dashboard.html:69`): sidebar nav “Plagiarism” with active state (uses existing `nav-item` + `brand-600`), visible only after login via `updateAuthUI()`
- **Full plagiarism page** at `/plagiarism` + **integrated `view-plagiarism` section** inside dashboard + **compact homepage widget** on Overview (`#plagWidget`): paste short text / upload, “Check Similarity”, latest result, stats, and “View Full Report” link that calls `navigate('plagiarism')`
- Accessible, responsive UI with semantic HTML, keyboard navigation, ARIA live regions (`plagStatusRegion`, `aria-live="polite"`), and no color-only cues (icons + text labels for matches)

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAGIARISM_API_KEY` | API key for external plagiarism service | *empty (internal only)* |
| `PLAGIARISM_API_URL` | Base URL for external service | `https://api.plagiarismdetector.com/v1` |
| `PLAGIARISM_MAX_UPLOAD_SIZE_MB` | Max file size for uploads | `10` |
| `PLAGIARISM_ALLOWED_MIME_TYPES` | JSON list of allowed MIME types | `["text/plain","application/pdf",...]` |
| `PLAGIARISM_SIMILARITY_THRESHOLD` | Minimum score to report a match | `0.3` |
| `PLAGIARISM_STORE_SUBMISSIONS` | Default for `consented_to_store` | `false` |
| `PLAGIARISM_RATE_LIMIT_PER_MINUTE` | Per-IP/user checks/min | `10` |
| `PLAGIARISM_RATE_LIMIT_PER_HOUR` | Per-IP/user checks/hour | `100` |

Copy from example:
```bash
cp .env.example .env
# Edit PLAGIARISM_* values as needed
```

### Database Changes

New tables (migration `0004_add_plagiarism_tables`):
- `plagiarism_checks` — one row per submission (user, project, hash, status, scores, consent flag, timestamps)
- `plagiarism_matches` — per-segment matches (similarity, confidence, source document/URL, offsets)

Run migration:
```bash
alembic upgrade head
```

### API Endpoints

All plagiarism endpoints require `Authorization: Bearer <JWT>` except `/supported-types` and `/plagiarism` UI.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/plagiarism/supported-types` | List MIME types, extensions, max size |
| `POST` | `/v1/plagiarism/check/text` | Submit JSON `{text, project_id?, threshold?, consented_to_store}` |
| `POST` | `/v1/plagiarism/check/file` | Multipart `file`, `project_id`, `threshold`, `consented_to_store` (.txt/.pdf/.docx) |
| `GET` | `/v1/plagiarism/checks` | Paginated history `?page=&page_size=&status=` |
| `GET` | `/v1/plagiarism/checks/{check_id}` | Full report with matches + human-readable `summary` (uses “potentially similar content” wording) |
| `DELETE` | `/v1/plagiarism/checks/{check_id}` | Delete own check |
| `GET` | `/plagiarism` | Accessible HTML UI |

Rate limiting: 10/min, 100/hour per IP/user (plagiarism-specific, on top of global 60/min).

### Example Requests & Responses

**Check text:**
```bash
curl -X POST http://localhost:8000/v1/plagiarism/check/text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"The network intrusion detection system monitors traffic...","consented_to_store":true}'
```
**Response (201):**
```json
{
  "id": "c0e8f9a0-...","user_id":"...","status":"completed",
  "overall_similarity": 0.82, "originality_score": 18.0,
  "total_matches": 2, "provider_used": "internal",
  "created_at": "2026-09-24T17:00:00Z"
}
```

**Full report (GET /v1/plagiarism/checks/{id}):**
```json
{
  "check": { "id":"...", "overall_similarity":0.82, "originality_score":18.0, "total_matches":2 },
  "matches": [{
    "source_type":"internal","matched_text":"...","source_text":"...","similarity_score":0.82,"confidence_score":0.82,
    "source_document_title":"Seed Document","source_url":null
  }],
  "summary": "Found 2 potentially similar passage(s) with an overall similarity of 82.0%. 1 passage(s) show high similarity (≥70%), which may indicate direct copying... Note: Similarity scores indicate textual overlap, not necessarily plagiarism."
}
```

**Check file:**
```bash
curl -X POST http://localhost:8000/v1/plagiarism/check/file \
  -H "Authorization: Bearer $TOKEN" \
  -F file=@paper.pdf -F consented_to_store=false
```

**Error cases:**
- `400` unsupported type: `{"detail":"Unsupported file type: image/png"}`
- `413` too large: `{"detail":"File exceeds maximum allowed size of 10 MB"}`
- `429` rate limit: `{"detail":"Rate limit exceeded: max 10 plagiarism checks per minute"}`

### Dashboard Integration

- **Navigation:** Sidebar item `data-view="plagiarism"` (`dashboard.html:69`) with `fa-magnifying-glass-chart` icon, active `bg-brand-600` state via `navigate('plagiarism')` (`dashboard.html:537`). Requires auth (`token` + `updateAuthUI()`); `/plagiarism` HTML and `/v1/plagiarism/supported-types` are exempt for public bootstrap.
- **Full page:** `view-plagiarism` section (`dashboard.html:239`) reuses dashboard cards (`rounded-2xl`, `shadow-soft`, `brand-600` buttons), accessible form (radio group, labels, `aria-describedby`, `focus-visible`), file validation, threshold slider, consent, loading/empty/error/unsupported states, score cards, summary, and highlighted passages (`plag-match-high/medium/low` + `plag-highlight` + icons).
- **Homepage widget:** `plagWidget` on Overview (`dashboard.html:166`) — paste ≤5000 chars or upload, “Check Similarity” (`runPlagWidgetScan()`), displays `checked/avg/high` stats, latest `similarity/originality/matches` and summary, “View Full Report” (`navigate('plagiarism')`). Stats loaded via `loadPlagWidgetStats()` → `GET /v1/plagiarism/checks`.

### UI Usage

1. Log in via dashboard (token stored in `localStorage`).
2. **From homepage widget:** paste short text or upload, click **Check Similarity**, view latest result inline, click **View Full Report** to open detailed page — all without leaving Overview.
3. **Full checker:** Click sidebar **Plagiarism** or visit `http://localhost:8000/plagiarism` (or `http://localhost:8000/dashboard#plagiarism`). Choose **Paste text** or **Upload file**, optionally set project scope/threshold, check consent, and submit.
4. Loading spinner, empty/error/unsupported states are announced via ARIA live regions. Results show originality/similarity cards, summary, and highlighted passages with icons + text labels (not color alone). Table history supports search/sort/pagination (reuses dashboard patterns).

### Security & Privacy

- File type via extension + MIME, size validated server-side
- Text sanitized (`html.escape`, control-char stripping)
- API keys never exposed to client (server env only)
- Submissions not persisted unless `consented_to_store=true` (hash retained, matches stored only with consent)
- Rate limiting + global `RateLimitMiddleware` + `SecurityHeadersMiddleware`

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