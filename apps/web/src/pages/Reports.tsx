import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import {
  ChevronRight,
  Download,
  Copy,
  Check,
  RefreshCw,
  FileCode,
  BookOpen,
  FileText,
  ShieldAlert,
  FolderOpen,
  Sparkles,
} from "lucide-react"
import { useProject } from "@/contexts/ProjectContext"
import { reportsApi } from "@/lib/api"
import type { ReportType, ReportPreviewResponse } from "@/types"

interface ReportTabOption {
  id: ReportType
  label: string
  extension: string
  icon: React.ReactNode
  description: string
  badge: string
}

const REPORT_TABS: ReportTabOption[] = [
  {
    id: "latex",
    label: "LaTeX Manuscript",
    extension: ".tex",
    icon: <FileCode size={18} />,
    description: "Compile-ready IEEEtran two-column survey article with synthesis table and cite commands.",
    badge: "IEEE / ACM Ready",
  },
  {
    id: "bibtex",
    label: "BibTeX Citations",
    extension: ".bib",
    icon: <BookOpen size={18} />,
    description: "Standardized bibliographic references with deterministic cite keys and verified DOIs.",
    badge: "Zotero / Overleaf",
  },
  {
    id: "markdown",
    label: "Markdown Literature Survey",
    extension: ".md",
    icon: <FileText size={18} />,
    description: "Comprehensive structured report with catalog, synthesis matrices, and identified research gaps.",
    badge: "GitHub Flavored",
  },
  {
    id: "audit",
    label: "Claim Audit Log",
    extension: ".md",
    icon: <ShieldAlert size={18} />,
    description: "NLI verification provenance trail cross-linking extracted claims to exact chunk IDs and pages.",
    badge: "Strict Grounding",
  },
]

export default function Reports() {
  const { projects, selectedProject, setSelectedProject } = useProject()
  const [activeTab, setActiveTab] = useState<ReportType>("latex")
  const [customTitle, setCustomTitle] = useState("")
  const [preview, setPreview] = useState<ReportPreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const activeOption: ReportTabOption =
    REPORT_TABS.find((t) => t.id === activeTab) ?? (REPORT_TABS[0] as ReportTabOption)

  useEffect(() => {
    if (selectedProject) {
      loadPreview()
    }
  }, [selectedProject?.id, activeTab])

  async function loadPreview() {
    if (!selectedProject) return
    try {
      setLoading(true)
      setError(null)
      const res = await reportsApi.preview({
        project_id: selectedProject.id,
        report_type: activeTab,
        custom_title: customTitle.trim() || undefined,
      })
      setPreview(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report preview")
    } finally {
      setLoading(false)
    }
  }

  function handleCopy() {
    if (!preview?.content) return
    navigator.clipboard.writeText(preview.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function handleDownload() {
    if (!selectedProject) return
    const url = reportsApi.exportUrl(selectedProject.id, activeTab)
    const a = document.createElement("a")
    a.href = url
    // Set token authorization if needed or trigger download directly
    a.download = preview?.filename || `report_${activeTab}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Breadcrumb & Header */}
      <div className="space-y-2">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-foreground transition-colors">
            Overview
          </Link>
          <ChevronRight size={12} />
          <span className="text-foreground font-medium">Reports & Exports</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
                PUBLISHING & SYNTHESIS SUITE
              </p>
              <span className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-0.5 text-[10px] font-mono font-medium text-accent">
                IEEE · ACM · BibTeX · NLI
              </span>
            </div>
            <h1 className="text-3xl font-bold text-foreground tracking-tight">
              Reports & Manuscript Exports
            </h1>
            <p className="text-sm text-muted-foreground max-w-2xl">
              Export compile-ready LaTeX articles, structured BibTeX citations, survey digests, and claim verification logs grounded in your ingested literature.
            </p>
          </div>

          {/* Project Selector dropdown */}
          <div className="flex items-center gap-3 bg-panel border border-border p-2 rounded-xl">
            <FolderOpen size={16} className="text-accent ml-1" />
            <select
              value={selectedProject?.id || ""}
              onChange={(e) => {
                const found = projects.find((p) => p.id === e.target.value)
                if (found) setSelectedProject(found)
              }}
              className="bg-transparent text-sm text-foreground focus:outline-none pr-3"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-panel text-foreground">
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {REPORT_TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col text-left p-4 rounded-xl border transition-all ${
                isActive
                  ? "bg-accent/10 border-accent text-foreground shadow-sm shadow-accent/5"
                  : "bg-panel border-border text-muted-foreground hover:bg-panel-light hover:text-foreground"
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <div className={`p-2 rounded-lg ${isActive ? "bg-accent text-accent-foreground" : "bg-panel-light text-muted-foreground"}`}>
                  {tab.icon}
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-border text-muted-foreground">
                  {tab.badge}
                </span>
              </div>
              <span className="font-semibold text-sm text-foreground">{tab.label}</span>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                {tab.description}
              </p>
            </button>
          )
        })}
      </div>

      {/* Action Toolbar & Custom Options */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-xl bg-panel border border-border">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <input
            type="text"
            placeholder="Custom Manuscript Title (optional)..."
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
            className="w-full text-xs px-3 py-2 rounded-lg bg-panel-light border border-border text-foreground focus:outline-none focus:border-accent"
          />
          <button
            onClick={loadPreview}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-panel-light hover:bg-border text-foreground transition-colors shrink-0"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>Apply</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            disabled={!preview?.content}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-panel-light border border-border hover:bg-border text-foreground transition-colors"
          >
            {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
            <span>{copied ? "Copied!" : "Copy Code"}</span>
          </button>

          <button
            onClick={handleDownload}
            disabled={!selectedProject}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 transition-colors shadow-sm"
          >
            <Download size={14} />
            <span>Download {activeOption.extension}</span>
          </button>
        </div>
      </div>

      {/* Preview Output Panel */}
      <div className="rounded-xl border border-border bg-panel overflow-hidden shadow-sm">
        {/* Panel Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-panel-light text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="font-mono text-foreground font-semibold">
              {preview?.filename || `manuscript${activeOption.extension}`}
            </span>
            {preview && (
              <span className="text-[11px] text-muted-foreground">
                ({preview.line_count} lines · {preview.char_count.toLocaleString()} chars)
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px]">
              <Sparkles size={12} className="text-accent" />
              Generated live from database evidence
            </span>
          </div>
        </div>

        {/* Panel Content */}
        <div className="p-4">
          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center gap-3 text-muted-foreground">
              <RefreshCw size={28} className="animate-spin text-accent" />
              <p className="text-sm">Synthesizing evidence and compiling {activeOption.label}...</p>
            </div>
          ) : error ? (
            <div className="p-6 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <p className="font-semibold mb-1">Error Generating Preview</p>
              <p>{error}</p>
            </div>
          ) : preview?.content ? (
            <pre className="font-mono text-xs text-foreground bg-[#0a0f1d] p-5 rounded-lg overflow-x-auto max-h-[600px] leading-relaxed border border-border/50">
              <code>{preview.content}</code>
            </pre>
          ) : (
            <div className="py-20 text-center text-muted-foreground space-y-2">
              <BookOpen size={36} className="mx-auto text-muted-foreground/50 mb-2" />
              <p className="text-sm font-medium">No report generated yet</p>
              <p className="text-xs">Ensure your project has indexed research papers to generate complete reports.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
