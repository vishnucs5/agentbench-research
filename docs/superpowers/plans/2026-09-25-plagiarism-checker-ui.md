# Plagiarism Checker UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a responsive, accessible Plagiarism Checker interface seamlessly integrated into both the main Dashboard Overview page (`/`) and a dedicated route (`/dashboard/plagiarism-checker`), adhering strictly to the existing dark SaaS design system.

**Architecture:** A reusable `PlagiarismCheckerPanel` orchestrator manages the checking workflow (Text & File input $\rightarrow$ 3-stage animated scan progress $\rightarrow$ neutral score summary and Recharts similarity gauge $\rightarrow$ passage comparisons $\rightarrow$ full scan history with search/filter/delete). This panel is embedded in the main `Overview` page alongside a compact `PlagiarismWidget`, and also rendered on the dedicated `PlagiarismChecker` page. All communication uses the existing `/v1/plagiarism` backend endpoints.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, Lucide React, Recharts, Radix UI primitives (`@radix-ui/react-tabs`, `@radix-ui/react-dialog`), `@tanstack/react-query`, FastAPI, Python 3.11.

**Spec:** `docs/superpowers/specs/2026-09-25-plagiarism-checker-ui-design.md`

## Global Constraints
- Colors: Background `#080D16`, Card Panel `#101A26`, Panel Light `#142331`, Border `#1E293B`, Primary Accent `#CFFF4B`.
- Fonts: `Inter` for UI text, `JetBrains Mono` for percentages, numbers, hashes, and scores.
- Zero new npm dependencies; reuse existing packages in `apps/web/package.json`.
- Neutral terminology: "Potentially Similar Content", "Possible Match", "Similarity Detected".
- WCAG 2.1 AA accessible: ARIA live regions for progress, labels on all form inputs, full keyboard navigation.
- Both embedded in Dashboard Overview AND available on `/dashboard/plagiarism-checker`.

---

### Task 1: Plagiarism TypeScript Types & API Client Enhancement

**Files:**
- Modify: `apps/web/src/types/index.ts`
- Modify: `apps/web/src/lib/api.ts`

**Interfaces:**
- Produces in `types/index.ts`:
  - `PlagiarismCheckStatus` = `"pending" | "processing" | "completed" | "failed"`
  - `PlagiarismSourceType` = `"internal" | "external_api"`
  - `PlagiarismMatch`: `{ id: string; source_type: PlagiarismSourceType; matched_text: string; source_text: string; similarity_score: number; confidence_score: number; source_document_id?: string | null; source_document_title?: string | null; source_url?: string | null; source_location?: string | null; match_start_offset?: number | null; match_end_offset?: number | null; created_at: string; }`
  - `PlagiarismCheck`: `{ id: string; user_id: string; project_id?: string | null; source_filename?: string | null; source_mime_type?: string | null; source_size_bytes?: number | null; status: PlagiarismCheckStatus; overall_similarity: number; originality_score: number; total_matches: number; provider_used: string; error_message?: string | null; consented_to_store: boolean; created_at: string; completed_at?: string | null; }`
  - `PlagiarismReport`: `{ check: PlagiarismCheck; matches: PlagiarismMatch[]; summary: string; }`
  - `PlagiarismListResponse`: `{ checks: PlagiarismCheck[]; total: number; page: number; page_size: number; }`
  - `SupportedFileTypes`: `{ mime_types: string[]; extensions: string[]; max_size_mb: number; }`
- Produces in `lib/api.ts`:
  - `api<T>` supporting `FormData` without overriding `Content-Type`.
  - `plagiarismApi`:
    - `checkText(data: { text: string; project_id?: string; threshold?: number; consented_to_store?: boolean }): Promise<PlagiarismCheck>`
    - `checkFile(formData: FormData): Promise<PlagiarismCheck>`
    - `listChecks(params?: { page?: number; page_size?: number; status?: string }): Promise<PlagiarismListResponse>`
    - `getReport(checkId: string): Promise<PlagiarismReport>`
    - `deleteCheck(checkId: string): Promise<void>`
    - `getSupportedTypes(): Promise<SupportedFileTypes>`

