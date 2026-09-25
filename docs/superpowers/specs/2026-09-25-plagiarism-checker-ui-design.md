# Plagiarism Checker UI Design Specification

**Date:** 2026-09-25  
**Topic:** Embedded & Dedicated Plagiarism Checker Interface for AgentBench-Research Dashboard  
**Status:** Validated Design Spec  

---

## 1. Overview & Objectives

This specification defines the design and implementation of a polished, responsive Plagiarism Checker interface inside AgentBench-Research. It fulfills two complementary presentation modes:
1. **Embedded Dashboard Integration:** A compact summary widget and full-featured checking capability directly within the main Dashboard Overview page (`/`).
2. **Dedicated Route:** A full-page experience at `/dashboard/plagiarism-checker` (aliased to `/plagiarism`).

The design strictly reuses the existing design system (deep slate `#080D16` / `#101A26`, `#CFFF4B` lime accent, `#1E293B` borders, Radix UI primitives, Lucide icons, and Recharts), presenting a cohesive, native look and feel.

---

## 2. Design System Alignment

| Element | Specification | Existing Reference |
|---|---|---|
| **Backgrounds** | Page: `#080D16` (`bg-background`), Cards/Panels: `#101A26` (`bg-panel`), Elevated/Hover: `#142331` (`bg-panel-light`) | `tailwind.config.ts`, `Overview.tsx` |
| **Borders** | Subtle slate border: `#1E293B` (`border-border`), Accent border: `#CFFF4B`/30 | `card.tsx`, `Sidebar.tsx` |
| **Accent & Actions** | Primary: `#CFFF4B` (`text-accent` / `bg-accent`), Focus ring: `#CFFF4B` | `button.tsx`, `Sidebar.tsx` |
| **Status Colors** | High originality ($\ge 90\%$): Emerald (`bg-emerald-500/20 text-emerald-400`); Moderate similarity (70–89%): Amber (`bg-amber-500/20 text-amber-400`); High similarity ($< 70\%$): Red/Coral (`bg-red-500/20 text-red-400` / `#FF6B6B`) | `StatusBadge.tsx` |
| **Typography** | Body & headings: `Inter`, sans-serif; Numbers, metrics, percentages, hashes: `JetBrains Mono` monospace | `tailwind.config.ts`, `MetricCard.tsx` |
| **Radius** | Rounded-xl (12px) for cards, rounded-md (6px) for inputs/buttons, rounded-full for badges | `card.tsx`, `badge.tsx` |

---

## 3. Architecture & Routing

### 3.1 Routing
* **Frontend Routes (React Router in `App.tsx`):**
  * `/` $\rightarrow$ `Overview` (includes `PlagiarismWidget` + embedded `PlagiarismCheckerPanel`)
  * `/dashboard/plagiarism-checker` $\rightarrow$ `PlagiarismChecker` (dedicated page)
  * `/plagiarism` $\rightarrow$ redirect to `/dashboard/plagiarism-checker`
* **FastAPI Backend Pass-through (`dashboard_ui.py`):**
  * Mount `/dashboard/plagiarism-checker` and `/plagiarism` to serve `apps/api/static/index.html` (SPA fallback).
  * Update `AuthMiddleware.exempt_paths` in `packages/security/middleware.py` so direct navigation doesn't 401.

### 3.2 Navigation
* **Sidebar (`Sidebar.tsx`):**
  * Add navigation entry under `workspaceNav`:
    ```tsx
    { label: "Plagiarism Checker", path: "/dashboard/plagiarism-checker", icon: <FileSearch size={18} /> }
    ```

---

## 4. Component Architecture & Data Flow

