# React Dashboard MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the single-file HTML dashboard with a React/TypeScript/Tailwind/shadcn-ui frontend. MVP: App Shell, Auth, Overview, Projects, Trace Replay.

**Architecture:** React SPA built with Vite, served by FastAPI at `/`. HTML dashboard moves to `/dashboard-legacy`. Live backend at `localhost:8000`.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v3, shadcn/ui, Lucide React, Recharts, React Router v6

## Global Constraints

- Node >=18, Python >=3.11
- Tailwind CSS v3, shadcn/ui "new-york" style, slate base
- JWT in localStorage key `token`, API prefix `/v1/*`
- Dark theme only: bg `#080D16`, panels `#101A26`, accent `#CFFF4B`
- Monospace: JetBrains Mono; Sans-serif: Inter
- No lorem ipsum

## File Structure

```
apps/web/
├── package.json
├── vite.config.ts
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── tailwind.config.ts
├── postcss.config.js
├── components.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── lib/
    │   ├── api.ts           # fetch wrapper with JWT
    │   ├── utils.ts         # cn() helper
    │   └── mock-data.ts     # fallback mock data
    ├── types/index.ts       # TypeScript interfaces
    ├── hooks/
    │   ├── use-auth.ts      # AuthContext + login/register/logout
    │   └── use-toast.ts
    ├── components/
    │   ├── ui/              # shadcn/ui (button, card, input, badge, dialog, select, table, tabs, toast, label, separator, dropdown-menu, avatar, skeleton, scroll-area)
    │   ├── layout/
    │   │   ├── AppShell.tsx
    │   │   ├── Sidebar.tsx
    │   │   └── TopBar.tsx
    │   ├── auth/
    │   │   ├── LoginOverlay.tsx
    │   │   └── RegisterOverlay.tsx
    │   └── dashboard/
    │       ├── MetricCard.tsx
    │       ├── StatusBadge.tsx
    │       ├── EmptyState.tsx
    │       └── PipelineStepper.tsx
    └── pages/
        ├── Overview.tsx
        ├── Projects.tsx
        ├── TraceReplay.tsx
        └── Settings.tsx      # placeholder
```

---

### Task 1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `apps/web/package.json`, `apps/web/vite.config.ts`, `apps/web/tsconfig.json`, `apps/web/tsconfig.app.json`, `apps/web/tsconfig.node.json`, `apps/web/tailwind.config.ts`, `apps/web/postcss.config.js`, `apps/web/index.html`, `apps/web/src/main.tsx`, `apps/web/src/App.tsx`, `apps/web/src/index.css`

- [ ] Create `apps/web/package.json`:
```json
{
  "name": "agentbench-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }
}
```

- [ ] Create `apps/web/vite.config.ts`:
```ts
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import path from "path"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
      "/docs": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
    },
  },
  build: {
    outDir: "../api/static",
    emptyOutDir: true,
  },
})
```

- [ ] Create `apps/web/tsconfig.json`:
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] Create `apps/web/tsconfig.app.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] Create `apps/web/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] Create `apps/web/tailwind.config.ts`:
```ts
import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#080D16",
        panel: "#101A26",
        "panel-light": "#142331",
        border: "#1E293B",
        accent: "#CFFF4B",
        "accent-dim": "#8FBF2A",
        cyan: "#22D3EE",
        coral: "#FF6B6B",
        amber: "#F59E0B",
        muted: "#64748B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
export default config
```

- [ ] Create `apps/web/postcss.config.js`:
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] Create `apps/web/index.html`:
```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AgentBench Research</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-background text-white antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] Create `apps/web/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-white; }
}
```

- [ ] Create `apps/web/src/main.tsx`:
```tsx
import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import "./index.css"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] Create `apps/web/src/App.tsx` (placeholder):
```tsx
export default function App() {
  return <div className="p-8 text-accent font-mono">AgentBench Research — Loading...</div>
}
```

- [ ] Install dependencies:
```bash
cd apps/web
npm init -y  # already have package.json
npm install react react-dom react-router-dom @tanstack/react-query lucide-react recharts clsx tailwind-merge class-variance-authority
npm install -D typescript @types/react @types/react-dom vite @vitejs/plugin-react tailwindcss postcss autoprefixer tailwindcss-animate
npx tailwindcss init -p
```

- [ ] Verify dev server starts:
```bash
cd apps/web
npm run dev
# Should start on http://localhost:5173
```

---

### Task 2: Install and configure shadcn/ui

**Files:**
- Create: `apps/web/components.json`
- Create: `apps/web/src/lib/utils.ts`
- Create: `apps/web/src/components/ui/` (multiple files via CLI)

