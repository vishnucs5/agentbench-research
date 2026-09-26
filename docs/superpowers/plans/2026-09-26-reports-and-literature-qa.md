# Comprehensive Report Export Suite, Literature Q&A, and GitHub Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade Report Export Suite (BibTeX, LaTeX manuscripts, Markdown surveys, Plagiarism certificates, Claim audit logs), a Multi-Paper Interactive Literature Q&A Assistant ("Chat with Papers") with grounded citation pills, clean git hygiene, and push the repository to GitHub.

**Architecture:**
- **Reporting Engine (`packages/reports`)**: Modular generators for BibTeX citations, compile-ready IEEE/ACM LaTeX documents, Markdown literature surveys, and audit logs.
- **Reports API (`apps/api/reports.py`)**: Endpoints supporting live in-browser preview, download attachments, and clipboard export.
- **Literature Q&A Engine (`apps/api/chat.py`)**: RAG-powered project chat using hybrid BM25 + dense retrieval, generating answers with interactive citation pills.
- **Frontend Station (`apps/web/src/pages/Reports.tsx` & `LiteratureChat.tsx`)**: Dedicated sidebar views with syntax-highlighted preview, 1-click downloads, and interactive citation popovers.
- **Git Hygiene**: Ignore temporary databases/logs and stage/commit clean commits ready to push.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy Async, React 19, TypeScript, Vite, Tailwind CSS, Lucide icons, Pytest.

---

## User Review Required

> [!IMPORTANT]
> **GitHub Remote Configuration:** The local git repository currently has no remote configured (`git remote -v` returns empty). When ready to push, you can provide your GitHub repository URL (e.g. `https://github.com/<username>/<repo>.git` or SSH `git@github.com:...`). We will make sure all commits are clean and prepared.

> [!NOTE]
> **API Key Safety:** Secrets such as `.env` and `agentbench.db` are strictly ignored by `.gitignore` to ensure your OpenRouter API key is never committed or pushed to GitHub.

---

## Proposed Changes

### Component 1: Git Hygiene & GitHub Preparation
- Modify: `.gitignore` to ignore `*.db`, `test_paper.pdf`, `sample_research.py`, and `test_db.py`.
- Stage and commit existing work in logical, conventional-commit messages.

### Component 2: Reporting Engine Package (`packages/reports`)
#### [NEW] `packages/reports/__init__.py`
#### [NEW] `packages/reports/generators/bibtex.py`
- Formats RFC-compliant `@article` / `@inproceedings` entries for project papers.
#### [NEW] `packages/reports/generators/latex.py`
- Produces compile-ready academic IEEE/ACM LaTeX documents (`.tex`) with `\begin{table}` comparative matrices and `\cite{}` keys.
#### [NEW] `packages/reports/generators/markdown.py`
- Generates Markdown literature surveys with executive summaries, paper matrices, and detected research gaps.
#### [NEW] `packages/reports/generators/audit.py`
- Generates verifiable claim audit tables with NLI confidence and chunk/page citations.
#### [NEW] `packages/reports/generators/plagiarism_cert.py`
- Formats certified originality and similarity audit reports.
#### [NEW] `tests/unit/test_reports_generators.py`
- Comprehensive unit tests verifying each generator's output format and syntax.

### Component 3: Backend REST Endpoints
#### [NEW] `apps/api/reports.py`
- `GET /v1/reports/projects/{id}/export?type=...&format=...`
- `GET /v1/reports/plagiarism/{check_id}/export?format=...`
- `POST /v1/reports/preview`
#### [NEW] `apps/api/chat.py`
- `POST /v1/projects/{id}/chat`: Grounded literature question-answering with citation spans.
#### [MODIFY] `apps/api/main.py`
- Register `reports_router` and `chat_router`.
#### [NEW] `tests/integration/test_reports_api.py`
- Integration tests for report downloads and previews.
#### [NEW] `tests/integration/test_chat_api.py`
- Integration tests for literature chat and citation retrieval.

