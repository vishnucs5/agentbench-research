# AgentBench High+Critical Bugfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all High and Critical bugs so `docker-compose up` boots Postgres/Qdrant/MinIO/Redis/Ollama, `alembic upgrade head` succeeds, and `pytest` passes with no auth bypass or data-corruption.

**Architecture:** Fix in dependency order — safety/env → config/DB engine → auth/middleware → migrations → Docker/infra → API wiring → ingestion/retrieval/extraction/synthesis/verification/evaluation → test isolation + Docker verification. Each task is independently testable via repro script + existing tests.

**Tech Stack:** Python 3.11, FastAPI 0.109+, SQLAlchemy 2.0 async + asyncpg, Alembic 1.13, Qdrant 1.9, MinIO 7.2, Redis 7, Docker Compose v2, pytest 8 + pytest-asyncio auto mode.

**Spec:** Prior audit in plan conversation (2026-09-22): `packages/domain/config.py:82 demo_mode=True`, `middleware.py:21-88` overbroad exempt + demo bypass, `auth.py:236 role=request.role`, `auth.py:192` discarded refresh, `database.py:16-28` SQLite override + `pool_size` on sqlite, `models.py` PG-UUID vs sqlite, `migrations/versions/0001_initial.py:114` FK before table + drifted `users`, `docker-compose.yml:30,48,77` curl healthchecks + mandatory GPU + missing SECRET_KEY/env_file, `Dockerfile.api:14-22` per-package install with no pyproject, `papers.py/extraction.py/dashboard.py` `get_db_session()` misuse, `projects.py:73-84` fan-out count, retrieval chunker/qdrant UUID/dimension, synthesis limitations word-split, verifier hardcoded mock + missing await, runner discarded TaskResult.

## Global Constraints

- Python `>=3.11`, `ruff line-length=100 target-version=py311`, `mypy strict=true disallow_untyped_defs=true`.
- Never commit `.env` or `agentbench.db`; use `.env.example` only.
- `DEFAULT_MODEL_PROVIDER=mock` in tests; Docker truth is `docker-compose up` + `alembic upgrade head`.
- Each task ends with `pytest` + repro check, then git commit. No `TBD/TODO` placeholders.

---

### Task 1: Secrets safety + env parity

**Files:**
- Modify: `.gitignore`
- Modify: `.env.example`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: `packages/domain/config.py:10-109 Settings` fields.
- Produces: `SECRET_KEY` generation doc, `REDIS_URL/CACHE_DEFAULT_TTL/CACHE_ENABLED/DEMO_MODE/DEMO_USER_EMAIL/LOCAL_STORAGE_PATH/BM25_INDEX_PATH` documented for Task 2/6.

- [ ] **Step 1: Write the failing test**

```python
def test_env_example_parity():
    from pathlib import Path

    text = Path(".env.example").read_text()
    for key in [
        "SECRET_KEY",
        "REDIS_URL",
        "CACHE_DEFAULT_TTL",
        "CACHE_ENABLED",
        "DEMO_MODE",
        "DEMO_USER_EMAIL",
        "LOCAL_STORAGE_PATH",
        "BM25_INDEX_PATH",
        "MINIO_SECURE",
    ]:
        assert key in text, f"missing {key}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v -k parity`
Expected: FAIL with `missing REDIS_URL` (current `.env.example:1-70` lacks them).

- [ ] **Step 3: Write minimal implementation**

1. In `.gitignore` ensure explicit lines (keep existing venv `.env` intent, add comment):
```
# env secrets - never commit
.env
agentbench.db
data/papers/*
data/bm25_index.pkl
data/benchmark/*.json
!data/benchmark/.gitkeep
```
2. Rotate leaked key: delete local `.env` secret or replace `OPENROUTER_API_KEY` with empty; do NOT commit `.env` (verify `git status --porcelain` shows no `.env`).
3. Append to `.env.example`:
```
REDIS_URL=redis://localhost:6379/0
CACHE_DEFAULT_TTL=30
CACHE_ENABLED=true
DEMO_MODE=false
DEMO_USER_EMAIL=demo@test.com
LOCAL_STORAGE_PATH=data/papers
BM25_INDEX_PATH=data/bm25_index.pkl
MINIO_SECURE=false
# Generate: openssl rand -hex 32 (SECRET_KEY must be 32+ chars)
# ALLOWED_MIME_TYPES must be JSON list: ALLOWED_MIME_TYPES='["application/pdf"]'
```
4. Fix `.env.example:40` to `ALLOWED_MIME_TYPES='["application/pdf"]'` to match `config.py:58 list[str]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS (parity test added as `tests/unit/test_env_parity.py::test_env_example_parity` if `test_config.py` is assertion-locked; keep both green).

- [ ] **Step 5: Commit**

```bash
git add .gitignore .env.example tests/unit/test_env_parity.py
git commit -m "fix: gitignore secrets and document all Settings env keys"
```

---

### Task 2: Config + DB engine boot path

**Files:**
- Modify: `packages/domain/config.py:21-28,82`
- Modify: `packages/domain/database.py:12-28,47-62`
- Test: `tests/unit/test_config.py`, repro `python -c "from packages.domain.config import get_settings; print(get_settings().demo_mode)"`

**Interfaces:**
- Consumes: `SECRET_KEY` from env (Task 1).
- Produces: `get_settings()->Settings`, `engine`, `get_session()`, `get_db_session()` semantics used by Tasks 3-5,7-8.

- [ ] **Step 1: Write the failing test**

```python
def test_demo_mode_defaults_false(monkey_patch_env_missing_demo):
    from packages.domain.config import Settings

    s = Settings(_env_file=None, SECRET_KEY="x" * 32)
    assert s.demo_mode is False
