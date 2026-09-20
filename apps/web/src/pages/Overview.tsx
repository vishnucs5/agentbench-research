import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import MetricCard from "@/components/dashboard/MetricCard"
import StatusBadge from "@/components/dashboard/StatusBadge"
import EmptyState from "@/components/dashboard/EmptyState"
import PipelineStepper from "@/components/dashboard/PipelineStepper"
import { MOCK_STATS, MOCK_PIPELINE } from "@/lib/mock-data"
import { FileText, Search, GitCompare, Activity, ClipboardList } from "lucide-react"

const QUICK_ACTIONS = [
  { label: "Upload PDF", icon: FileText },
  { label: "Search", icon: Search },
  { label: "Compare", icon: GitCompare },
  { label: "Benchmark", icon: Activity },
]

const PROVIDERS = [
  { name: "OpenRouter", model: "claude-3.5-sonnet", status: "completed" },
  { name: "Ollama", model: "qwen3-coder:30b", status: "fallback" },
  { name: "Mock", model: "deterministic", status: "created" },
]

const BUDGETS = [
  { label: "max_papers", value: "10" },
  { label: "max_tool_calls", value: "40" },
  { label: "deadline", value: "180s" },
]

const EVIDENCE_METRICS = [
  { label: "Citation precision", value: "≥ 90%" },
  { label: "Unsupported", value: "< 10%" },
  { label: "Page-aware", value: "text + tables" },
]

export default function Overview() {
  const stats = MOCK_STATS

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
          OVERVIEW
        </p>
        <h1 className="text-3xl font-bold text-white">
          Research with a quality loop.
        </h1>
        <p className="text-[#64748B]">
          Plan, retrieve, extract, synthesize, verify, and evaluate every answer.
        </p>
      </div>

      {/* Metric Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
            Metrics
          </p>
          <Badge
            variant="outline"
            className="text-[10px] font-semibold border-[#CFFF4B]/30 bg-[#CFFF4B]/10 text-[#CFFF4B]"
          >
            confidence ≥ 0.8
          </Badge>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <MetricCard title="Projects" value="0" />
          <MetricCard title="Papers" value={stats.total_papers ?? "0"} />
          <MetricCard
            title="Evidence"
            value={stats.total_evidence ?? "—"}
            description="Chunks · 512 tok · Hybrid"
          />
          <MetricCard title="Claims" value="—" description="8 types · Structured · Cited" />
          <MetricCard title="Runs" value={stats.total_runs ?? "—"} description="Traces · Budgets · Replay" />
        </div>
      </div>

      {/* Pipeline Progress */}
      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="space-y-1">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
              Pipeline Progress · Vertical Slices
            </p>
          </div>
          <Badge
            variant="outline"
            className="text-[10px] font-semibold border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
          >
            110 tests passing
          </Badge>
        </div>
        <div className="overflow-x-auto pt-2 pb-4">
          <PipelineStepper phases={MOCK_PIPELINE} />
        </div>
      </Card>

      {/* Three-column row: Evidence, Budgets, Providers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Evidence-Grounded Answering */}
        <Card className="bg-[#101A26] border-[#1E293B] p-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-2">
            Evidence-Grounded Answering
          </p>
          <p className="text-white font-medium mb-4">Every claim → page</p>
          <div className="space-y-2">
            {EVIDENCE_METRICS.map((m) => (
              <div key={m.label} className="flex items-center justify-between text-sm">
                <span className="text-[#64748B]">{m.label}</span>
                <span className="font-mono text-white">{m.value}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-[#1E293B]">
            <div className="flex items-center gap-2 text-xs text-[#64748B]">
              <span className="inline-block h-2 w-2 rounded-full bg-[#CFFF4B]" />
              <span>Citation index mapped to page references</span>
            </div>
          </div>
        </Card>

        {/* Bounded Agent Budgets */}
        <Card className="bg-[#101A26] border-[#1E293B] p-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-2">
            Bounded Agent Budgets
          </p>
          <div className="space-y-3 mt-4">
            {BUDGETS.map((b) => (
              <div key={b.label} className="flex items-center justify-between text-sm">
                <span className="text-[#64748B] font-mono text-xs">{b.label}</span>
                <span className="font-mono text-white font-bold">{b.value}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Model Providers */}
        <Card className="bg-[#101A26] border-[#1E293B] p-6">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-2">
            Model Providers
          </p>
          <div className="space-y-3 mt-4">
            {PROVIDERS.map((p) => (
              <div key={p.name} className="flex items-center justify-between text-sm">
                <div className="space-y-0.5">
                  <p className="text-white font-medium">{p.name}</p>
                  <p className="text-[#64748B] font-mono text-xs">{p.model}</p>
                </div>
                <StatusBadge status={p.status} />
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Quick Actions */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-3">
          Quick Actions
        </p>
        <div className="flex flex-wrap gap-3">
          {QUICK_ACTIONS.map((action) => (
            <Button
              key={action.label}
              variant="outline"
              className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B] hover:bg-[#101A26]"
            >
              <action.icon className="h-4 w-4" />
              {action.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Recent Runs */}
      <Card className="bg-[#101A26] border-[#1E293B] p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B] mb-2">
          Recent Runs · Trace Completeness 100%
        </p>
        <EmptyState
          icon={ClipboardList}
          title="No runs yet"
          description="Upload a paper to start. Traces are redacted and retained per retention policy."
        />
      </Card>
    </div>
  )
}
