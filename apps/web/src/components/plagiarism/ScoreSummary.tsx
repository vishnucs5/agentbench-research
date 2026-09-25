import { ShieldCheck, AlertTriangle, Layers, Activity } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import StatusBadge from "@/components/dashboard/StatusBadge"

interface ScoreSummaryProps {
  originalityScore: number
  overallSimilarity: number
  totalMatches: number
  status: string
}

export default function ScoreSummary({
  originalityScore,
  overallSimilarity,
  totalMatches,
  status,
}: ScoreSummaryProps) {
  // Determine interpretation based on originality score (0-100)
  let interpretation = "High originality"
  let interpretationColor = "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"

  if (originalityScore < 70) {
    interpretation = "High similarity detected"
    interpretationColor = "border-red-500/30 bg-red-500/10 text-red-400"
  } else if (originalityScore < 90) {
    interpretation = "Moderate similarity detected"
    interpretationColor = "border-amber-500/30 bg-amber-500/10 text-amber-400"
  }

  const similarityPercent = (overallSimilarity * 100).toFixed(1)

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Originality Score */}
      <Card className="bg-panel border-border p-5 border-l-4 border-l-accent relative overflow-hidden">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Originality Score
          </p>
          <ShieldCheck size={16} className="text-accent" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-3xl font-bold text-white">
            {originalityScore.toFixed(1)}%
          </span>
        </div>
        <div className="mt-2">
          <Badge variant="outline" className={`text-[10px] font-semibold ${interpretationColor}`}>
            {interpretation}
          </Badge>
        </div>
      </Card>

      {/* Similarity Percentage */}
      <Card className="bg-panel border-border p-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Potentially Similar Content
          </p>
          <AlertTriangle size={16} className="text-amber-400" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-3xl font-bold text-white">
            {similarityPercent}%
          </span>
        </div>
        <p className="mt-2 text-xs text-muted">
          Text overlap across indexed documents
        </p>
      </Card>

      {/* Potential Matches */}
      <Card className="bg-panel border-border p-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Potential Matches
          </p>
          <Layers size={16} className="text-cyan" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-3xl font-bold text-white">
            {totalMatches}
          </span>
          <span className="text-xs text-muted">passages</span>
        </div>
        <p className="mt-2 text-xs text-muted">
          {totalMatches === 0
            ? "No overlapping sections found"
            : `${totalMatches} passage(s) flagged for manual review`}
        </p>
      </Card>

      {/* Scan Status */}
      <Card className="bg-panel border-border p-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Scan Status
          </p>
          <Activity size={16} className="text-muted" />
        </div>
        <div className="flex items-center gap-2 mt-1">
          <StatusBadge status={status} />
        </div>
        <p className="mt-3 text-xs text-muted">
          Scores reflect overlap, not definitive plagiarism.
        </p>
      </Card>
    </div>
  )
}
