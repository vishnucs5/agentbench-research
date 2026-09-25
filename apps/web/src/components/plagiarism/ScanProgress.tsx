import { useEffect, useState } from "react"
import { CheckCircle2, Loader2, FileSearch, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

interface ScanProgressProps {
  statusMessage?: string
}

const STAGES = [
  { id: 1, title: "Extracting text", description: "Parsing structure, removing noise & normalizing" },
  { id: 2, title: "Comparing content", description: "Evaluating n-grams, TF-IDF vectors & MinHash signatures" },
  { id: 3, title: "Preparing report", description: "Aligning passage offsets & compiling match metrics" },
]

export default function ScanProgress({ statusMessage }: ScanProgressProps) {
  const [currentStage, setCurrentStage] = useState(1)

  useEffect(() => {
    // Advance stage animation over time for realistic feedback while request is processing
    const t1 = setTimeout(() => setCurrentStage(2), 1200)
    const t2 = setTimeout(() => setCurrentStage(3), 2600)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [])

  return (
    <Card className="bg-panel border-border shadow-md overflow-hidden">
      {/* Top pulsing accent bar */}
      <div className="h-1 bg-panel-light w-full overflow-hidden">
        <div className="h-full bg-accent animate-pulse w-full" />
      </div>

      <CardContent className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-10 w-10 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <FileSearch size={20} className="animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">
              {statusMessage || "Analyzing your content..."}
            </h3>
            <p className="text-xs text-muted">
              Scanning against stored research papers and external citation sources. Please do not close this window.
            </p>
          </div>
        </div>

        {/* Stepper */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4" role="status" aria-live="polite">
          {STAGES.map((stage) => {
            const isCompleted = stage.id < currentStage
            const isCurrent = stage.id === currentStage

            return (
              <div
                key={stage.id}
                className={`p-4 rounded-xl border transition-all ${
                  isCurrent
                    ? "bg-panel-light border-accent/40 ring-1 ring-accent/20"
                    : isCompleted
                    ? "bg-panel-light/40 border-emerald-500/30"
                    : "bg-panel-light/20 border-border opacity-50"
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  {isCompleted ? (
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 size={16} className="text-accent animate-spin shrink-0" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border border-muted shrink-0 flex items-center justify-center text-[10px] text-muted font-mono">
                      {stage.id}
                    </div>
                  )}
                  <span
                    className={`text-xs font-semibold ${
                      isCurrent ? "text-accent" : isCompleted ? "text-emerald-400" : "text-muted"
                    }`}
                  >
                    Step {stage.id}: {stage.title}
                  </span>
                </div>
                <p className="text-[11px] text-muted pl-6">{stage.description}</p>
              </div>
            )
          })}
        </div>

        <div className="mt-4 flex items-center justify-between text-xs text-muted pt-3 border-t border-border">
          <span className="flex items-center gap-1.5">
            <Sparkles size={12} className="text-accent" />
            <span>Multi-method similarity analysis active</span>
          </span>
          <span className="font-mono text-[11px]">Est. time: &lt; 5s</span>
        </div>
      </CardContent>
    </Card>
  )
}