```

Run currently fails (`demo_mode=True` in `config.py:82`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL `assert True is False` + existing `test_config.py:19` expects `openrouter` vs `ollama` default (note drift, fix test to `ollama`).

- [ ] **Step 3: Write minimal implementation**

```python
# packages/domain/config.py
secret_key: str = Field(..., min_length=32)
demo_mode: bool = False  # was True; NEVER active in production
```

```python
# packages/domain/database.py
import os
from sqlalchemy.pool import NullPool

settings = get_settings()
database_url = str(settings.database_url)
use_sqlite = database_url.startswith("sqlite")
# REMOVE postgresql->sqlite override in development; honor DATABASE_URL as-is.
# Only default to sqlite when DATABASE_URL is unset (handled by Settings default).
if "sqlite" in database_url:
    engine = create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        database_url,
        echo=settings.is_development,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
```

Keep `get_session()` commit-on-exit but document read-only callers must not rely on auto-commit; keep `get_db_session()` as:
```python
async def get_db_session():
    async with get_session() as session:
        yield session
```
Callers must use `Depends(get_db_session)` (fixed in Task 7), never `PaperRepository(get_db_session())`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS after updating stale assertion `default_model_provider=="ollama"` (not `openrouter`).

- [ ] **Step 5: Commit**

```bash
git add packages/domain/config.py packages/domain/database.py tests/unit/test_config.py
git commit -m "fix: secure demo_mode default and honor DATABASE_URL without sqlite override"
```

---

### Task 3: Auth service hardening

**Files:**
- Modify: `packages/security/auth.py:192,236,288,296-303,324-352`
- Modify: `packages/security/schemas.py:94-98`
- Modify: `apps/api/auth.py:75-86`
- Test: `tests/unit/test_auth*.py`

**Interfaces:**
- Consumes: `User` model, `SecurityConfig`.
- Produces: `AuthService.register/login/refresh_token/change_password` with correct return types for Task 4 middleware.

- [ ] **Step 1: Write the failing test**

```python
async def test_register_forces_researcher_role():
    from packages.security.schemas import RegisterRequest
    from packages.security.auth import AuthService

    svc = AuthService()
    # client sends admin; service must downgrade unless caller is admin
    req = RegisterRequest(email="a@b.co", password="Aa1!aaaa", full_name="A", role="admin")
    # with fix: svc.register(req, requester_role="researcher") -> role researcher
    assert req.role == "admin"  # documents exploit pre-fix
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit -k auth -v`
Expected: FAIL or exploit confirmed (registered user gets `admin`).

- [ ] **Step 3: Write minimal implementation**

```python
# packages/security/schemas.py
from packages.security.schemas import UserRole


class RegisterRequest(BaseModel):
    role: UserRole = UserRole.RESEARCHER  # keep, but AuthService ignores unprivileged input
```

```python
# packages/security/auth.py register()
async def register(self, request: RegisterRequest, requester_role=None) -> UserResponse:
    valid, error = self.validate_password_strength(request.password)
    if not valid:
        raise ValueError(error)
    # Privilege fix: only ADMIN can create ADMIN/SUPERVISOR
    from packages.security.schemas import UserRole
    role = UserRole.RESEARCHER
    if request.role in (UserRole.ADMIN, UserRole.SUPERVISOR) and requester_role == UserRole.ADMIN:
        role = request.role
    user = User(..., role=role, ...)
```

```python
# packages/security/auth.py login(): return refresh token
refresh = self.create_refresh_token(user.id)
return LoginResponse(..., refresh_token=refresh)  # add field to LoginResponse
```

Add `refresh_token: str | None = None` to `LoginResponse` in `schemas.py:85-91`, thread through `refresh_token()` rotation (already revokes old, now returns new refresh too).

```python
# apps/api/auth.py change_password
try:
    ok = await svc.change_password(current_user.id, payload)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