- [ ] **Step 1: Add Plagiarism Types to `apps/web/src/types/index.ts`**
- [ ] **Step 2: Update `apps/web/src/lib/api.ts` to handle `FormData` and export `plagiarismApi`**
- [ ] **Step 3: Verify TypeScript compilation with `npm run build` in `apps/web`**
- [ ] **Step 4: Commit**
  ```bash
  git add apps/web/src/types/index.ts apps/web/src/lib/api.ts
  git commit -m "feat(web): add plagiarism types and api client methods"
  ```

---

### Task 2: Textarea UI Primitive & Plagiarism React Query Hooks

**Files:**
- Create: `apps/web/src/components/ui/textarea.tsx`
- Create: `apps/web/src/hooks/use-plagiarism.ts`

**Interfaces:**
- Produces in `components/ui/textarea.tsx`:
  - `Textarea` component styled consistently with `input.tsx` (`bg-transparent border border-input focus-visible:ring-1 focus-visible:ring-ring text-white placeholder:text-muted-foreground`).
- Produces in `hooks/use-plagiarism.ts`:
  - `usePlagiarismChecks(page?: number, pageSize?: number, status?: string)`
  - `usePlagiarismReport(checkId: string | null)`
  - `usePlagiarismSupportedTypes()`
  - `useCheckTextMutation()`
  - `useCheckFileMutation()`
  - `useDeleteCheckMutation()`

- [ ] **Step 1: Create `apps/web/src/components/ui/textarea.tsx`**
- [ ] **Step 2: Create `apps/web/src/hooks/use-plagiarism.ts` with React Query hooks**
- [ ] **Step 3: Test compilation via `npm run build` in `apps/web`**
- [ ] **Step 4: Commit**
  ```bash
  git add apps/web/src/components/ui/textarea.tsx apps/web/src/hooks/use-plagiarism.ts
  git commit -m "feat(web): create textarea primitive and plagiarism query hooks"
  ```

---

### Task 3: Plagiarism Input & File Upload Components

**Files:**
- Create: `apps/web/src/components/plagiarism/FileUploadZone.tsx`
- Create: `apps/web/src/components/plagiarism/PlagiarismInput.tsx`

**Interfaces:**
- Consumes: `Textarea`, `Button`, `Card`, `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`
- Produces in `FileUploadZone.tsx`:
  - Props: `{ file: File | null; onFileSelect: (file: File | null) => void; disabled?: boolean; maxSizeMb?: number; allowedExtensions?: string[] }`
  - Accessible dropzone with drag enter/leave states, native file browser, format validation, size check, preview pill, and remove button.
- Produces in `PlagiarismInput.tsx`:
  - Props: `{ onSubmitText: (text: string, threshold: number, consent: boolean) => void; onSubmitFile: (file: File, threshold: number, consent: boolean) => void; isLoading: boolean; }`
  - Paste text with word count, character count, clear button, and "Use Sample Text" button.
  - Threshold selector / slider (10% to 50%, default 20%).
  - Consent checkbox with helper text.
  - Submit button with disabled state and loading spinner.

- [ ] **Step 1: Create `FileUploadZone.tsx`**
- [ ] **Step 2: Create `PlagiarismInput.tsx`**
- [ ] **Step 3: Verify TypeScript compilation via `npm run build` in `apps/web`**
- [ ] **Step 4: Commit**
  ```bash
  git add apps/web/src/components/plagiarism/FileUploadZone.tsx apps/web/src/components/plagiarism/PlagiarismInput.tsx
  git commit -m "feat(web): create plagiarism input and file upload components"
  ```

---

### Task 4: Scan Progress, Score Summary, Similarity Chart & Matching Passages