### Component 4: Frontend Station & Navigation
#### [MODIFY] `apps/web/src/lib/api.ts`
- Add `reportsApi.getExportUrl`, `reportsApi.preview`, and `chatApi.sendMessage`.
#### [NEW] `apps/web/src/pages/Reports.tsx`
- Centralized station with project selector, report type tabs (`Survey`, `BibTeX`, `LaTeX`, `Audit`, `Plagiarism`), live code preview, and 1-click Download / Copy / Print.
#### [NEW] `apps/web/src/pages/LiteratureChat.tsx`
- Interactive multi-paper research chat with grounded citation pills and excerpt popovers.
#### [MODIFY] `apps/web/src/components/layout/Sidebar.tsx`
- Add "Reports & Exports" (`FileText`) and "Literature Q&A" (`MessageSquare`) to workspace navigation.
#### [MODIFY] `apps/web/src/App.tsx`
- Register `/reports` and `/chat` routes.

---

## Implementation Tasks

### Task 1: Git Hygiene & Clean Commit Preparation
**Files:**
- Modify: `.gitignore`
- Clean untracked scratch files: `test.db`, `test_db.py`, `sample_research.py`, `test_paper.pdf`
- Commit: Stage completed code changes cleanly.

- [ ] **Step 1:** Update `.gitignore` to ensure all `*.db` and temporary test artifacts are never tracked.
- [ ] **Step 2:** Stage all application files and run `git status` to verify secrets (`.env`) remain ignored.
- [ ] **Step 3:** Commit staged changes with message: `feat: add plagiarism checker, trace replay execution, and interactive dashboard redesign`.

---

### Task 2: Core Reporting Engine Generators (`packages/reports`)
**Files:**
- Create: `packages/reports/__init__.py`
- Create: `packages/reports/generators/bibtex.py`
- Create: `packages/reports/generators/latex.py`
- Create: `packages/reports/generators/markdown.py`
- Create: `packages/reports/generators/audit.py`
- Create: `packages/reports/generators/plagiarism_cert.py`
- Test: `tests/unit/test_reports_generators.py`

**Interfaces:**
- Produces:
  - `generate_bibtex(papers: list[Paper]) -> str`
  - `generate_latex_manuscript(project: Project, papers: list[Paper], runs: list[ResearchRun], comparisons: list[ComparisonTable], gaps: list[Gap]) -> str`
  - `generate_markdown_survey(project: Project, papers: list[Paper], runs: list[ResearchRun], gaps: list[Gap]) -> str`
  - `generate_claim_audit_log(claims: list[dict], verifications: list[dict]) -> str`
  - `generate_plagiarism_certificate(check: PlagiarismCheck) -> str`

- [ ] **Step 1:** Write unit tests in `tests/unit/test_reports_generators.py`.
- [ ] **Step 2:** Run pytest to verify tests fail (module not yet created).
- [ ] **Step 3:** Implement `bibtex.py` with `@article` formatting and sanitization.
- [ ] **Step 4:** Implement `latex.py` with document header, packages, sections, tables, and citations.
- [ ] **Step 5:** Implement `markdown.py`, `audit.py`, and `plagiarism_cert.py`.
- [ ] **Step 6:** Run `pytest tests/unit/test_reports_generators.py -v` to verify 100% pass.

---

### Task 3: Backend REST Endpoints (`apps/api/reports.py` & `chat.py`)
**Files:**
- Create: `apps/api/reports.py`
- Create: `apps/api/chat.py`
- Modify: `apps/api/main.py:100-130`
- Test: `tests/integration/test_reports_api.py`
- Test: `tests/integration/test_chat_api.py`

**Endpoints:**
- `GET /v1/reports/projects/{id}/export?type={bibtex|latex|markdown|audit}&format={file|json}`
- `GET /v1/reports/plagiarism/{check_id}/export?format={html|md}`
- `POST /v1/projects/{id}/chat` -> `ChatResponse(answer: str, citations: list[CitationHit])`