```
apps/web/src/
├── components/
│   ├── dashboard/
│   │   └── PlagiarismWidget.tsx        # Overview summary widget (stats + CTA)
│   ├── plagiarism/
│   │   ├── PlagiarismCheckerPanel.tsx  # Core orchestrator: Input -> Progress -> Results -> History
│   │   ├── PlagiarismInput.tsx         # Tabs: Paste Text vs Upload File + threshold & consent
│   │   ├── FileUploadZone.tsx          # Drag-and-drop & native file picker with validation
│   │   ├── ScanProgress.tsx            # Multi-stage progress indicator with ARIA live announcements
│   │   ├── ScoreSummary.tsx            # Originality, Similarity, Matches, Status metric cards
│   │   ├── SimilarityChart.tsx         # Recharts Donut / Gauge visualization of overlap
│   │   ├── MatchingPassage.tsx         # Collapsible card/accordion comparison with text highlighting
│   │   └── ScanHistory.tsx             # Paginated table with search, status filters, report modal, delete
│   └── ui/
│       └── textarea.tsx                # Auto-resizing styled textarea primitive
├── pages/
│   └── PlagiarismChecker.tsx           # Dedicated full-page view
├── hooks/
│   └── use-plagiarism.ts               # React Query hooks for checks, reports, history, mutations
└── lib/
    └── api.ts                          # plagiarismApi integration with FormData support
```

### 4.1 Component Details

#### 1. `PlagiarismWidget.tsx` (Dashboard Overview Widget)
* **Summary Metrics:**
  * Total Documents Checked (`number`)
  * Average Similarity Score (`percentage`)
  * Average Originality Score (`percentage`)
  * High-Similarity Documents Count ($\ge 30\%$ similarity)
  * Latest Scan Status badge (`StatusBadge`)
* **CTA:** "Open Plagiarism Checker" button linking to `/dashboard/plagiarism-checker` or expanding the embedded panel.

#### 2. `PlagiarismInput.tsx`
* **Tab 1: Paste Text:**
  * Accessible `<Textarea>` with comfortable height (`min-h-[160px]`).
  * Live character count and word count display.
  * "Clear Text" button (resets state).
  * "Use Sample Text" button (populates academic sample text for rapid testing).
* **Tab 2: Upload Document (`FileUploadZone.tsx`):**
  * Drag-and-drop target with visual hover ring (`border-[#CFFF4B]`).
  * "Browse Files" button supporting `.txt`, `.pdf`, `.docx`.
  * Client-side validation: formats check, maximum 10MB file size, unreadable/empty file catch.
  * Selected file preview pill with filename, size (KB/MB), and remove button.
* **Sensitivity & Privacy Controls:**
  * Similarity threshold slider / selector (default: 0.20 or 20%).
  * "Consent to store permanently" checkbox with tooltip explaining privacy.
* **Primary Action:**
  * Button: "Check for Similarity" (disabled when input is empty or invalid, loading spinner when scanning).

#### 3. `ScanProgress.tsx`
* Shows 3-step animated pipeline progress:
  1. *Extracting text* (normalizing and parsing document structure)
  2. *Comparing content* (computing TF-IDF, Jaccard, and MinHash similarity)
  3. *Preparing report* (ranking matched passages and computing scores)
* Rendered with an `aria-live="polite"` region and accessibility text for assistive technologies.

#### 4. `ScoreSummary.tsx` & `SimilarityChart.tsx`
* **Neutral, non-defamatory phrasing:**
  * "Potentially Similar Content", "Possible Match", "Similarity Detected", "High Originality".
* **Cards:**
  * **Originality Score:** `0–100%` (e.g. 94.2% $\rightarrow$ High originality)
  * **Similarity Percentage:** `0–100%` (e.g. 5.8%)
  * **Potential Matches:** Total count of matched passages
  * **Status:** Badge (Completed, Failed, Processing)
* **Score Visualization (`SimilarityChart.tsx`):**
  * Donut / pie chart powered by `Recharts` using `#CFFF4B` (Original) and `#FF6B6B` (Similar).
  * Centered percentage label in monospace font.