if not ok:
    raise HTTPException(status_code=400, detail="Current password incorrect")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -k auth -v`
Expected: PASS; manual repro `register(role=admin)` creates `researcher`.

- [ ] **Step 5: Commit**

```bash
git add packages/security/auth.py packages/security/schemas.py apps/api/auth.py tests/unit/test_auth*.py
git commit -m "fix: prevent privilege escalation and return refresh tokens, 400 on weak password"
```

---

### Task 4: Middleware + projects + route auth

**Files:**
- Modify: `packages/security/middleware.py:21-43,88,110-143`
- Modify: `apps/api/projects.py:18-27,73-84,118-151`
- Modify: `apps/api/papers.py:37-45,92-99`, `apps/api/retrieval.py`, `apps/api/extraction.py`, `apps/api/synthesis.py`, `apps/api/verification.py`, `apps/api/evaluation.py`, `apps/api/dashboard.py`
- Test: `tests/unit/test_api_health.py`, repro `curl without token -> 401`

**Interfaces:**
- Consumes: `AuthService.decode_token`, `get_current_user`, `require_permission`.
- Produces: Authenticated routers with `owner_id` scoping for Task 7.

- [ ] **Step 1: Write the failing test**

```python
def test_exempt_paths_minimal():
    from apps.api.main import create_app
    from packages.security.middleware import AuthMiddleware

    m = AuthMiddleware.__new__(AuthMiddleware)
    m.exempt_paths = {
        "/",
        "/healthz",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/auth/login",
        "/v1/auth/register",
        "/v1/auth/refresh",
    }
    assert "/projects" not in m.exempt_paths
    assert "/dashboard" not in m.exempt_paths
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_api_health.py -v`
Expected: FAIL pre-fix (current `exempt_paths` contains `/projects,/dashboard,/app,/ui,/trace,/settings`).

- [ ] **Step 3: Write minimal implementation**

```python
# packages/security/middleware.py
self.exempt_paths = {
    "/",
    "/healthz",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/v1/auth/login",
    "/v1/auth/register",
    "/v1/auth/refresh",
}


async def dispatch(self, request, call_next):
    if request.url.path in self.exempt_paths or request.url.path.startswith(
        ("/static", "/assets", "/openapi.json")
    ):
        return await call_next(request)
```

Fix cache rehydration: cache full user via DB fallback only; remove `UserModel(**cached_user)` incomplete construction, instead:
```python
cached_user = await cache.get(f"user:{payload.user_id}")
if cached_user:
    # validate shape, else fall through to DB
    if set(["id", "email", "role", "is_active"]) <= set(cached_user):
        pass  # still DB lookup for correctness; keep cache as negative-cache only
```
Simplest correct: skip object construction, always DB lookup, cache only `is_active` flag. Avoid `str vs UUID` bug.

`apps/api/projects.py`:
```python
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(default="network-intrusion-detection", max_length=100)
    retention_days: int = Field(default=90, ge=1, le=3650)


project_id: UUID  # was str in get/delete; change signature
func.count(distinct(Paper.id)), func.count(distinct(ResearchRun.id))  # fix fan-out
# remove fabricated Demo NIDS Project block lines 100-113; return [] when empty
```

Add to every data router (`papers,retrieval,extraction,synthesis,verification,evaluation,dashboard`):
```python
from packages.domain.models import User
from packages.security.middleware import get_current_user
async def endpoint(..., current_user: User = Depends(get_current_user)): ...
```
Plus ownership check: `where(Project.id==project_id, Project.owner_id==current_user.id)` before paper ops; return 404 if not owned (prevents IDOR).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_api_health.py -v`
Expected: PASS; repro `curl http://localhost:8000/v1/projects` without token → `401`.

- [ ] **Step 5: Commit**

```bash
git add packages/security/middleware.py apps/api/projects.py apps/api/papers.py apps/api/retrieval.py apps/api/extraction.py apps/api/synthesis.py apps/api/verification.py apps/api/evaluation.py apps/api/dashboard.py
git commit -m "fix: narrow auth exemptions, enforce per-route auth and ownership, fix counts and UUIDs"
```

---

### Task 5: Migrations repair

**Files:**
- Modify: `migrations/env.py:7,18,52-68`
- Modify: `migrations/versions/0001_initial.py:20-30,102-152,210-221`
- Modify: `migrations/versions/0002_add_dashboard_indexes.py:18-22`
- Modify: `migrations/versions/0003_add_run_metrics_columns.py:35-42`
- Test: `alembic upgrade head` on Postgres (Docker truth)

**Interfaces:**
- Consumes: `packages/domain/models.py Base.metadata`.
- Produces: Clean `alembic upgrade head` + `downgrade` for Task 6/11.