**Files:**
- Create: `apps/web/src/components/plagiarism/ScanProgress.tsx`
- Create: `apps/web/src/components/plagiarism/ScoreSummary.tsx`
- Create: `apps/web/src/components/plagiarism/SimilarityChart.tsx`
- Create: `apps/web/src/components/plagiarism/MatchingPassage.tsx`

**Interfaces:**
- Produces in `ScanProgress.tsx`:
  - Animated 3-step progress bar (Extracting $\rightarrow$ Comparing $\rightarrow$ Preparing report) with `role="status"` and `aria-live="polite"`.
- Produces in `ScoreSummary.tsx`:
  - Props: `{ originalityScore: number; overallSimilarity: number; totalMatches: number; status: string; }`
  - Metric cards using `#101A26` cards, emerald/amber/red badges, and neutral labels.
- Produces in `SimilarityChart.tsx`:
  - Props: `{ originalityScore: number; similarityScore: number; }`
  - Recharts Pie / Donut visualization with `#CFFF4B` and `#FF6B6B` colors and central percentage.
- Produces in `MatchingPassage.tsx`:
  - Props: `{ match: PlagiarismMatch; index: number; }`
  - Collapsible card with similarity %, confidence score, matched excerpt, source excerpt, document title, and external link.

- [ ] **Step 1: Create `ScanProgress.tsx`**
- [ ] **Step 2: Create `ScoreSummary.tsx`**
- [ ] **Step 3: Create `SimilarityChart.tsx`**
- [ ] **Step 4: Create `MatchingPassage.tsx`**
- [ ] **Step 5: Verify compilation via `npm run build` in `apps/web`**
- [ ] **Step 6: Commit**
  ```bash
  git add apps/web/src/components/plagiarism/ScanProgress.tsx apps/web/src/components/plagiarism/ScoreSummary.tsx apps/web/src/components/plagiarism/SimilarityChart.tsx apps/web/src/components/plagiarism/MatchingPassage.tsx
  git commit -m "feat(web): add scan progress, score summary, chart and matching passages"
  ```

---

### Task 5: Scan History Component

**Files:**
- Create: `apps/web/src/components/plagiarism/ScanHistory.tsx`

**Interfaces:**
- Produces in `ScanHistory.tsx`:
  - Props: `{ onSelectCheck: (checkId: string) => void; currentCheckId?: string | null; }`
  - Search filter input, status filter dropdown (`All`, `Completed`, `Failed`, `Processing`), sorting.
  - Table displaying: Document name/preview, checked date, originality %, similarity %, matches count, status badge, action buttons (View Report, Download JSON, Delete check).
  - Delete confirmation dialog using Radix Dialog.
  - Mobile responsive table (horizontal scroll or card layout).

- [ ] **Step 1: Create `ScanHistory.tsx`**
- [ ] **Step 2: Verify compilation via `npm run build` in `apps/web`**
- [ ] **Step 3: Commit**
  ```bash
  git add apps/web/src/components/plagiarism/ScanHistory.tsx
  git commit -m "feat(web): add responsive scan history table with search and delete"
  ```

---

### Task 6: Core Plagiarism Checker Panel & Dedicated Page

**Files:**
- Create: `apps/web/src/components/plagiarism/PlagiarismCheckerPanel.tsx`
- Create: `apps/web/src/pages/PlagiarismChecker.tsx`

**Interfaces:**
- Produces in `PlagiarismCheckerPanel.tsx`:
  - Orchestrates: `PlagiarismInput` $\rightarrow$ `ScanProgress` $\rightarrow$ `ScoreSummary` + `SimilarityChart` + `MatchingPassage` list + Action buttons (Download Report, Print, Start New Check) + `ScanHistory` section below.
- Produces in `PlagiarismChecker.tsx`:
  - Dedicated page container with page header, breadcrumbs, information tooltip, and `PlagiarismCheckerPanel`.