#### 5. `MatchingPassage.tsx`
* Accordion/card comparison layout:
  * Left/Top: Submitted excerpt with highlighted matching substrings (`bg-amber-500/20 text-amber-200 px-1 rounded`).
  * Right/Bottom: Matched source document / web page excerpt.
  * Source Title & URL (`target="_blank" rel="noopener noreferrer"` with `ExternalLink` icon).
  * Similarity score badge (e.g., `85% similarity`) & confidence rating.
  * Expand/collapse toggling.

#### 6. `ScanHistory.tsx`
* Filterable table with search query (document name/content), status dropdown (`All`, `Completed`, `Failed`, `Processing`), and sort controls.
* Rows display: Document Name / Snippet, Checked Date (relative / formatted), Originality Score, Similarity %, Matches Count, Status badge, Actions menu.
* Actions:
  * "View Report" (opens full report view or modal).
  * "Download Report" (JSON / Markdown file export).
  * "Delete Scan" (triggers confirmation dialog and deletes via `DELETE /v1/plagiarism/checks/{id}`).

---

## 5. API Integration & Error Handling

### 5.1 API Client Updates (`apps/web/src/lib/api.ts`)
* Enhance `api<T>` to omit `"Content-Type": "application/json"` when `options.body instanceof FormData` (allowing browser-generated boundary).
* Export `plagiarismApi`:
  * `checkText(data: { text: string; project_id?: string; threshold?: number; consented_to_store?: boolean })`
  * `checkFile(formData: FormData)`
  * `listChecks(params?: { page?: number; page_size?: number; status?: string })`
  * `getReport(checkId: string)`
  * `deleteCheck(checkId: string)`
  * `getSupportedTypes()`

### 5.2 Error & Validation Handling
* **Client-side validation:**
  * Prevent submission if text is $< 10$ characters or file is empty / unsupported.
  * Immediate feedback with red inline message.
* **Server-side error handling:**
  * 400 (Invalid input) $\rightarrow$ Display user-friendly error alert.
  * 413 (File/Text too large) $\rightarrow$ "File exceeds maximum size limit (10MB)".
  * 429 (Rate limit) $\rightarrow$ "Rate limit reached. Please wait a moment before running another scan."
  * 500 (Internal) $\rightarrow$ "An unexpected error occurred while analyzing the document. Please try again."

---

## 6. Accessibility & Responsiveness

* **Accessibility (WCAG 2.1 AA):**
  * Semantic HTML (`<main>`, `<section>`, `<article>`, `<header>`).
  * Form inputs have explicitly linked `<Label>` components (`htmlFor`).
  * Icon-only buttons have `aria-label` attributes.
  * Full keyboard navigability (Tab, Enter, Space, Escape to close modals).
  * `aria-live="polite"` for scan progress and dynamic score updates.
  * Color is never the sole indicator of status (always accompanied by percentage text and labels).
* **Responsive Breakpoints:**
  * **Desktop ($\ge 1024$px):** 2-column or side-by-side view for input and recent scan summary; 4-card metric grid.
  * **Tablet ($768$px–$1023$px):** 2-column metric grid; passage comparisons stack comfortably.
  * **Mobile ($< 768$px):** Single-column stacked layout; full-width buttons; horizontally scrollable history table with compact badges.

---

## 7. Testing & Verification Plan

1. **Unit & Component Testing:**
   * Test `PlagiarismInput` character/word count calculations and validation.
   * Test `FileUploadZone` drag-and-drop file rejection on invalid MIME types.
   * Test `MatchingPassage` expand/collapse state.
2. **Build & Lint Verification:**
   * `npm run build` in `apps/web` (TypeScript check `tsc -b` and Vite bundle generation).
   * Verify static assets generated into `apps/api/static/`.
   * `ruff check .` for backend route additions.
3. **End-to-End API & Route Verification:**
   * Test `POST /v1/plagiarism/check/text` and `GET /v1/plagiarism/checks` from web client.
   * Direct URL browser navigation to `/dashboard/plagiarism-checker` returns 200 OK.