- [ ] Create `apps/web/src/lib/utils.ts`:
```ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short", day: "numeric", year: "numeric",
  }).format(new Date(date))
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function truncate(str: string, len: number): string {
  return str.length > len ? str.slice(0, len) + "..." : str
}
```

- [ ] Create `apps/web/components.json`:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": false
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui"
  }
}
```

- [ ] Run shadcn init and add components:
```bash
cd apps/web
npx shadcn@latest init --defaults
npx shadcn@latest add button card input badge dialog select table tabs toast label separator dropdown-menu avatar skeleton scroll-area
```

- [ ] Verify components exist in `src/components/ui/`

---

### Task 3: Define TypeScript types and API client

**Files:**
- Create: `apps/web/src/types/index.ts`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/mock-data.ts`

- [ ] Create `apps/web/src/types/index.ts`:
```ts
export interface User {
  id: string
  email: string
  full_name: string
  role: "viewer" | "researcher" | "supervisor" | "admin"
}

export interface Project {
  id: string
  name: string
  domain: string
  retention_days: number
  created_at: string
  updated_at: string
  paper_count?: number
}

export interface Paper {
  id: string
  project_id: string
  title: string
  authors: string
  status: "uploaded" | "parsed" | "chunked" | "indexed" | "error"
  page_count: number
  parser: string
  sha256: string
  created_at: string
}

export interface ProjectStats {
  project_id: string
  project_name: string
  total_papers: number
  total_runs: number
  completed_runs: number
  failed_runs: number
  total_evidence: number
  avg_latency_ms: number
  recent_runs: RunListItem[]
}

export interface RunListItem {
  id: string
  status: RunStatus
  latency_ms: number
  tool_calls: number
  evidence_count: number
  model: string
  created_at: string
}

export type RunStatus =
  | "created" | "planning" | "retrieving" | "extracting"
  | "synthesizing" | "verifying" | "completed" | "paused"
  | "failed" | "needs_review" | "cancelled"

export interface TraceEvent {
  id: string
  sequence_no: number
  event_type: string
  component: string
  status: string
  latency_ms: number
  input_summary: string
  output_summary: string
  evidence_ids: string[]
  metadata: Record<string, unknown>
}

export interface RunTrace {
  run_id: string
  project_id: string
  status: RunStatus
  total_latency_ms: number
  tool_calls: number
  evidence_ids: string[]
  model: string
  events: TraceEvent[]
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
}
```

- [ ] Create `apps/web/src/lib/api.ts`:
```ts
const API_BASE = ""

function getToken(): string | null {
  return localStorage.getItem("token")
}

export function setToken(token: string) {
  localStorage.setItem("token", token)
}

export function clearToken() {
  localStorage.removeItem("token")
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
  }

  return res.json()
}

// Auth
export const authApi = {
  login: (data: { email: string; password: string }) =>
    api<{ access_token: string; token_type: string }>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  register: (data: {
    email: string; password: string; full_name: string; role?: string
  }) =>
    api<{ id: string; email: string }>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
}

// Projects
export const projectsApi = {
  list: () => api<{ items: any[] }>("/v1/projects"),
  get: (id: string) => api<any>(`/v1/projects/${id}`),
  create: (data: { name: string; domain: string; retention_days?: number }) =>
    api<any>("/v1/projects", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/v1/projects/${id}`, { method: "DELETE" }),
}

// Dashboard
export const dashboardApi = {
  stats: (projectId: string) =>
    api<any>(`/v1/dashboard/projects/${projectId}/stats`),
}

// Papers
export const papersApi = {
  list: (projectId: string) =>
    api<{ items: any[] }>(`/v1/projects/${projectId}/papers`),
}

// Trace Replay
export const traceApi = {
  listRuns: (projectId: string) =>
    api<{ items: any[] }>(`/v1/dashboard/projects/${projectId}/runs`),
  getRun: (runId: string) => api<any>(`/v1/dashboard/runs/${runId}/trace`),
}

// Health
export const healthApi = {
  check: () => api<any>("/healthz"),
}
```

- [ ] Create `apps/web/src/lib/mock-data.ts`:
```ts
export const MOCK_STATS = {
  total_papers: 0,
  total_runs: 0,
  completed_runs: 0,
  failed_runs: 0,
  total_evidence: 0,
  avg_latency_ms: 0,
  recent_runs: [],
}

