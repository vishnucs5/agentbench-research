import { Link } from "react-router-dom"
import {
  FileSearch,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Activity,
} from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import StatusBadge from "@/components/dashboard/StatusBadge"
import { usePlagiarismChecks } from "@/hooks/use-plagiarism"

interface PlagiarismWidgetProps {
  onOpenEmbedded?: () => void
}

export default function PlagiarismWidget({ onOpenEmbedded }: PlagiarismWidgetProps) {
  const { data, isLoading } = usePlagiarismChecks(1, 50)

  const checks = data?.checks ?? []
  const totalChecked = data?.total ?? 0

  // Calculate aggregates
  let avgOriginality = 100
  let avgSimilarity = 0
  let highSimilarityCount = 0

  if (checks.length > 0) {
    const sumOriginality = checks.reduce((acc, c) => acc + c.originality_score, 0)
    const sumSimilarity = checks.reduce((acc, c) => acc + c.overall_similarity, 0)
    avgOriginality = sumOriginality / checks.length
    avgSimilarity = (sumSimilarity / checks.length) * 100
    highSimilarityCount = checks.filter(
      (c) => c.overall_similarity >= 0.3 || c.originality_score < 70
    ).length
  }

  const latestScan = checks[0]

  return (
    <Card className="bg-panel border-border p-6 shadow-sm relative overflow-hidden">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-border/60">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <FileSearch size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">Plagiarism & Similarity</h3>
              <Badge
                variant="outline"
                className="text-[10px] font-semibold border-accent/30 bg-accent/10 text-accent font-mono"
              >
                Corpus Index
              </Badge>
            </div>
            <p className="text-xs text-muted">
              Evidence-grounded text overlap detection against research literature
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onOpenEmbedded && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onOpenEmbedded}
              className="text-xs border-border bg-panel text-white hover:bg-panel-light h-8"
            >
              Quick Check Below
            </Button>
          )}
          <Button
            asChild
            size="sm"
            className="text-xs bg-accent text-black font-semibold hover:bg-accent/90 gap-1.5 h-8"
          >
            <Link to="/dashboard/plagiarism-checker">
              <span>Open Plagiarism Checker</span>
              <ArrowRight size={13} />
            </Link>
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-4">
        {/* Total Checked */}
        <div className="p-3 rounded-lg bg-panel-light/30 border border-border">
          <div className="flex items-center justify-between text-muted text-[10px] uppercase font-semibold tracking-wider mb-1">
            <span>Documents Checked</span>
            <FileText size={12} />
          </div>
          <p className="font-mono text-xl font-bold text-white">
            {isLoading ? "..." : totalChecked}
          </p>
        </div>

        {/* Avg Originality */}
        <div className="p-3 rounded-lg bg-panel-light/30 border border-border">
          <div className="flex items-center justify-between text-muted text-[10px] uppercase font-semibold tracking-wider mb-1">
            <span>Avg Originality</span>
            <ShieldCheck size={12} className="text-accent" />
          </div>
          <p className="font-mono text-xl font-bold text-accent">
            {isLoading ? "..." : totalChecked === 0 ? "—" : `${avgOriginality.toFixed(1)}%`}
          </p>
        </div>

        {/* Avg Similarity */}
        <div className="p-3 rounded-lg bg-panel-light/30 border border-border">
          <div className="flex items-center justify-between text-muted text-[10px] uppercase font-semibold tracking-wider mb-1">
            <span>Avg Similarity</span>
            <AlertTriangle size={12} className="text-amber-400" />
          </div>
          <p className="font-mono text-xl font-bold text-coral">
            {isLoading ? "..." : totalChecked === 0 ? "—" : `${avgSimilarity.toFixed(1)}%`}
          </p>
        </div>

        {/* High-Similarity Count */}
        <div className="p-3 rounded-lg bg-panel-light/30 border border-border">
          <div className="flex items-center justify-between text-muted text-[10px] uppercase font-semibold tracking-wider mb-1">
            <span>High Overlap</span>
            <AlertTriangle size={12} className="text-red-400" />
          </div>
          <p className="font-mono text-xl font-bold text-white">
            {isLoading ? "..." : highSimilarityCount}
          </p>
        </div>

        {/* Latest Scan Status */}
        <div className="p-3 rounded-lg bg-panel-light/30 border border-border col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-muted text-[10px] uppercase font-semibold tracking-wider mb-1">
            <span>Latest Status</span>
            <Activity size={12} />
          </div>
          <div className="pt-0.5">
            {isLoading ? (
              <span className="text-xs text-muted font-mono">...</span>
            ) : latestScan ? (
              <StatusBadge status={latestScan.status} />
            ) : (
              <span className="text-xs text-muted">No scans yet</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}
