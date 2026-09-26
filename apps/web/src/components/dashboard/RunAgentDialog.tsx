import { useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { runsApi } from "@/lib/api"
import { useProject } from "@/contexts/ProjectContext"
import { queryClient } from "@/lib/query-client"
import {
  Bot,
  Play,
  CheckCircle2,
  GitBranch,
  Loader2,
  Sparkles,
} from "lucide-react"

interface RunAgentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

const DEFAULT_PROMPTS = [
  "Compare deep learning approaches for network intrusion detection (2023-2025)",
  "Synthesize CNN vs Transformer anomaly detection architectures and trade-offs",
  "Extract and verify benchmark accuracy claims on CIC-IDS2017 and NSL-KDD",
]

export function RunAgentDialog({
  open,
  onOpenChange,
  onSuccess,
}: RunAgentDialogProps) {
  const { selectedProject } = useProject()
  const { toast } = useToast()
  const navigate = useNavigate()

  const [prompt, setPrompt] = useState<string>(DEFAULT_PROMPTS[0] ?? "")
  const [modelProfile, setModelProfile] = useState("mock")
  const [running, setRunning] = useState(false)
  const [completedRunId, setCompletedRunId] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState("")

  async function handleExecute() {
    if (!selectedProject) {
      toast({
        title: "No project selected",
        description: "Please select a project before running the research agent.",
        variant: "destructive",
      })
      return
    }
    if (!prompt.trim()) {
      toast({
        title: "Prompt required",
        description: "Please enter a research prompt or topic.",
        variant: "destructive",
      })
      return
    }

    setRunning(true)
    setCompletedRunId(null)
    setCurrentStep("Planning agent trajectory & budgets...")

    try {
      // Simulate step transitions for smooth visual feedback
      const stepTimer1 = setTimeout(() => setCurrentStep("Retrieving hybrid evidence chunks..."), 400)
      const stepTimer2 = setTimeout(() => setCurrentStep("Extracting structured claims & metrics..."), 800)
      const stepTimer3 = setTimeout(() => setCurrentStep("Synthesizing comparative matrix & gaps..."), 1200)

      const res = await runsApi.execute(selectedProject.id, {
        prompt: prompt.trim(),
        model_profile: modelProfile,
      })

      clearTimeout(stepTimer1)
      clearTimeout(stepTimer2)
      clearTimeout(stepTimer3)

      setCompletedRunId(res.run_id)
      setCurrentStep("Completed")

      toast({
        title: "Research run completed",
        description: `Generated execution trace with ${res.total_tool_calls} tool calls.`,
      })

      // Invalidate queries so dashboard metrics update
      queryClient.invalidateQueries({ queryKey: ["stats", selectedProject.id] })
      queryClient.invalidateQueries({ queryKey: ["runs", selectedProject.id] })
      queryClient.invalidateQueries({ queryKey: ["projects"] })

      onSuccess?.()
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Run execution failed"
      toast({
        title: "Execution failed",
        description: msg,
        variant: "destructive",
      })
      setCurrentStep("")
    } finally {
      setRunning(false)
    }
  }

  function handleGoToTrace() {
    onOpenChange(false)
    navigate("/trace")
  }

  return (
    <Dialog open={open} onOpenChange={(val) => !running && onOpenChange(val)}>
      <DialogContent className="sm:max-w-[560px] bg-[#101A26] border-[#1E293B] text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <Bot className="h-5 w-5 text-[#CFFF4B]" />
            Run Autonomous Research Agent
          </DialogTitle>
          <DialogDescription className="text-[#64748B]">
            Execute the full evidence-grounded research pipeline on{" "}
            <span className="font-semibold text-white">
              {selectedProject?.name ?? "selected project"}
            </span>
            .
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Research Prompt */}
          <div className="space-y-2">
            <Label htmlFor="agent-prompt" className="text-xs text-[#94A3B8]">
              Research Query / Synthesis Goal
            </Label>
            <Textarea
              id="agent-prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={running}
              placeholder="e.g. Compare deep learning approaches for network intrusion detection..."
              className="bg-[#0A1017] border-[#1E293B] text-white text-sm focus:border-[#CFFF4B] focus:ring-1 focus:ring-[#CFFF4B]"
            />
            {/* Quick Suggestion Pills */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              <span className="text-[11px] text-[#64748B] flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-[#CFFF4B]" /> Quick prompts:
              </span>
              {DEFAULT_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(p)}
                  className="text-[10px] px-2 py-0.5 rounded-full bg-[#1E293B] text-[#94A3B8] hover:text-white hover:bg-[#1E293B]/80 transition truncate max-w-[200px]"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Model Profile Selection */}
          <div className="space-y-2">
            <Label className="text-xs text-[#94A3B8]">Model Profile</Label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "mock", label: "Mock Provider", desc: "Fast, deterministic" },
                { id: "balanced", label: "Balanced", desc: "Cloud OpenRouter" },
                { id: "ollama", label: "Local Ollama", desc: "qwen3-coder:30b" },
              ].map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setModelProfile(m.id)}
                  disabled={running}
                  className={`p-2.5 rounded-xl border text-left transition ${
                    modelProfile === m.id
                      ? "border-[#CFFF4B] bg-[#CFFF4B]/10 text-white"
                      : "border-[#1E293B] bg-[#0A1017] text-[#64748B] hover:text-white"
                  }`}
                >
                  <p className="text-xs font-semibold">{m.label}</p>
                  <p className="text-[10px] text-[#64748B]">{m.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Pipeline Stages Stepper */}
          <div className="p-3 rounded-xl bg-[#0A1017] border border-[#1E293B] space-y-2">
            <p className="text-[10px] uppercase font-semibold tracking-wider text-[#64748B]">
              Pipeline Execution Plan
            </p>
            <div className="flex items-center justify-between text-xs text-[#94A3B8]">
              {["1. Plan", "2. Retrieve", "3. Extract", "4. Synthesize", "5. Verify"].map((step, i) => (
                <div key={i} className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#CFFF4B]" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Running Status or Completion */}
          {running && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-[#CFFF4B]/10 border border-[#CFFF4B]/20 text-xs text-[#CFFF4B]">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>{currentStep}</span>
            </div>
          )}

          {completedRunId && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                <span>Run executed successfully! Trace ID: {completedRunId.slice(0, 8)}...</span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleGoToTrace}
                className="h-7 text-xs border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
              >
                <GitBranch className="h-3 w-3 mr-1" />
                View Trace
              </Button>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={running}
            className="text-[#64748B] hover:text-white"
          >
            Close
          </Button>
          <Button
            type="button"
            onClick={handleExecute}
            disabled={running || !prompt.trim()}
            className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold"
          >
            {running ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Executing Pipeline...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Play className="h-4 w-4 fill-black" />
                Execute Research Agent
              </span>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