- [ ] **Step 1: Create `PlagiarismCheckerPanel.tsx`**
- [ ] **Step 2: Create `PlagiarismChecker.tsx`**
- [ ] **Step 3: Verify compilation via `npm run build` in `apps/web`**
- [ ] **Step 4: Commit**
  ```bash
  git add apps/web/src/components/plagiarism/PlagiarismCheckerPanel.tsx apps/web/src/pages/PlagiarismChecker.tsx
  git commit -m "feat(web): create plagiarism checker panel and dedicated page"
  ```

---

### Task 7: Dashboard Overview Widget & Embedded Integration

**Files:**
- Create: `apps/web/src/components/dashboard/PlagiarismWidget.tsx`
- Modify: `apps/web/src/pages/Overview.tsx`

**Interfaces:**
- Produces in `PlagiarismWidget.tsx`:
  - Compact widget computing total checks, avg similarity, avg originality, high-similarity count, latest scan status, and "Open Plagiarism Checker" button.
- Updates in `Overview.tsx`:
  - Renders `PlagiarismWidget` in the metrics/summary section.
  - Embeds the `PlagiarismCheckerPanel` directly on the Overview page in a dedicated section with toggle/collapse or full view so users can check content without leaving the homepage.

- [ ] **Step 1: Create `PlagiarismWidget.tsx`**
- [ ] **Step 2: Integrate widget and embedded panel into `apps/web/src/pages/Overview.tsx`**
- [ ] **Step 3: Verify compilation via `npm run build` in `apps/web`**
- [ ] **Step 4: Commit**
  ```bash
  git add apps/web/src/components/dashboard/PlagiarismWidget.tsx apps/web/src/pages/Overview.tsx
  git commit -m "feat(web): add plagiarism widget and embedded checker to overview page"
  ```

---

### Task 8: Navigation, App Routing & FastAPI Backend Pass-through

**Files:**
- Modify: `apps/web/src/components/layout/Sidebar.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/api/dashboard_ui.py`
- Modify: `packages/security/middleware.py`

**Interfaces:**
- Updates in `Sidebar.tsx`:
  - Adds "Plagiarism Checker" to `workspaceNav` pointing to `/dashboard/plagiarism-checker`.
- Updates in `App.tsx`:
  - Adds `/dashboard/plagiarism-checker` and `/plagiarism` routes pointing to `PlagiarismChecker`.
- Updates in `dashboard_ui.py`:
  - Serves `serve_react_app()` for `/dashboard/plagiarism-checker` and `/plagiarism-checker`.
- Updates in `packages/security/middleware.py`:
  - Adds `/dashboard/plagiarism-checker` and `/plagiarism-checker` to `exempt_paths`.

- [ ] **Step 1: Update `Sidebar.tsx` and `App.tsx`**
- [ ] **Step 2: Update `dashboard_ui.py` and `middleware.py`**
- [ ] **Step 3: Run `npm run build` in `apps/web` to build static assets into `apps/api/static/`**
- [ ] **Step 4: Verify Python syntax and lint via `ruff check .`**
- [ ] **Step 5: Commit**
  ```bash
  git add apps/web/src/components/layout/Sidebar.tsx apps/web/src/App.tsx apps/api/dashboard_ui.py packages/security/middleware.py
  git commit -m "feat: wire plagiarism routes in sidebar, react router, and backend spa fallback"
  ```

---

### Task 9: Verification, Accessibility & End-to-End Testing

**Files:**
- Modify/Create: `tests/integration/test_plagiarism_ui_routes.py`

- [ ] **Step 1: Write integration test verifying `/dashboard/plagiarism-checker` returns 200 OK and index.html**
- [ ] **Step 2: Run all unit and integration tests (`pytest -v`)**
- [ ] **Step 3: Run `ruff check .`**
- [ ] **Step 4: Verify live UI endpoints responding via `curl` / `Invoke-WebRequest`**
- [ ] **Step 5: Commit**
  ```bash
  git add tests/integration/
  git commit -m "test: add integration test for plagiarism checker UI route"
  ```
