import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"
import { Card } from "@/components/ui/card"

interface SimilarityChartProps {
  originalityScore: number
  similarityScore: number // 0.0 to 1.0 or 0 to 100
}

export default function SimilarityChart({
  originalityScore,
  similarityScore,
}: SimilarityChartProps) {
  // Normalize similarity percentage (0-100)
  const similarityPct =
    similarityScore <= 1.0 ? similarityScore * 100 : similarityScore
  const originalityPct = Math.max(0, Math.min(100, originalityScore))
  const overlapPct = Math.max(0, Math.min(100, similarityPct))

  const data = [
    { name: "Original Content", value: originalityPct, color: "#CFFF4B" }, // Accent lime
    { name: "Potentially Similar", value: overlapPct, color: "#FF6B6B" }, // Coral/Red
  ]

  // If both zero, default to 100% original representation
  if (originalityPct === 0 && overlapPct === 0 && data[0]) {
    data[0].value = 100
  }

  return (
    <Card className="bg-panel border-border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
            Content Breakdown
          </p>
          <h4 className="text-sm font-semibold text-white">Originality Gauge</h4>
        </div>
        <span className="text-xs font-mono text-muted">Dual-Ratio Metric</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Circular Donut Visualization */}
        <div className="relative h-44 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart aria-label={`Originality: ${originalityPct.toFixed(1)}%, Similar: ${overlapPct.toFixed(1)}%`}>
              <Pie
                data={data}
                innerRadius={52}
                outerRadius={72}
                paddingAngle={4}
                dataKey="value"
                startAngle={90}
                endAngle={-270}
                stroke="#101A26"
                strokeWidth={3}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          {/* Centered Percentage readout */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="font-mono text-2xl font-bold text-white">
              {originalityPct.toFixed(1)}%
            </span>
            <span className="text-[10px] uppercase font-semibold text-accent tracking-wider">
              Original
            </span>
          </div>
        </div>

        {/* Linear breakdown details */}
        <div className="space-y-4">
          {/* Original Bar */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="flex items-center gap-1.5 text-white font-medium">
                <span className="h-2.5 w-2.5 rounded-full bg-accent inline-block" />
                Original Content
              </span>
              <span className="font-mono text-accent font-semibold">
                {originalityPct.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 w-full bg-panel-light rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${originalityPct}%` }}
              />
            </div>
          </div>

          {/* Similar Bar */}
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="flex items-center gap-1.5 text-muted font-medium">
                <span className="h-2.5 w-2.5 rounded-full bg-coral inline-block" />
                Potentially Similar Content
              </span>
              <span className="font-mono text-coral font-semibold">
                {overlapPct.toFixed(1)}%
              </span>
            </div>
            <div className="h-2 w-full bg-panel-light rounded-full overflow-hidden">
              <div
                className="h-full bg-coral rounded-full transition-all duration-500"
                style={{ width: `${overlapPct}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-muted leading-relaxed">
            Text overlap is calculated using TF-IDF cosine similarity and MinHash signature Jaccard index against indexed repository papers.
          </p>
        </div>
      </div>
    </Card>
  )
}