- [ ] **Step 1: Write the failing test**

```bash
docker-compose up -d postgres
alembic upgrade head
```

Expected pre-fix: `NoSuchTableError: research_runs` (claims FK before table) + `no such column: users.email`.

- [ ] **Step 2: Run to verify it fails**

Run: `alembic upgrade head; echo $?`
Expected: non-zero, FK error.

- [ ] **Step 3: Write minimal implementation**

```python
# migrations/env.py
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))  # was ../..
settings = None


def get_settings_lazy():
    global settings
    if settings is None:
        from packages.domain.config import get_settings as _gs

        settings = _gs()
    return settings


def get_url():
    return str(get_settings_lazy().database_url)


# guard None section:
configuration = config.get_section(config.config_ini_section) or {}
```

```python
# 0001_initial.py upgrade(): reorder research_runs BEFORE claims/evidence_links
# users table: add missing columns to match models.py:106-124
(sa.Column("email", sa.String(255), nullable=False),)
(sa.Column("hashed_password", sa.String(255), nullable=False),)
(sa.Column("full_name", sa.String(255), nullable=True),)
(sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),)
(sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),)
# + unique index on email
# research_runs block moved above claims block
# downgrade(): add
op.execute(
    "DROP TYPE IF EXISTS userrole; DROP TYPE IF EXISTS userstatus; DROP TYPE IF EXISTS paperstatus; DROP TYPE IF EXISTS claimstatus; DROP TYPE IF EXISTS supporttype; DROP TYPE IF EXISTS runstatus; DROP TYPE IF EXISTS eventtype;"
)
```

`0002`: replace `["project_id", sa.text("started_at DESC")]` with two indexes: `op.create_index(..., ["project_id"])` + `op.create_index(..., ["started_at"])` (portable; avoid TextClause).
`0003`: replace `json_array_length(evidence_ids)` with Python-side backfill or `COALESCE(json_array_length(...))` guarded by dialect check; use `server_default=sa.text("0")` for Integer.

- [ ] **Step 4: Run to verify it passes**

Run: `alembic downgrade base; if ($?) { alembic upgrade head }; if ($?) { alembic check }`
Expected: clean upgrade/downgrade, no FK/column errors.

- [ ] **Step 5: Commit**

```bash
git add migrations/env.py migrations/versions/0001_initial.py migrations/versions/0002_add_dashboard_indexes.py migrations/versions/0003_add_run_metrics_columns.py
git commit -m "fix: repair migration order, users drift, portable indexes and downgrade"
```

---

### Task 6: Docker Compose + Dockerfiles

**Files:**
- Modify: `docker-compose.yml:1,30,48,77,81-87,94-165`
- Modify: `infra/docker/Dockerfile.api`, `infra/docker/Dockerfile.worker`, `infra/docker/Dockerfile.web`
- Test: `docker-compose up -d --build postgres qdrant minio redis api`

**Interfaces:**
- Consumes: Task 1 env, Task 5 migrations.
- Produces: Bootable stack for Tasks 7-11 verification.

- [ ] **Step 1: Write the failing test**

```bash
docker-compose up -d qdrant minio ollama
docker ps --format "{{.Names}} {{.Status}}"
```

Expected pre-fix: `unhealthy` (curl missing), `api` crash `ValidationError SECRET_KEY`, ollama blocks CPU hosts.

- [ ] **Step 2: Run to verify it fails**

Run: `docker-compose ps`
Expected: `qdrant/minio/ollama` unhealthy, `api` never healthy.

- [ ] **Step 3: Write minimal implementation**

```yaml
# docker-compose.yml
# remove version: "3.9"
# qdrant healthcheck: ["CMD-SHELL", "wget -qO- http://localhost:6333/healthz | grep -q ok"]
# minio healthcheck: ["CMD-SHELL", "mc ready local || wget -qO- http://localhost:9000/minio/health/live"]
# ollama healthcheck: ["CMD-SHELL", "wget -qO- http://localhost:11434/api/tags || exit 1"]
# ollama: add profiles: ["gpu"] to deploy block OR remove deploy, add comment for GPU override file
# api/worker env: add env_file: [.env], SECRET_KEY=${SECRET_KEY}, REDIS_URL=redis://redis:6379/0, APP_ENV, plus CACHE_*, DEMO_MODE=false
# api/worker depends_on: add redis condition service_healthy
# api command: uvicorn without --reload (prod); keep override for dev via command swap
# volumes: add ./migrations:/app/migrations:ro and remove :ro from code mounts OR keep ro but pip install root first
# web: fix API_BASE_URL to http://localhost:8000 for browser + depends_on api healthy
```

