import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Server, Database, Shield, Lock, Eye, AlertTriangle } from "lucide-react"

const PROVIDERS = [
  {
    name: "OpenRouter",
    model: "claude-3.5-sonnet",
    endpoint: "https://openrouter.ai/api/v1",
    key: "sk-or-...xxxx",
    status: "Active",
  },
  {
    name: "Ollama",
    model: "qwen3-coder:30b",
    endpoint: "http://localhost:11434",
    key: "\u2014",
    status: "Fallback",
  },
  {
    name: "Mock",
    model: "deterministic",
    endpoint: "\u2014",
    key: "\u2014",
    status: "CI",
  },
]

const BUDGETS = [
  { label: "max_papers", value: "10" },
  { label: "max_tool_calls", value: "40" },
  { label: "deadline", value: "180s" },
  { label: "token_budget", value: "100k" },
]

const RETRIEVAL = [
  { label: "Chunk size", value: "512 tok" },
  { label: "Chunk overlap", value: "50" },
  { label: "Embedding", value: "all-MiniLM-L6-v2 \u00b7 384d" },
  { label: "Hybrid", value: "BM25 0.5 + Semantic 0.5" },
  { label: "Score threshold", value: "0.0" },
  { label: "Not enough evidence", value: "< 0.3" },
]

const SECURITY_ITEMS = [
  { icon: Lock, label: "Auth", value: "JWT, RBAC (viewer / researcher / supervisor / admin)" },
  { icon: AlertTriangle, label: "Rate limit", value: "60/min \u00b7 1000/hour" },
  { icon: Shield, label: "Protections", value: "Prompt injection \u00b7 SSRF \u00b7 XSS" },
  { icon: Eye, label: "Headers", value: "CSP headers \u00b7 Redaction v1" },
  { icon: Database, label: "Data", value: "No secrets in traces \u00b7 Retention per project" },
  { icon: Server, label: "Storage", value: "SQLite (dev) / Postgres (prod)" },
]

const API_ROUTES = [
  { method: "GET", path: "/api/health" },
  { method: "POST", path: "/api/auth/login" },
  { method: "POST", path: "/api/auth/refresh" },
  { method: "GET", path: "/api/projects" },
  { method: "POST", path: "/api/projects" },
  { method: "GET", path: "/api/projects/:id" },
  { method: "PUT", path: "/api/projects/:id" },
  { method: "DELETE", path: "/api/projects/:id" },
  { method: "POST", path: "/api/projects/:id/papers" },
  { method: "GET", path: "/api/projects/:id/papers" },
  { method: "GET", path: "/api/papers/:id" },
  { method: "POST", path: "/api/papers/:id/reprocess" },
  { method: "GET", path: "/api/papers/:id/chunks" },
  { method: "GET", path: "/api/projects/:id/search" },
  { method: "POST", path: "/api/projects/:id/query" },
  { method: "GET", path: "/api/projects/:id/runs" },
  { method: "POST", path: "/api/projects/:id/runs" },
  { method: "GET", path: "/api/runs/:id" },
  { method: "GET", path: "/api/runs/:id/trace" },
  { method: "GET", path: "/api/settings" },
  { method: "PUT", path: "/api/settings" },
]

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  POST: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  PUT: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  DELETE: "bg-red-500/20 text-red-400 border-red-500/30",
}

function SectionHeader({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="h-4 w-4 text-[#CFFF4B]" />
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
        {label}
      </p>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="p-6 space-y-8">
      <div className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
          SETTINGS
        </p>
        <h1 className="text-3xl font-bold text-white">
          Settings &middot; Security &amp; Reproducibility
        </h1>
        <p className="text-[#64748B]">
          Read-only view of local defaults. Values shown are display-only for MVP.
        </p>
      </div>

      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <SectionHeader icon={Server} label="Model Providers" />
        <div className="space-y-3">
          {PROVIDERS.map((p) => (
            <div
              key={p.name}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-lg border border-[#1E293B] bg-[#0B1120] p-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-white font-medium">{p.name}</span>
                  <Badge
                    variant="outline"
                    className={
                      p.status === "Active"
                        ? "text-[10px] border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : p.status === "Fallback"
                          ? "text-[10px] border-amber-500/30 bg-amber-500/10 text-amber-400"
                          : "text-[10px] border-[#1E293B] bg-[#1E293B] text-[#64748B]"
                    }
                  >
                    {p.status}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#64748B]">
                  <span className="font-mono">{p.model}</span>
                  <span className="font-mono">{p.endpoint}</span>
                  <span className="font-mono">{p.key}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <SectionHeader icon={AlertTriangle} label="Budgets & Limits" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          {BUDGETS.map((b) => (
            <div key={b.label} className="rounded-lg border border-[#1E293B] bg-[#0B1120] p-4">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-1">
                {b.label}
              </p>
              <p className="font-mono text-white text-lg font-bold">{b.value}</p>
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-[#1E293B] bg-[#0B1120] p-3 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-[#64748B]">
            System prefers explicit <span className="font-mono text-amber-400">not_reported</span> over
            hallucination. Metric names normalized.
          </p>
        </div>
      </Card>

      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <SectionHeader icon={Database} label="Ingestion & Retrieval" />
        <div className="space-y-2">
          {RETRIEVAL.map((r) => (
            <div key={r.label} className="flex items-center justify-between text-sm py-1 border-b border-[#1E293B] last:border-0">
              <span className="text-[#64748B]">{r.label}</span>
              <span className="font-mono text-white">{r.value}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <SectionHeader icon={Shield} label="Security" />
        <div className="space-y-2">
          {SECURITY_ITEMS.map((s) => (
            <div
              key={s.label}
              className="flex items-center gap-3 rounded-lg border border-[#1E293B] bg-[#0B1120] p-4"
            >
              <s.icon className="h-4 w-4 text-[#CFFF4B] shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-0.5">
                  {s.label}
                </p>
                <p className="font-mono text-white text-sm">{s.value}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <SectionHeader icon={Lock} label="API Endpoints" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1E293B]">
                <th className="text-left py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
                  Method
                </th>
                <th className="text-left py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
                  Path
                </th>
              </tr>
            </thead>
            <tbody>
              {API_ROUTES.map((route, i) => (
                <tr key={i} className="border-b border-[#1E293B] last:border-0">
                  <td className="py-2 pr-4">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${METHOD_COLORS[route.method]}`}>
                      {route.method}
                    </span>
                  </td>
                  <td className="py-2 font-mono text-white">{route.path}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
