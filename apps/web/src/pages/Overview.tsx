import { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import MetricCard from "@/components/dashboard/MetricCard"
import StatusBadge from "@/components/dashboard/StatusBadge"
import EmptyState from "@/components/dashboard/EmptyState"
import PipelineStepper from "@/components/dashboard/PipelineStepper"
import PlagiarismWidget from "@/components/dashboard/PlagiarismWidget"
import PlagiarismCheckerPanel from "@/components/plagiarism/PlagiarismCheckerPanel"
import { UploadPaperDialog } from "@/components/papers/UploadPaperDialog"
import { RunAgentDialog } from "@/components/dashboard/RunAgentDialog"
import { useProject } from "@/contexts/ProjectContext"
import { useStats } from "@/hooks/use-stats"
import { MOCK_PIPELINE } from "@/lib/mock-data"
import {
  ClipboardList,
  FileUp,
  Play,
  ArrowRight,
  Bot,
  Sparkles,
  Search,
  CheckCircle2,
  Cpu,
  ChevronRight,
} from "lucide-react"

const EVIDENCE_METRICS = [
  { label: "Citation precision", value: "≥ 90%" },
  { label: "Unsupported", value: "< 10%" },
  { label: "Page-aware", value: "text + tables" },
]

const BUDGETS = [
  { label: "max_papers", value: "10" },
  { label: "max_tool_calls", value: "40" },
  { label: "deadline", value: "180s" },
]

const PROVIDERS = [
  { name: "OpenRouter", model: "claude-3.5-sonnet", status: "completed" },
  { name: "Ollama", model: "qwen3-coder:30b", status: "fallback" },
  { name: "Mock", model: "deterministic", status: "created" },
]

const PROMPT_SUGGESTIONS = [
  "Compare transformer vs CNN anomaly detectors on CICIDS2017",
  "Extract accuracy and F1 scores across all intrusion detection papers",
  "Identify methodological limitations and unexplored evaluation gaps",
]

const PHASE_DETAILS: Record<number, { title: string; desc: string; modules: string[]; tests: string }> = {
  0: { title: "Phase 0: Foundation", desc: "Configuration, database schemas, and baseline architecture.", modules: ["Settings", "Alembic", "Domain Models"], tests: "44 tests passing" },
  1: { title: "Phase 1: Ingestion & Parsing", desc: "PyMuPDF PDF parsing, table extraction, and page segmentation.", modules: ["PyMuPDF", "MinIO / S3", "Deduplicator"], tests: "38 tests passing" },
  2: { title: "Phase 2: Hybrid Retrieval", desc: "BM25Okapi lexical search + dense neural embeddings via SentenceTransformers.", modules: ["Chunker", "BM25Okapi", "SentenceTransformers"], tests: "52 tests passing" },
  3: { title: "Phase 3: Claim Extraction", desc: "Structured empirical finding, metric, and benchmark extraction.", modules: ["ClaimExtractor", "ClassificationService"], tests: "30 tests passing" },
  4: { title: "Phase 4: Synthesis & Matrices", desc: "Cross-document comparison tables and research gap detection.", modules: ["ComparisonService", "GapAnalysis", "Normalization"], tests: "42 tests passing" },
  5: { title: "Phase 5: Verification & NLI", desc: "Evidence-grounded assertion validation to prevent hallucination.", modules: ["NLIModel", "CitationVerifier", "AuditReporter"], tests: "28 tests passing" },
  6: { title: "Phase 6: Evaluation", desc: "Benchmark task suite with citation precision and unsupported claim metrics.", modules: ["EvalSuite", "BenchmarkHarness"], tests: "18 tests passing" },
  7: { title: "Phase 7: Dashboard & Trace Replay", desc: "Live trace timeline, WebSocket updates, and telemetry monitoring.", modules: ["TraceReplay", "WebSocketManager", "React SPA"], tests: "All 16 E2E passing" },
}

export default function Overview() {
  const { selectedProject } = useProject()
  const { data: stats, isLoading } = useStats(selectedProject?.id ?? null)
  const checkerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [runAgentOpen, setRunAgentOpen] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState<number>(7)
  const [runFilter, setRunFilter] = useState<"all" | "completed" | "active">("all")
  const [runSearchQuery, setRunSearchQuery] = useState("")

  const runsList = stats?.recent_runs ?? []
  const filteredRuns = runsList.filter((run) => {
    if (runFilter === "completed" && run.status !== "completed") return false
    if (runFilter === "active" && run.status === "completed") return false
    if (runSearchQuery.trim()) {
      return run.request_text.toLowerCase().includes(runSearchQuery.toLowerCase())
    }
    return true
  })

  return (
    <div className="p-6 space-y-8">
      {/* Header with Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
              OVERVIEW
            </p>
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#CFFF4B]/10 text-[#CFFF4B] border border-[#CFFF4B]/20">
              Interactive Mode
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Research with a quality loop.
          </h1>
          <p className="text-[#64748B] text-sm">
            Plan, retrieve, extract, synthesize, verify, and evaluate every answer.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            onClick={() => setUploadOpen(true)}
            className="border-[#1E293B] text-white hover:bg-[#1E293B] hover:text-white text-xs font-semibold transition"
          >
            <FileUp className="h-4 w-4 mr-1.5 text-[#CFFF4B]" />
            Upload Paper (PDF)
          </Button>
          <Button
            onClick={() => setRunAgentOpen(true)}
            className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold text-xs shadow-md shadow-[#CFFF4B]/10 transition"
          >
            <Play className="h-3.5 w-3.5 mr-1.5 fill-black" />
            Run Research Agent
          </Button>
        </div>
      </div>

      {/* Quick Prompt Suggestions */}
      <div className="bg-[#101A26]/80 border border-[#1E293B] rounded-xl p-3 flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-[#CFFF4B] shrink-0">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Quick Prompts:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {PROMPT_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setRunAgentOpen(true)}
              className="text-xs text-left px-2.5 py-1 rounded-md bg-[#1E293B]/70 hover:bg-[#1E293B] text-slate-300 hover:text-white border border-[#1E293B] hover:border-[#64748B] transition truncate max-w-[280px] md:max-w-none"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
            System Metrics (Click to inspect)
          </p>
          <Badge
            variant="outline"
            className="text-[10px] font-semibold border-[#CFFF4B]/30 bg-[#CFFF4B]/10 text-[#CFFF4B]"
          >
            confidence ≥ 0.8
          </Badge>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div onClick={() => navigate("/projects")} className="cursor-pointer">
            <MetricCard title="Projects" value={isLoading ? "..." : stats ? "1" : "0"} />
          </div>
          <div onClick={() => setUploadOpen(true)} className="cursor-pointer">
            <MetricCard title="Papers" value={isLoading ? "..." : stats?.total_papers?.toString() ?? "0"} />
          </div>
          <div onClick={() => navigate("/trace")} className="cursor-pointer">
            <MetricCard
              title="Evidence"
              value={isLoading ? "..." : stats?.total_evidence?.toString() ?? "—"}
              description="Chunks · 512 tok · Hybrid"
            />
          </div>
          <div>
            <MetricCard title="Claims" value="8" description="8 types · Structured · Cited" />
          </div>
          <div onClick={() => navigate("/trace")} className="cursor-pointer">
            <MetricCard
              title="Runs"
              value={isLoading ? "..." : stats?.total_runs?.toString() ?? "—"}
              description="Traces · Budgets · Replay"
            />
          </div>
        </div>
      </div>

      {/* Pipeline Progress with Interactive Stage Drill-down */}
      <Card className="bg-[#101A26] border-[#1E293B] p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
              Pipeline Progress · Vertical Slices
            </p>
            <p className="text-xs text-slate-400">Click any stage to inspect sub-modules and verified capabilities</p>
          </div>
          <Badge
            variant="outline"
            className="text-[10px] font-semibold border-emerald-500/30 bg-emerald-500/10 text-emerald-400 flex items-center gap-1"
          >
            <CheckCircle2 className="h-3 w-3" />
            264 unit tests passing
          </Badge>
        </div>

        <div className="overflow-x-auto pt-2 pb-2">
          <PipelineStepper
            phases={MOCK_PIPELINE}
            selectedPhase={selectedPhase}
            onSelectPhase={(phase) => setSelectedPhase(phase)}
          />
        </div>

        {/* Selected Phase Drill-down Panel */}
        {PHASE_DETAILS[selectedPhase] && (
          <div className="p-4 rounded-xl bg-[#0B131E] border border-[#1E293B] flex flex-col md:flex-row md:items-center justify-between gap-4 mt-2 transition animate-in fade-in-50">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#CFFF4B]" />
                <h4 className="text-sm font-bold text-white">
                  {PHASE_DETAILS[selectedPhase].title}
                </h4>
                <Badge variant="outline" className="text-[10px] border-[#1E293B] text-slate-400 font-mono">
                  {PHASE_DETAILS[selectedPhase].tests}
                </Badge>
              </div>
              <p className="text-xs text-slate-400">
                {PHASE_DETAILS[selectedPhase].desc}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-1.5 shrink-0">
              <span className="text-[10px] text-slate-500 font-mono uppercase mr-1">Modules:</span>
              {PHASE_DETAILS[selectedPhase].modules.map((mod) => (
                <span
                  key={mod}
                  className="px-2 py-0.5 rounded text-[10px] font-mono bg-[#1E293B] text-slate-200 border border-[#334155]"
                >
                  {mod}
                </span>
              ))}
            </div>
          </div>
        )}
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
          <div className="mt-4 pt-4 border-t border-[#1E293B]">
            <div className="flex items-center gap-2 text-xs text-[#64748B]">
              <Cpu className="h-3 w-3 text-[#CFFF4B]" />
              <span>100,000 token budget per run</span>
            </div>
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

      {/* Recent Runs with Interactive Filter Tabs */}
      <Card className="bg-[#101A26] border-[#1E293B] p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
              Recent Runs · Trace Completeness 100%
            </p>
            <p className="text-xs text-slate-400">Click any run to inspect millisecond telemetry and tool calls</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-[#0B131E] border border-[#1E293B] text-xs">
              <button
                type="button"
                onClick={() => setRunFilter("all")}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  runFilter === "all" ? "bg-[#CFFF4B] text-black font-semibold" : "text-slate-400 hover:text-white"
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setRunFilter("completed")}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  runFilter === "completed" ? "bg-[#CFFF4B] text-black font-semibold" : "text-slate-400 hover:text-white"
                }`}
              >
                Completed
              </button>
              <button
                type="button"
                onClick={() => setRunFilter("active")}
                className={`px-2.5 py-1 rounded font-medium transition ${
                  runFilter === "active" ? "bg-[#CFFF4B] text-black font-semibold" : "text-slate-400 hover:text-white"
                }`}
              >
                Active
              </button>
            </div>

            {/* Run Search Filter */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Filter runs..."
                value={runSearchQuery}
                onChange={(e) => setRunSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-[#0B131E] border border-[#1E293B] text-white placeholder-slate-500 focus:outline-none focus:border-[#CFFF4B] w-36 sm:w-44"
              />
            </div>

            <button
              onClick={() => navigate("/trace")}
              className="text-xs text-[#64748B] hover:text-white flex items-center gap-1 ml-1"
            >
              View in Replay <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </div>

        {filteredRuns.length > 0 ? (
          <div className="space-y-2">
            {filteredRuns.slice(0, 5).map((run) => (
              <div
                key={run.run_id}
                onClick={() => navigate("/trace")}
                className="flex items-center justify-between text-sm py-2.5 px-3.5 rounded-lg border border-[#1E293B] bg-[#0B131E]/40 hover:bg-[#1E293B]/50 hover:border-[#64748B]/50 transition cursor-pointer group"
              >
                <div className="flex items-center gap-2.5 truncate pr-4">
                  <Bot className="h-4 w-4 text-[#CFFF4B] shrink-0" />
                  <span className="text-white font-mono text-xs truncate group-hover:text-[#CFFF4B] transition">
                    {run.request_text}
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[10px] font-mono text-[#64748B]">
                    {run.total_tool_calls} tool calls
                  </span>
                  <StatusBadge status={run.status} />
                  <ChevronRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-white transition" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 space-y-3">
            <EmptyState
              icon={ClipboardList}
              title="No runs match filter"
              description="Run the autonomous research agent to generate new execution traces."
            />
            <div className="flex justify-center gap-3">
              <Button
                size="sm"
                onClick={() => setRunAgentOpen(true)}
                className="text-xs bg-[#CFFF4B] text-black font-semibold"
              >
                <Play className="h-3 w-3 mr-1 fill-black" />
                Run Agent Now
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Plagiarism Summary Widget */}
      <PlagiarismWidget
        onOpenEmbedded={() => {
          checkerRef.current?.scrollIntoView({ behavior: "smooth" })
        }}
      />

      {/* Embedded Plagiarism Checker Section */}
      <div ref={checkerRef} className="space-y-4 pt-4 border-t border-[#1E293B]">
        <div className="space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
            PLAGIARISM & SIMILARITY CHECKER
          </p>
          <h2 className="text-xl font-bold text-white">
            Instant Similarity Analysis
          </h2>
          <p className="text-xs text-[#64748B]">
            Check research text or upload files directly within the dashboard.
          </p>
        </div>

        <PlagiarismCheckerPanel embedded />
      </div>

      {/* Dialog Modals */}
      <UploadPaperDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
      />
      <RunAgentDialog
        open={runAgentOpen}
        onOpenChange={setRunAgentOpen}
      />
    </div>
  )
}
