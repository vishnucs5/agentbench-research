import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const statusStyles: Record<string, string> = {
  completed: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/20 text-red-400 border-red-500/30",
  created: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  planning: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  retrieving: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  extracting: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  synthesizing: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  verifying: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  paused: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  needs_review: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  cancelled: "bg-slate-500/20 text-slate-400 border-slate-500/30",
}

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase().replace(/-/g, "_")
  return (
    <Badge
      variant="outline"
      className={cn(
        "text-[10px] font-semibold uppercase tracking-wider border rounded-full px-2.5 py-0.5",
        statusStyles[normalized] ?? "bg-slate-500/20 text-slate-400 border-slate-500/30"
      )}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  )
}
