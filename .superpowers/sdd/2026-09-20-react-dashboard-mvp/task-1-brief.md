# Task 1: Scaffold Vite + React + TypeScript project

## Task Description

Read your task brief first: this file
It contains the full task text from the plan.

## Context

This is the foundation task for the AgentBench React dashboard. The project currently has NO frontend build system — no package.json, no Vite, no React. The existing dashboard is a single 850-line HTML file served by FastAPI at `/dashboard`.

Your job is to create the `apps/web/` directory with a complete Vite + React + TypeScript + Tailwind CSS project that can run in dev mode and build for production.

## What to Create

Create ALL of these files in `apps/web/`:

### 1. `package.json`
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

### 2. `vite.config.ts`
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

### 3. `tsconfig.json`
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

### 4. `tsconfig.app.json`
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

### 5. `tsconfig.node.json`
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

### 6. `tailwind.config.ts`
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

### 7. `postcss.config.js`
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### 8. `index.html`
```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
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

### 9. `src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-white; }
}
```

### 10. `src/main.tsx`
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

### 11. `src/App.tsx` (placeholder)
```tsx
export default function App() {
  return <div className="p-8 text-accent font-mono">AgentBench Research — Loading...</div>
}
```

## After Creating Files

1. Run `npm install` in `apps/web/`
2. Install all dependencies:
   - Runtime: react, react-dom, react-router-dom, @tanstack/react-query, lucide-react, recharts, clsx, tailwind-merge, class-variance-authority
   - Dev: typescript, @types/react, @types/react-dom, vite, @vitejs/plugin-react, tailwindcss, postcss, autoprefixer, tailwindcss-animate
3. Run `npx tailwindcss init -p` if needed (postcss.config.js already created above)
4. Verify `npm run dev` starts the Vite dev server on port 5173
5. Verify the page shows "AgentBench Research — Loading..." with the accent color

## Your Job

1. Create all files listed above
2. Install dependencies
3. Verify the dev server starts and the page renders
4. Commit your work
5. Self-review
6. Report back

Work from: `C:\Users\pc\agentbench-research\apps\web`

**Do NOT dispatch subagents.** Do all work yourself.

## Report Format

Write your full report to `C:\Users\pc\agentbench-research\.superpowers\sdd\2026-09-20-react-dashboard-mvp\task-1-report.md`:
- What you implemented
- What you tested and test results
- Files changed
- Self-review findings (if any)
- Any issues or concerns

Then report back with ONLY:
- **Status:** DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
- Commits created (short SHA + subject)
- One-line test summary
- Your concerns, if any
- The report file path
