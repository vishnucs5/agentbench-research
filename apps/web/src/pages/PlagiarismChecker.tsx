import { Link } from "react-router-dom"
import { ChevronRight, ShieldCheck } from "lucide-react"
import PlagiarismCheckerPanel from "@/components/plagiarism/PlagiarismCheckerPanel"

export default function PlagiarismChecker() {
  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto">
      {/* Breadcrumb & Header */}
      <div className="space-y-2">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted">
          <Link to="/" className="hover:text-white transition-colors">
            Overview
          </Link>
          <ChevronRight size={12} />
          <span className="text-white font-medium">Plagiarism Checker</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent">
                EVIDENCE ANALYSIS
              </p>
              <span className="inline-flex items-center gap-1 rounded-md bg-accent/10 px-2 py-0.5 text-[10px] font-mono font-medium text-accent">
                TF-IDF · MinHash
              </span>
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Plagiarism Checker
            </h1>
            <p className="text-sm text-muted max-w-2xl">
              Check your content for potentially similar passages against repository papers and external literature references.
            </p>
          </div>

          {/* Info Badge / Disclaimer */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-panel border border-border text-xs text-muted max-w-xs shrink-0">
            <ShieldCheck size={16} className="text-accent shrink-0" />
            <span>Scores evaluate textual overlap. Review flagged sections in context.</span>
          </div>
        </div>
      </div>

      {/* Main Checker Workflow + Scan History on same page */}
      <PlagiarismCheckerPanel />
    </div>
  )
}