export const MOCK_PIPELINE = [
  { phase: 0, name: "Foundation", status: "done" as const },
  { phase: 1, name: "Ingestion", status: "done" as const },
  { phase: 2, name: "Retrieval", status: "done" as const },
  { phase: 3, name: "Extraction", status: "done" as const },
  { phase: 4, name: "Synthesis", status: "done" as const },
  { phase: 5, name: "Verification", status: "done" as const },
  { phase: 6, name: "Evaluation", status: "done" as const },
  { phase: 7, name: "Dashboard", status: "active" as const },
]
```

- [ ] Verify TypeScript compiles: `npx tsc --noEmit`

---

### Task 4: Build Auth context and login/register overlays

**Files:**
- Create: `apps/web/src/hooks/use-auth.tsx`
- Create: `apps/web/src/components/auth/LoginOverlay.tsx`
- Create: `apps/web/src/components/auth/RegisterOverlay.tsx`

- [ ] Create `apps/web/src/hooks/use-auth.tsx`:
```tsx
import { createContext, useContext, useState, useCallback, type ReactNode } from "react"
import { authApi, setToken, clearToken } from "@/lib/api"

interface AuthCtx {
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(() => localStorage.getItem("token"))

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setTok(res.access_token)
  }, [])

  const register = useCallback(async (email: string, password: string, name: string) => {
    await authApi.register({ email, password, full_name: name, role: "researcher" })
    // Auto-login after register
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setTok(res.access_token)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setTok(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, login, register, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
```

- [ ] Create `apps/web/src/components/auth/LoginOverlay.tsx` — full-screen overlay with email/password fields, "Sign in & Launch" button, demo credentials helper, toggle to register. Use shadcn Button, Card, Input, Label. Dark theme with accent color.

- [ ] Create `apps/web/src/components/auth/RegisterOverlay.tsx` — similar layout with full_name, email, password fields, role dropdown, password helper text, toggle to login.

- [ ] Verify: `npm run dev` shows login overlay, can register and login against live backend.

---

### Task 5: Build App Shell — Sidebar + TopBar + Layout

**Files:**
- Create: `apps/web/src/components/layout/Sidebar.tsx`
- Create: `apps/web/src/components/layout/TopBar.tsx`
- Create: `apps/web/src/components/layout/AppShell.tsx`

- [ ] Create `apps/web/src/components/layout/Sidebar.tsx`:
  - Fixed left sidebar, dark panel bg
  - Logo/wordmark "AgentBench Research" at top
  - "Research v0.1.0" subtitle
  - Environment badge: "openrouter . balanced"
  - Navigation groups: WORKSPACE (Overview, Projects, Papers, Retrieval, Extraction, Synthesis, Verification, Reports, Evaluation, Trace Replay) and SYSTEM (Settings, API Docs)
  - Each item has Lucide icon + label
  - Active item has lime accent indicator
  - User profile at bottom: "Researcher" + role + status dot

- [ ] Create `apps/web/src/components/layout/TopBar.tsx`:
  - Project selector dropdown
  - "New Project" button
  - Global search: "Ask over papers... (hybrid retrieval)" with ⌘K hint
  - System health: "Live API . SQLite . Qdrant Mock . MinIO Mock"
  - User menu (avatar dropdown with logout)

- [ ] Create `apps/web/src/components/layout/AppShell.tsx`:
  - Flex layout: Sidebar (fixed 260px) + main content area (TopBar + page content via `<Outlet />`)
  - React Router `<Outlet />` for nested routes

- [ ] Wire up React Router in `App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/hooks/use-auth"
import AppShell from "@/components/layout/AppShell"
import LoginOverlay from "@/components/auth/LoginOverlay"
import Overview from "@/pages/Overview"
import Projects from "@/pages/Projects"
import TraceReplay from "@/pages/TraceReplay"
import Settings from "@/pages/Settings"

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <LoginOverlay />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ProtectedRoute>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<Overview />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/trace" element={<TraceReplay />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/dashboard-legacy" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ProtectedRoute>
      </AuthProvider>
    </BrowserRouter>
  )
}
```

- [ ] Verify: Sidebar navigation works, TopBar renders, login overlay shows when unauthenticated.

---

### Task 6: Build shared dashboard components

**Files:**
- Create: `apps/web/src/components/dashboard/MetricCard.tsx`
- Create: `apps/web/src/components/dashboard/StatusBadge.tsx`
- Create: `apps/web/src/components/dashboard/EmptyState.tsx`
- Create: `apps/web/src/components/dashboard/PipelineStepper.tsx`

- [ ] Create `MetricCard.tsx` — accepts title, value, description, accent boolean. Renders a card with monospace value, muted description, optional lime border.

- [ ] Create `StatusBadge.tsx` — accepts status string, returns colored badge (green for completed, red for failed, amber for running, etc.)

- [ ] Create `EmptyState.tsx` — accepts icon, title, description. Centered empty state with muted text.

- [ ] Create `PipelineStepper.tsx` — accepts array of phases with name/status. Renders horizontal stepper with dots connected by lines, lime for done/active, muted for pending.

---

### Task 7: Build Overview page

**Files:**
- Create: `apps/web/src/pages/Overview.tsx`

- [ ] Create `Overview.tsx`:
  - Header: "OVERVIEW" eyebrow, "Research with a quality loop." title
  - 5 MetricCards: Projects, Papers, Evidence, Claims, Runs (fetch from API or use empty state)
  - Pipeline progress section using PipelineStepper (use MOCK_PIPELINE)
  - "Evidence-Grounded Answering" card with citation metrics
  - "Bounded Agent Budgets" card with max_papers: 10, max_tool_calls: 40, deadline: 180s
  - "Model Providers" card showing OpenRouter/Ollama/Mock
  - Quick actions: Upload PDF, Search, Compare, Benchmark buttons
  - Recent runs section (empty state if no runs)

- [ ] Verify: Overview renders with all sections, metric cards show data from API or empty state.

---

### Task 8: Build Projects page

**Files:**
- Create: `apps/web/src/pages/Projects.tsx`

- [ ] Create `Projects.tsx`:
  - Header with "Projects" title, subtitle about retention/domain
  - "New Project" button
  - Dialog/modal for creating project (name, domain pre-filled "network-intrusion-detection", retention 90)
  - Table/cards showing projects with: name, domain, retention, paper count, last activity, "Open" action
  - Uses `projectsApi.list()` and `projectsApi.create()`
  - Toast on create success/error

- [ ] Verify: Can list projects, create new project via modal, see it in list.

---

### Task 9: Build Trace Replay page

**Files:**
- Create: `apps/web/src/pages/TraceReplay.tsx`

- [ ] Create `TraceReplay.tsx`:
  - Header: "Trace Replay", description about redacted traces
  - Controls: Reload button, search input, status filter dropdown
  - Runs table: Run ID, Status (StatusBadge), Latency, Tools, Evidence count, Model
  - When row selected, show detail panel:
    - Summary: total latency, tool calls, evidence IDs, model
    - Timeline: table of TraceEvents with #, Type, Component, Status, Latency, Evidence, Input/Output
  - "redact-v1" label indicating sensitive data is redacted
  - Uses `traceApi.listRuns()` and `traceApi.getRun()`
  - Empty state when no runs

- [ ] Verify: Page loads, shows runs from API (or empty state), selecting a run shows timeline.

---

### Task 10: Build Settings page (placeholder)

**Files:**
- Create: `apps/web/src/pages/Settings.tsx`

- [ ] Create `Settings.tsx`:
  - Header: "Settings . Security & Reproducibility"
  - Read-only sections showing:
    - Model Providers (OpenRouter, Ollama, Mock)
    - Budgets & Limits
    - Ingestion & Retrieval config
    - Security badges (JWT, RBAC, rate limit, etc.)
    - API endpoints list
  - All display-only for MVP

---

### Task 11: Configure FastAPI to serve React build

**Files:**
- Modify: `apps/api/main.py` (add static mount + SPA fallback)
- Modify: `apps/api/dashboard_ui.py` (rename legacy routes)

- [ ] Create `apps/api/static/` directory (Vite builds here)

- [ ] Modify `apps/api/main.py` to add:
```python
from fastapi.staticfiles import StaticFiles

# After all API routes, before the dashboard UI routes:
app.mount("/assets", StaticFiles(directory="apps/api/static/assets"), name="static-assets")
```

- [ ] Modify `apps/api/dashboard_ui.py`:
  - Keep existing HTML routes at `/dashboard`, `/app`, `/ui`
  - Add new route: `GET /` serves `apps/api/static/index.html` (React SPA)
  - Add catch-all: `GET /{path:path}` serves `apps/api/static/index.html` for client-side routing (but only for non-API routes)

- [ ] Build and test:
```bash
cd apps/web
npm run build
# Then restart FastAPI
cd ../..
python -m uvicorn apps.api.main:app --reload
# Visit http://localhost:8000 — should show React dashboard
# Visit http://localhost:8000/dashboard — should show legacy HTML
```

---

### Task 12: Polish and verify

- [ ] Verify all pages render correctly against live backend
- [ ] Verify auth flow: register -> login -> authenticated pages
- [ ] Verify project CRUD: create project -> appears in list -> select
- [ ] Verify trace replay: shows runs or empty state
- [ ] Verify responsive behavior: sidebar collapses on tablet
- [ ] Verify no TypeScript errors: `npx tsc --noEmit`
- [ ] Verify build succeeds: `npm run build`
- [ ] Verify legacy dashboard still works at `/dashboard`