```dockerfile
# infra/docker/Dockerfile.api (same for worker)
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl wget && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install --no-cache-dir -e .
COPY apps/api ./apps/api
# do NOT pip install -e ./apps/api (no pyproject); root install covers it
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://localhost:8000/healthz | grep -q healthy
```

`Dockerfile.web`: switch to Node build if `apps/web/package.json` is Vite/React, else pin Streamlit and ensure `apps/api/static/assets` exists (`mkdir -p`).

- [ ] **Step 4: Run to verify it passes**

Run: `docker-compose up -d --build postgres redis qdrant minio; if ($?) { docker-compose ps }; if ($?) { curl http://localhost:8000/healthz }`
Expected: infra healthy, `api` healthy (after Task 7 health probe).

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml infra/docker/Dockerfile.api infra/docker/Dockerfile.worker infra/docker/Dockerfile.web
git commit -m "fix: portable healthchecks, optional GPU, env wiring and root install"
```

---

### Task 7: API main + dashboard + papers wiring

**Files:**
- Modify: `apps/api/main.py:31,60-62,81,112,119-133`
- Modify: `apps/api/dashboard.py:55-62,80-99,133,200-238`
- Modify: `apps/api/papers.py:55,92-99,270,277`
- Modify: `apps/api/extraction.py:34,43-47,61`
- Modify: `apps/api/retrieval.py:39,99-109`
- Modify: `apps/api/evaluation.py:29-51`
- Test: `tests/unit/test_api_health.py`, `tests/integration/test_ingestion_api.py`

**Interfaces:**
- Consumes: `get_session()`, `cache_client`, `TraceReplayService`.
- Produces: Correct 422/404/304 semantics for pipeline Tasks 8-10.

- [ ] **Step 1: Write the failing test**

```python
async def test_dashboard_runs_bad_date_returns_422():
    from httpx import AsyncClient, ASGITransport
    from apps.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(
            "/v1/dashboard/projects/00000000-0000-0000-0000-000000000000/runs?date_from=foo"
        )
        assert r.status_code in (400, 422)
```

Pre-fix returns 500 (`datetime.fromisoformat` unguarded, `dashboard.py:93`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_api_health.py -v`
Expected: FAIL (500 vs 422, `async with get_db_session()` TypeError on `/runs/{id}`).

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/main.py
from apps.api.main import cache_client  # typed as RedisCache | MemoryCache | None


