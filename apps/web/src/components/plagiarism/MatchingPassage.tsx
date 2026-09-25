import { useState } from "react"
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { PlagiarismMatch } from "@/types"

interface MatchingPassageProps {
  match: PlagiarismMatch
  index: number
}

export default function MatchingPassage({ match, index }: MatchingPassageProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const similarityPct = (match.similarity_score * 100).toFixed(1)
  const confidencePct = (match.confidence_score * 100).toFixed(0)

  // Style badge based on severity
  let badgeColor = "border-blue-500/30 bg-blue-500/10 text-blue-400"
  if (match.similarity_score >= 0.7) {
    badgeColor = "border-red-500/30 bg-red-500/10 text-red-400"
  } else if (match.similarity_score >= 0.4) {
    badgeColor = "border-amber-500/30 bg-amber-500/10 text-amber-400"
  }

  return (
    <div className="rounded-xl border border-border bg-panel-light/40 overflow-hidden transition-all">
      {/* Header bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-panel-light/70 transition-colors select-none"
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-panel text-xs font-mono font-bold text-muted border border-border">
            {index + 1}
          </span>
          <div className="overflow-hidden">
            <p className="text-sm font-semibold text-white truncate">
              {match.source_document_title || "Indexed Corpus Document"}
            </p>
            <p className="text-xs text-muted">
              Source Type: <span className="font-mono text-white/80">{match.source_type}</span>
              {match.source_location && (
                <> · Location: <span className="text-white/80">{match.source_location}</span></>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <Badge variant="outline" className={`text-xs font-mono font-bold ${badgeColor}`}>
            {similarityPct}% overlap
          </Badge>

          <span className="hidden sm:inline-block text-xs font-mono text-muted">
            {confidencePct}% conf.
          </span>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted hover:text-white"
            aria-label={isExpanded ? "Collapse match details" : "Expand match details"}
          >
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </Button>
        </div>
      </div>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-border/60 mt-1 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            {/* Submitted Excerpt */}
            <div className="rounded-lg p-3.5 bg-panel border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-muted pb-1 border-b border-border/40">
                <span className="font-semibold text-white">Your Submitted Excerpt</span>
                {match.match_start_offset !== null && match.match_end_offset !== null && (
                  <span className="font-mono text-[10px]">
                    Offset: {match.match_start_offset}–{match.match_end_offset}
                  </span>
                )}
              </div>
              <p className="text-xs leading-relaxed text-white/95 font-sans">
                <mark className="bg-amber-400/20 text-amber-200 px-1 py-0.5 rounded font-medium border-b border-amber-400/40">
                  {match.matched_text}
                </mark>
              </p>
            </div>

            {/* Matched Source Excerpt */}
            <div className="rounded-lg p-3.5 bg-panel border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-muted pb-1 border-b border-border/40">
                <span className="font-semibold text-white">Matched Source Excerpt</span>
                {match.source_url && (
                  <a
                    href={match.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-accent hover:underline text-[11px]"
                  >
                    <span>View Source</span>
                    <ExternalLink size={11} />
                  </a>
                )}
              </div>
              <p className="text-xs leading-relaxed text-white/95 font-sans">
                <mark className="bg-amber-400/20 text-amber-200 px-1 py-0.5 rounded font-medium border-b border-amber-400/40">
                  {match.source_text || match.matched_text}
                </mark>
              </p>
            </div>
          </div>

          {/* Footer with metadata */}
          <div className="flex items-center justify-between text-[11px] text-muted pt-2 border-t border-border/40 flex-wrap gap-2">
            <span>
              Comparison metric: TF-IDF n-gram vector alignment (confidence: {confidencePct}%)
            </span>
            {match.source_url && (
              <a
                href={match.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted hover:text-accent flex items-center gap-1 truncate max-w-xs"
              >
                <span className="truncate">{match.source_url}</span>
                <ExternalLink size={10} className="shrink-0" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