- [ ] **Step 1:** Write integration tests in `tests/integration/test_reports_api.py` and `tests/integration/test_chat_api.py`.
- [ ] **Step 2:** Run tests to verify failure.
- [ ] **Step 3:** Implement `apps/api/reports.py` handlers with attachment `Content-Disposition` headers and preview mode.
- [ ] **Step 4:** Implement `apps/api/chat.py` with hybrid search grounding and fallback model provider execution.
- [ ] **Step 5:** Mount both routers in `apps/api/main.py`.
- [ ] **Step 6:** Run pytest on integration test files to verify passing.

---

### Task 4: Frontend API Client & Types
**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/types/index.ts`

- [ ] **Step 1:** Add TypeScript definitions for `ReportType`, `ExportFormat`, `ReportPreviewResponse`, `ChatMessage`, `CitationHit`.
- [ ] **Step 2:** Add `reportsApi.getExportUrl`, `reportsApi.preview`, and `chatApi.sendMessage` to `api.ts`.

---

### Task 5: Frontend Reports & Exports Center (`apps/web/src/pages/Reports.tsx`)
**Files:**
- Create: `apps/web/src/pages/Reports.tsx`

**Features:**
- Project selector dropdown.
- Report Type pills: `Literature Survey (.md)`, `BibTeX Library (.bib)`, `LaTeX Manuscript (.tex)`, `Claim Audit Log (.md)`, `Plagiarism Certificate (.html)`.
- Live preview pane with syntax highlighting, copy-to-clipboard, and download buttons.
- Print / Save-as-PDF action.

- [ ] **Step 1:** Create `Reports.tsx` component with tab selection and preview loading.
- [ ] **Step 2:** Wire copy and download handlers.

---

### Task 6: Frontend Literature Q&A Assistant (`apps/web/src/pages/LiteratureChat.tsx`)
**Files:**
- Create: `apps/web/src/pages/LiteratureChat.tsx`

**Features:**
- Real-time conversation thread with user and assistant messages.
- Grounded citation pills (e.g. `[Deep Learning Survey, p.1]`) that trigger excerpt popovers showing the raw chunk text and match score.
- Quick prompt buttons for common research queries.

- [ ] **Step 1:** Create `LiteratureChat.tsx` component with message history, input bar, and citation popovers.
- [ ] **Step 2:** Wire `chatApi.sendMessage` mutation.

---

### Task 7: Route Integration, Build & Full Verification
**Files:**
- Modify: `apps/web/src/components/layout/Sidebar.tsx`
- Modify: `apps/web/src/App.tsx`
- Update: `tests/e2e_live_backtest.py`

- [ ] **Step 1:** Add `/reports` and `/chat` to `Sidebar.tsx` navigation items.
- [ ] **Step 2:** Add routes to `App.tsx`.
- [ ] **Step 3:** Compile frontend with `npm run build` in `apps/web`.
- [ ] **Step 4:** Run full `pytest -v` across the entire codebase.
- [ ] **Step 5:** Run `python -u tests/e2e_live_backtest.py` against running server.
- [ ] **Step 6:** Provide user with instructions/command to push to GitHub remote.

---

## Verification Plan

### Automated Tests
1. `pytest tests/unit/test_reports_generators.py -v`
2. `pytest tests/integration/test_reports_api.py -v`
3. `pytest tests/integration/test_chat_api.py -v`
4. `pytest -v` (Full suite: >270 tests)
5. `npm run build` in `apps/web` (0 errors)
6. `python -u tests/e2e_live_backtest.py` (All 16+ checks passing)

### Manual Verification
1. Navigate to `http://127.0.0.1:8000/reports`
   - Select a project
   - Toggle between BibTeX, LaTeX, Survey Markdown, and Plagiarism Certificate
   - Click "Copy to Clipboard" and "Download File"
2. Navigate to `http://127.0.0.1:8000/chat`
   - Ask: "What anomaly detection architectures were tested on CICIDS2017?"
   - Verify grounded citation pill appears and expands to show page 1 excerpt.
