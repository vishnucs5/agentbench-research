import { useEffect, useState, useMemo } from "react"
import { traceApi } from "@/lib/api"
import { formatDuration } from "@/lib/utils"
import { useProject } from "@/contexts/ProjectContext"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import StatusBadge from "@/components/dashboard/StatusBadge"
import EmptyState from "@/components/dashboard/EmptyState"
import { useToast } from "@/hooks/use-toast"
import { RefreshCw, ClipboardList, Search } from "lucide-react"
import type { RunListItem, RunTrace } from "@/types"

const STATUS_FILTERS: { label: string; value: string }[] = [
  { label: "All Statuses", value: "all" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Running", value: "running" },
  { label: "Created", value: "created" },
  { label: "Needs Review", value: "needs_review" },
  { label: "Cancelled", value: "cancelled" },
]

function truncateId(id: string): string {
  return id.slice(0, 8)
}

export default function TraceReplay() {
  const { selectedProject } = useProject()
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [traceLoading, setTraceLoading] = useState(false)
  const [trace, setTrace] = useState<RunTrace | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const { toast } = useToast()

  useEffect(() => {
    if (selectedProject) {
      loadRuns()
    }
  }, [selectedProject])

  useEffect(() => {
    if (selectedRunId) {
      loadTrace(selectedRunId)
    } else {
      setTrace(null)
    }
  }, [selectedRunId])

  async function loadRuns() {
    if (!selectedProject) return
    try {
      setLoading(true)
      const res = await traceApi.listRuns(selectedProject.id)
      setRuns(res.runs ?? [])
    } catch (err) {
      toast({
        title: "Failed to load runs",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  async function loadTrace(runId: string) {
    try {
      setTraceLoading(true)
      const data = await traceApi.getRun(runId)
      setTrace(data)
    } catch (err) {
      toast({
        title: "Failed to load trace",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setTraceLoading(false)
    }
  }

  const filteredRuns = useMemo(() => {
    let result = runs

    if (statusFilter !== "all") {
      result = result.filter((r) => r.status === statusFilter)
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (r) =>
          r.request_text.toLowerCase().includes(q) ||
          r.model_profile.toLowerCase().includes(q)
      )
    }

    return result
  }, [runs, searchQuery, statusFilter])

  function handleRowClick(runId: string) {
    setSelectedRunId((prev) => (prev === runId ? null : runId))
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
          TRACE REPLAY
        </p>
        <h1 className="text-3xl font-bold text-white">Trace Replay</h1>
        <p className="text-[#64748B]">
          State transitions · Tool calls · Evidence IDs · Latency · Retries · Errors · Redacted
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          className="border-[#1E293B] bg-[#101A26] text-white hover:border-[#CFFF4B] hover:text-[#CFFF4B]"
          onClick={loadRuns}
          disabled={loading || !selectedProject}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Reload
        </Button>
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#64748B]" />
          <Input
            placeholder="Search request text..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-[#0D1420] border-[#1E293B] text-white placeholder:text-[#64748B] pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px] bg-[#0D1420] border-[#1E293B] text-white">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent className="bg-[#101A26] border-[#1E293B]">
            {STATUS_FILTERS.map((f) => (
              <SelectItem key={f.value} value={f.value} className="text-white focus:bg-[#1E293B] focus:text-white">
                {f.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Loading State */}
      {loading && (
        <Card className="bg-[#101A26] border-[#1E293B] p-6">
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-4 w-[80px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[60px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[60px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[40px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[40px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[100px] bg-[#1E293B]" />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!loading && runs.length === 0 && (
        <Card className="bg-[#101A26] border-[#1E293B] p-12">
          <EmptyState
            icon={ClipboardList}
            title="No runs yet"
            description="Upload a paper to start. Traces are redacted and retained per retention policy."
          />
        </Card>
      )}

      {/* Runs Table */}
      {!loading && runs.length > 0 && (
        <Card className="bg-[#101A26] border-[#1E293B]">
          <Table>
            <TableHeader>
              <TableRow className="border-[#1E293B] hover:bg-transparent">
                <TableHead className="text-[#64748B] font-semibold">Run</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Status</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Latency</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Tools</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Evidence</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Model</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRuns.length === 0 && (
                <TableRow className="border-[#1E293B]">
                  <TableCell colSpan={6} className="text-center text-[#64748B] py-8">
                    No matching runs found.
                  </TableCell>
                </TableRow>
              )}
              {filteredRuns.map((run) => (
                <TableRow
                  key={run.run_id}
                  className={`border-[#1E293B] cursor-pointer transition-colors ${
                    selectedRunId === run.run_id
                      ? "bg-[#CFFF4B]/5"
                      : "hover:bg-[#1E293B]/50"
                  }`}
                  onClick={() => handleRowClick(run.run_id)}
                >
                  <TableCell className="font-mono text-white text-xs">
                    {truncateId(run.run_id)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="font-mono text-[#94A3B8] text-xs">
                    {formatDuration(run.total_latency_ms)}
                  </TableCell>
                  <TableCell className="text-[#94A3B8]">{run.total_tool_calls}</TableCell>
                  <TableCell className="text-[#94A3B8]">{run.evidence_count}</TableCell>
                  <TableCell className="text-[#94A3B8]">{run.model_profile}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Run Detail Panel */}
      {selectedRunId && (
        <Card className="bg-[#101A26] border-[#1E293B] p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#64748B]">
                Run Detail · {truncateId(selectedRunId)}
              </p>
              {trace && (
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-[#94A3B8]">
                    Latency: <span className="font-mono text-white">{formatDuration(trace.total_latency_ms)}</span>
                  </span>
                  <span className="text-[#94A3B8]">
                    Tool calls: <span className="font-mono text-white">{trace.total_tool_calls}</span>
                  </span>
                  <span className="text-[#94A3B8]">
                    Evidence: <span className="font-mono text-white">{trace.evidence_ids.length}</span>
                  </span>
                  <span className="text-[#94A3B8]">
                    Model: <span className="font-mono text-white">{trace.model_profile}</span>
                  </span>
                </div>
              )}
            </div>
            <Badge
              variant="outline"
              className="text-[10px] font-mono border-[#1E293B] text-[#64748B] bg-[#0D1420]"
            >
              redact-v1
            </Badge>
          </div>

          {/* Trace Loading */}
          {traceLoading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-4">
                  <Skeleton className="h-4 w-[30px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[80px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[100px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[60px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[60px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[80px] bg-[#1E293B]" />
                  <Skeleton className="h-4 w-[150px] bg-[#1E293B]" />
                </div>
              ))}
            </div>
          )}

          {/* Timeline Table */}
          {trace && !traceLoading && (
            <div className="rounded-md border border-[#1E293B] overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-[#1E293B] hover:bg-transparent bg-[#0D1420]">
                    <TableHead className="text-[#64748B] font-semibold w-12">#</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Type</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Component</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Status</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Latency</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Evidence</TableHead>
                    <TableHead className="text-[#64748B] font-semibold">Input/Output</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {trace.trace_events.map((event, idx) => (
                    <TableRow
                      key={event.event_id}
                      className={`border-[#1E293B] ${
                        idx % 2 === 0 ? "bg-[#0D1420]/50" : "bg-[#101A26]"
                      }`}
                    >
                      <TableCell className="font-mono text-xs text-[#64748B]">
                        {event.sequence_no}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-white">
                        {event.event_type}
                      </TableCell>
                      <TableCell className="text-[#94A3B8] text-xs">
                        {event.component}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={event.status} />
                      </TableCell>
                      <TableCell className="font-mono text-xs text-[#94A3B8]">
                        {formatDuration(event.latency_ms ?? 0)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-[#94A3B8]">
                        {event.evidence_ids.length > 0
                          ? event.evidence_ids.join(", ")
                          : "—"}
                      </TableCell>
                      <TableCell className="text-[#64748B] text-xs max-w-[200px] truncate">
                        {Object.keys(event.input_summary).length > 0 || Object.keys(event.output_summary).length > 0
                          ? `${JSON.stringify(event.input_summary)} → ${JSON.stringify(event.output_summary)}`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
