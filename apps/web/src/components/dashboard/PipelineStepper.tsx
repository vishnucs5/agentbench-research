import { cn } from "@/lib/utils"

interface Phase {
  phase: number
  name: string
  status: "done" | "active" | "pending"
}

interface PipelineStepperProps {
  phases: Phase[]
}

export default function PipelineStepper({ phases }: PipelineStepperProps) {
  return (
    <div className="flex items-start gap-0">
      {phases.map((phase, i) => {
        const isDone = phase.status === "done"
        const isActive = phase.status === "active"
        const isPending = phase.status === "pending"

        return (
          <div key={phase.phase} className="flex items-center">
            <div className="flex flex-col items-center">
              {/* Dot */}
              <div
                className={cn(
                  "relative flex h-4 w-4 items-center justify-center rounded-full border-2 transition-colors",
                  isDone && "border-[#CFFF4B] bg-[#CFFF4B]",
                  isActive &&
                    "border-[#CFFF4B] bg-[#CFFF4B] shadow-[0_0_12px_rgba(207,255,75,0.5)]",
                  isPending && "border-[#64748B] bg-transparent"
                )}
              >
                {isActive && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#CFFF4B] opacity-40" />
                )}
              </div>
              {/* Label */}
              <span
                className={cn(
                  "mt-2 whitespace-nowrap text-[10px] font-medium uppercase tracking-wider",
                  isDone && "text-[#CFFF4B]",
                  isActive && "text-[#CFFF4B]",
                  isPending && "text-[#64748B]"
                )}
              >
                {phase.name}
              </span>
            </div>
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