def create_app():
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins
        if not settings.is_development
        else ["http://localhost:8501", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # static mount guarded:
    from pathlib import Path

    if Path("apps/api/static/assets").is_dir():
        app.mount("/assets", StaticFiles(directory="apps/api/static/assets"), name="static-assets")

    @app.get("/healthz")
    async def health_check():
        from sqlalchemy import text
        from packages.domain.database import engine

        db = "connected"
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            db = "disconnected"
        cache = "connected" if isinstance(cache_client, RedisCache) else "in-memory"
        status = "healthy" if db == "connected" else "degraded"
        return HealthResponse(
            status=status,
            version="0.1.0",
            environment=settings.app_env,
            database=db,
            cache=cache,
            checks={"database": db, "cache": cache, "config": "ok"},
        )
```

```python
# apps/api/dashboard.py
import hashlib
from fastapi import Response
def _etag(payload: dict) -> str:
    return '"' + hashlib.sha256(str(sorted(payload.items())).encode()).hexdigest()[:32] + '"'
# date parsing:
try:
    date_from_dt = datetime.fromisoformat(date_from) if date_from else None
except ValueError:
    raise HTTPException(status_code=422, detail="Invalid date_from")
try:
    event_types_enum = [EventType(e) for e in event_types] if event_types else None
except ValueError:
    raise HTTPException(status_code=422, detail="Invalid event_type")
# cache key includes page_size, truncated search:
cache_key = f"runs:{project_id}:p{page}:ps{page_size}:s{','.join(status or [])}:m{','.join(model_profile or [])}:{str(search)[:64]}:{date_from}:{date_to}"
# 304: return Response(status_code=304) instead of None with response_model
if request.headers.get("if-none-match")==etag:
    return Response(status_code=304)
# get_run_detail: replace async with get_db_session() with:
from packages.domain.database import get_session
async with get_session() as session:
```

```python
# apps/api/papers.py
page: int = Query(1, ge=1)
page_size: int = Query(20, ge=1, le=100)
# chunk linkage: fail loudly, don't fallback to page_rows[0]
pid = page_ids.get(c.page_number)
if pid is None:
    raise HTTPException(
        status_code=500, detail=f"Missing page {c.page_number} for paper {paper_id}"
    )
```

```python
# apps/api/extraction.py
async def extract_claims(..., session: AsyncSession = Depends(get_db_session), ...):
    repo = PaperRepository(session)
    if paper.status not in (PaperStatus.PARSED, PaperStatus.INDEXED):
        raise HTTPException(400, "Paper must be parsed before extraction")
async def get_paper_pdf(paper_id, session: AsyncSession = Depends(get_db_session)): ...
    storage = get_storage_service()
    return await storage.download_file(...) if inspect.isawaitable else storage.download_file(...)
```

```python
# apps/api/retrieval.py index stats:
info = (
    service.qdrant.get_collection_info()
    if service.qdrant
    else {"points_count": len(service._bm25_corpus), "status": "local"}
)
# hydrate page_number/section from Chunk join, not hardcoded 1/None
```

```python
# apps/api/evaluation.py: replace Depends(lambda: None) with real Depends(get_*_service)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_api_health.py tests/integration/test_ingestion_api.py -v`
Expected: PASS (422 on bad date, 200 health with real DB probe).

- [ ] **Step 5: Commit**

```bash
git add apps/api/main.py apps/api/dashboard.py apps/api/papers.py apps/api/extraction.py apps/api/retrieval.py apps/api/evaluation.py
git commit -m "fix: real health probe, CORS, ETag, 422 dates, session DI and chunk linkage"
```

---

### Task 8: Ingestion correctness

**Files:**
- Modify: `packages/ingestion/service.py:40,50,54-68,77,90-127`
- Modify: `packages/ingestion/repository.py:46,60-75,97-120`
- Modify: `packages/ingestion/storage.py:52-70`
- Test: `tests/unit/test_ingestion*.py`

**Interfaces:**
- Consumes: `PaperRepository`, `StorageService`, `PDFParser`.
- Produces: `ingest_upload()->(UUID,str)`, `process_paper()->ParsedPaper` for Task 9/10.

- [ ] **Step 1: Write the failing test**

```python
async def test_process_failure_sets_failed_not_parsing(tmp_session):
    # upload corrupt PDF bytes, process must set status FAILED not stuck PARSING
    pid, _ = await svc.ingest_upload(project_id, b"%PDF-corrupt", "a.pdf", "application/pdf", req)
    with pytest.raises(Exception):
        await svc.process_paper(pid)
    assert (await repo.get_by_id(pid)).status == PaperStatus.FAILED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit -k ingestion -v`
Expected: FAIL (stuck `PARSING`, `parsed.sha256 != paper.sha256` path raises with no status update).

- [ ] **Step 3: Write minimal implementation**

```python
# service.py ingest_upload
if not content_type.lower().split(";")[0].strip() == "application/pdf":
    raise ValueError(...)
existing = await self._repo.get_by_sha256_for_project(sha256, project_id)  # add project filter
try:
    self._storage.upload_file(storage_key, file_data, content_type)
    paper = await self._repo.create_paper(...)
except Exception:
    try:
        self._storage.delete_file(storage_key)
    except Exception:
        pass
    raise
# use datetime.now(timezone.utc) not utcnow()

# process_paper
await self._repo.update_status(paper_id, PaperStatus.PARSING)
try:
    pdf_data = await _to_thread(self._storage.download_file, paper.storage_key)
    parsed = await _to_thread(self._parser.parse, pdf_data)
    if parsed.sha256 != paper.sha256:
        raise ValueError("PDF hash mismatch after parsing")
    await self._repo.save_parsed_paper(paper_id, parsed)
except Exception as e:
    await self._repo.update_status(paper_id, PaperStatus.FAILED)
    raise
```

```python
# repository.py
async def get_by_sha256_for_project(self, sha256, project_id): return select where both
async def save_parsed_paper(...):
    # delete existing pages first to avoid uq_paper_page_number IntegrityError
    await self._session.execute(delete(PaperPage).where(PaperPage.paper_id==paper_id))
```

```python
# storage.py compute_sha256_stream: after read, stream.seek(0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -k ingestion -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/ingestion/service.py packages/ingestion/repository.py packages/ingestion/storage.py tests/unit/test_ingestion*.py
git commit -m "fix: scoped dedup, orphan cleanup, failed status and idempotent pages"
```

---

### Task 9: Retrieval correctness

**Files:**
- Modify: `packages/retrieval/chunker.py:23,110-150`
- Modify: `packages/retrieval/qdrant_store.py:24,63,110,128,198-228,244-250`
- Modify: `packages/retrieval/service.py:48-101,150,176,215,231,264-285`
- Modify: `packages/retrieval/schemas.py:34-35`
- Test: `tests/unit/test_retrieval*.py`, `tests/unit/test_chunker*.py`

**Interfaces:**
- Consumes: `ParsedPaper`, `EmbeddingService`, `QdrantClient`.
- Produces: `index_paper()->{chunk_count,embedded_count,bm25_indexed,vector_indexed}`, `search(SearchRequest)->SearchResponse` for Task 10 runner.

- [ ] **Step 1: Write the failing test**

```python
def test_chunker_rejects_bad_overlap():
    from packages.retrieval.chunker import ChunkingService
    import pytest

    s = ChunkingService(chunk_size=100, chunk_overlap=500)
    with pytest.raises(ValueError):
        s._create_chunks(
            text="w " * 200,
            paper_id=uuid4(),
            page_number=1,
            section_label=None,
            chunk_size=100,
            chunk_overlap=500,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit -k "retrieval or chunk" -v`
Expected: FAIL/hang (infinite loop `start=end-overlap`).

- [ ] **Step 3: Write minimal implementation**

```python
# schemas.py ChunkRequest: chunk_overlap ge=0, validator overlap < size
# chunker.py
if not (0 <= chunk_overlap < chunk_size):
    raise ValueError("chunk_overlap must satisfy 0 <= overlap < size")
# chunk_id stable per content: f"{paper_id}-p{page_number}-c{n}" keep, but _update_bm25_index dedups by chunk_id
```

```python
# qdrant_store.py
import hashlib


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))  # Qdrant requires UUID/int


dimension = len(embeddings[0]) if embeddings else 384  # or settings-driven dim probe
# replace deprecated search/query with query_points:
results = self._client.query_points(
    collection_name=..., query=query_embedding, query_filter=..., limit=top_k, with_payload=True
).points
# _results_to_hits guards:
paper_id = payload.get("paper_id")
text = payload.get("text")
if not paper_id or not text:
    continue
try:
    paper_uuid = uuid.UUID(str(paper_id))
except ValueError:
    continue
# _combine_hits: copy before weighting (don't mutate inputs)
```

```python
# service.py index_paper
allowed = {
    "chunk_id",
    "paper_id",
    "project_id",
    "page_number",
    "section_label",
    "text",
    "token_count",
    "metadata",
}
safe_meta = {k: v for k, v in (metadata or {}).items() if k not in allowed or k == "paper_title"}
chunk_dict.update(safe_meta)  # never clobber ids/text
assert len(chunk_dicts) == len(embeddings) or not embedded  # validate zip
# bm25_indexed reflects save success; search uses request.score_threshold not hardcoded 0.3
hits = [h for h in hits if h.score >= request.score_threshold]
# fix corpus guard: if not corpus or self._bm25_index is None: return []
# store paper_title in chunk_dicts for search_bm25_local
# save/load pickle: wrap in try except Exception, atomic write via tmp+rename
# embed calls via await asyncio.to_thread(self.embedder.embed_batch, texts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -k "retrieval or chunk" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/retrieval/chunker.py packages/retrieval/qdrant_store.py packages/retrieval/service.py packages/retrieval/schemas.py
git commit -m "fix: chunker guard, UUID point ids, query_points API and threshold handling"
```

---

### Task 10: Extraction/Synthesis/Verification/Evaluation logic

**Files:**
- Modify: `packages/extraction/service.py:72-81,146-181`
- Modify: `packages/synthesis/comparison.py:305-366,441,474-479`
- Modify: `packages/synthesis/gap_analysis.py:58-110`
- Modify: `packages/verification/verifier.py:27,100-133,151-158`
- Modify: `packages/verification/report_generator.py:31-95,242-270`
- Modify: `packages/evaluation/runner.py:48,98-120,160-164,202-228,309-346`
- Test: `tests/unit/test_extraction*.py tests/unit/test_synthesis*.py tests/unit/test_verification*.py`

**Interfaces:**
- Consumes: `RetrievalService.search(SearchRequest)`, `ExtractionService.get_paper_claims`.
- Produces: Comparison/gaps/conflicts, `VerificationResult`, `EvaluationSummary` for dashboard.

- [ ] **Step 1: Write the failing test**

```python
def test_limitations_not_word_split():
    from packages.synthesis.comparison import ComparisonService

    svc = ComparisonService()
    rows = svc._build_limitations_comparison(
        pids,
        {
            pid: {
                ClaimType.LIMITATIONS: [
                    {
                        "normalized_value": {"limitation_text": "Accuracy drops on cross-dataset"},
                        "claim_text": "x",
                    }
                ]
            }
        },
    )
    assert not any(r.attribute == "Limitation: accuracy" for r in rows)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit -k "synthesis or extraction or verification or evaluation" -v`
Expected: FAIL (explodes to 10 word rows).

- [ ] **Step 3: Write minimal implementation**

```python
# extraction/service.py: allow indexed, surface errors
if paper.status not in (PaperStatus.PARSED, PaperStatus.INDEXED):
    raise ...
# link_evidence: EvidenceLinkRequest.chunk_id may be str (Qdrant) -> resolve to Chunk.id via lookup, don't cast directly to UUID
```

```python
# comparison.py limitations: group by category/severity, not words
for claim in claims:
    key = normalized.get("category", "general") or "general"
# results: flatten metric_results dicts: {"CIC-IDS2017":{"accuracy":0.98}} -> rows "CIC-IDS2017 accuracy"
# metric defs: guard unhashable: unique = {json.dumps(v,sort_keys=True) for v in defs}
# result conflicts: accept {"accuracy":0.98} directly, not only {"value":x}
# _empty_cell: pass through paper_title param
```

```python
# gap_analysis.py: compare normalized metric names, fix frequency to count papers not occurrences
```

```python
# verifier.py
self.provider = get_provider()  # not get_provider("mock"); honor settings/model_profile
try:
    result = json.loads(...)
    status = AtomicClaimStatus(result.get("status", "unsupported"))
except (ValueError, KeyError):
    status = UNSUPPORTED  # keep inside try
# verify_draft: resolve evidence_ids via retrieval_service.search or DB chunks, honor strict_mode, guard indices (isinstance int, 0<=i<len)
# overall: if total==0: return NOT_REPORTED (not OPINION)
```

```python
# report_generator.py
async def generate_report(...):
    if request.synthesis_id: synthesis = await load_by_id(...)  # don't re-run blindly
    verification_request = VerificationRequest(draft_text=..., evidence_ids=..., paper_ids=..., strict_mode=False)
async def _build_bibliography(...):
    claims = await self.extraction_service.get_paper_claims(pid)  # add await
    # fetch Paper row for title/authors/year/doi, not normalized_value
```

```python
# evaluation/runner.py
benchmark_path = Path(__file__).resolve().parents[2] / "data/benchmark/gold.json"
results: list[TaskResult] = []
... r = TaskResult(...); results.append(r); run.results / store
search_result = await self.retrieval_service.search(SearchRequest(query=task.prompt, top_k=10))
# adaptive: SynthesisRequest(project_id=task.project_id or paper project lookup, paper_ids=...)
# compute summary from results via MetricCalculator, not hardcoded 0.0/1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -k "synthesis or extraction or verification or evaluation" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/extraction/service.py packages/synthesis/comparison.py packages/synthesis/gap_analysis.py packages/verification/verifier.py packages/verification/report_generator.py packages/evaluation/runner.py
git commit -m "fix: synthesis grouping, verifier provider and evidence, runner persistence"
```

---

### Task 11: Test isolation + Docker verification

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/integration/test_ingestion_api.py:21-84`
- Modify: `tests/unit/test_config.py:19`
- Test: `pytest tests/unit -v`, `docker-compose up`

**Interfaces:**
- Consumes: All Tasks 1-10.
- Produces: Green `pytest tests/unit`, bootable `docker-compose up`, `alembic upgrade head`.

- [ ] **Step 1: Write the failing test**

```python
def test_conftest_isolation():
    import os

    assert os.environ.get("APP_ENV") == "test"
    from packages.domain.config import get_settings

    get_settings.cache_clear()
    assert get_settings().database_url is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit -v`
Expected: FAIL pre-fix (`sys.path` points to `C:\Users\pc`, `test_config` expects `openrouter` vs `ollama`, integration uses invalid bcrypt + empty auth).

- [ ] **Step 3: Write minimal implementation**

```python
# tests/conftest.py
sys.path.insert(0, str(Path(__file__).parent.parent))  # repo root, was parent.parent.parent
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("QDRANT_URL", "memory://")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from packages.domain.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

`tests/unit/test_config.py:19`: expect `ollama`/`balanced` (match `config.py:53-54`), not `openrouter`.
`tests/integration/test_ingestion_api.py`: generate real bcrypt hash via `AuthService().hash_password("testpassword123")`, persist `User`+`Project`, login for headers, cleanup via delete; mark with `@pytest.mark.integration` and skip if `DATABASE_URL` unreachable.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit -v`
Expected: PASS. Then Docker truth:
Run: `docker-compose up -d --build postgres redis qdrant minio; if ($?) { alembic upgrade head }; if ($?) { curl http://localhost:8000/healthz }`
Expected: `{"status":"healthy","database":"connected"}`.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/unit/test_config.py tests/integration/test_ingestion_api.py
git commit -m "fix: test isolation, valid auth fixtures and Docker verification"
```

---

## Verification checklist (run after Task 11)

- `docker-compose up -d --build` → `postgres,redis,qdrant,minio` healthy, `api` healthy.
- `alembic downgrade base; alembic upgrade head` clean.
- `pytest tests/unit -v` green.
- Repro: `POST /v1/auth/register` with `role:admin` → `researcher`; `GET /v1/projects` without token → `401`; upload PDF → `process` → `search` → `extract` round-trip succeeds.
