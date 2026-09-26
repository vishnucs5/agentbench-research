import { cn } from "@/lib/utils"

interface Phase {
  phase: number
  name: string
  status: "done" | "active" | "pending"
}

interface PipelineStepperProps {
  phases: Phase[]
  selectedPhase?: number
  onSelectPhase?: (phase: number) => void
}

export default function PipelineStepper({
  phases,
  selectedPhase,
  onSelectPhase,
}: PipelineStepperProps) {
  return (
    <div className="flex items-start gap-0">
      {phases.map((phase, i) => {
        const isDone = phase.status === "done"
        const isActive = phase.status === "active"
        const isPending = phase.status === "pending"
        const isSelected = selectedPhase === phase.phase

        return (
          <div key={phase.phase} className="flex items-center">
            <button
              type="button"
              onClick={() => onSelectPhase?.(phase.phase)}
              className={cn(
                "flex flex-col items-center group transition cursor-pointer p-1 rounded-lg",
                isSelected && "bg-[#1E293B]/60 ring-1 ring-[#CFFF4B]/40"
              )}
            >
              {/* Dot */}
              <div
                className={cn(
                  "relative flex h-4 w-4 items-center justify-center rounded-full border-2 transition-colors",
                  isDone && "border-[#CFFF4B] bg-[#CFFF4B]",
                  isActive &&
                    "border-[#CFFF4B] bg-[#CFFF4B] shadow-[0_0_12px_rgba(207,255,75,0.5)]",
                  isPending && "border-[#64748B] bg-transparent group-hover:border-slate-400",
                  isSelected && "ring-2 ring-white ring-offset-2 ring-offset-[#101A26]"
                )}
              >
                {isActive && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#CFFF4B] opacity-40" />
                )}
              </div>
              {/* Label */}
              <span
                className={cn(
                  "mt-2 whitespace-nowrap text-[10px] font-medium uppercase tracking-wider group-hover:text-white transition",
                  isDone && "text-[#CFFF4B]",
                  isActive && "text-[#CFFF4B]",
                  isPending && "text-[#64748B]",
                  isSelected && "text-white font-bold"
                )}
              >
                {phase.name}
              </span>
            </button>
            {/* Connector line */}
            {i < phases.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-0.5 w-12 self-center rounded-full",
                  isDone ? "bg-[#CFFF4B]" : "bg-[#1E293B]"
                )}
                style={{ marginTop: -20 }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
