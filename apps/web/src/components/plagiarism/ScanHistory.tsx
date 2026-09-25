import { useState } from "react"
import {
  Search,
  Trash2,
  Eye,
  Download,
  FileText,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import StatusBadge from "@/components/dashboard/StatusBadge"
import EmptyState from "@/components/dashboard/EmptyState"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  usePlagiarismChecks,
  useDeleteCheckMutation,
} from "@/hooks/use-plagiarism"
import type { PlagiarismCheck } from "@/types"

interface ScanHistoryProps {
  onSelectCheck: (checkId: string) => void
  currentCheckId?: string | null
  onStartNewCheck?: () => void
}

export default function ScanHistory({
  onSelectCheck,
  currentCheckId,
  onStartNewCheck,
}: ScanHistoryProps) {
  const [page, setPage] = useState(1)
  const pageSize = 10
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null)

  const { data, isLoading } = usePlagiarismChecks(
    page,
    pageSize,
    statusFilter === "all" ? null : statusFilter
  )
  const deleteMutation = useDeleteCheckMutation()

  const checks = data?.checks ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  // Filter client-side by search query
  const filteredChecks = checks.filter((c) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      (c.source_filename && c.source_filename.toLowerCase().includes(q)) ||
      c.id.toLowerCase().includes(q) ||
      c.status.toLowerCase().includes(q)
    )
  })

  const handleDeleteConfirm = () => {
    if (deleteTargetId) {
      deleteMutation.mutate(deleteTargetId, {
        onSuccess: () => {
          setDeleteTargetId(null)
        },
      })
    }
  }

  const handleDownloadCheck = (check: PlagiarismCheck) => {
    const jsonStr = JSON.stringify(check, null, 2)
    const blob = new Blob([jsonStr], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `plagiarism-scan-${check.id.slice(0, 8)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoStr
    }
  }

  return (
    <Card className="bg-panel border-border shadow-sm">
      <CardContent className="p-6 space-y-4">
        {/* Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
              Scan History
            </p>
            <h3 className="text-base font-semibold text-white">
              Previous Plagiarism Reports
            </h3>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Search Input */}
            <div className="relative min-w-[200px]">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
              />
              <Input
                type="text"
                placeholder="Search scans..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-8 text-xs bg-panel-light border-border text-white placeholder:text-muted focus-visible:ring-accent"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1.5">
              <Filter size={14} className="text-muted" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  setPage(1)
                }}
                className="h-8 rounded-md bg-panel-light border border-border px-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
                aria-label="Filter scans by status"
              >
                <option value="all">All Statuses</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="processing">Processing</option>
              </select>
            </div>
          </div>
        </div>

        {/* Content Table / Cards */}
        {isLoading ? (
          <div className="py-12 text-center text-xs text-muted font-mono animate-pulse">
            Loading scan history...
          </div>
        ) : filteredChecks.length === 0 ? (
          <div className="py-8">
            <EmptyState
              icon={FileText}
              title="No plagiarism scans found"
              description="You have not run any plagiarism checks yet, or no scans match your filters."
            />
            {onStartNewCheck && (
              <div className="flex justify-center -mt-6">
                <Button
                  onClick={onStartNewCheck}
                  size="sm"
                  className="bg-accent text-black font-semibold hover:bg-accent/90 text-xs"
                >
                  Start Your First Check
                </Button>
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="overflow-x-auto rounded-lg border border-border hidden md:block">
              <table className="w-full text-left text-xs">
                <thead className="bg-panel-light/60 border-b border-border text-[10px] uppercase font-semibold text-muted tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Document / Source</th>
                    <th className="py-3 px-4">Date Checked</th>
                    <th className="py-3 px-4">Originality</th>
                    <th className="py-3 px-4">Similarity</th>
                    <th className="py-3 px-4">Matches</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredChecks.map((c) => {
                    const isSelected = currentCheckId === c.id
                    return (
                      <tr
                        key={c.id}
                        className={`transition-colors hover:bg-panel-light/40 ${
                          isSelected ? "bg-accent/5 border-l-2 border-l-accent" : ""
                        }`}
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2 max-w-xs">
                            <FileText size={15} className="text-muted shrink-0" />
                            <span className="font-medium text-white truncate">
                              {c.source_filename || `Text snippet (${c.id.slice(0, 8)})`}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-muted font-mono whitespace-nowrap">
                          {formatDate(c.created_at)}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-accent">
                          {c.originality_score.toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono font-medium text-coral">
                          {(c.overall_similarity * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono text-muted">
                          {c.total_matches}
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={c.status} />
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => onSelectCheck(c.id)}
                              className="h-7 w-7 text-muted hover:text-accent hover:bg-panel-light"
                              title="View full report"
                              aria-label={`View report for ${c.id}`}
                            >
                              <Eye size={14} />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDownloadCheck(c)}
                              className="h-7 w-7 text-muted hover:text-white hover:bg-panel-light"
                              title="Download JSON report"
                              aria-label={`Download report for ${c.id}`}
                            >
                              <Download size={14} />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => setDeleteTargetId(c.id)}
                              className="h-7 w-7 text-muted hover:text-red-400 hover:bg-panel-light"
                              title="Delete scan"
                              aria-label={`Delete scan ${c.id}`}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Stacked Cards View */}
            <div className="grid grid-cols-1 gap-3 md:hidden">
              {filteredChecks.map((c) => (
                <div
                  key={c.id}
                  className="p-4 rounded-xl border border-border bg-panel-light/30 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="overflow-hidden">
                      <p className="text-sm font-semibold text-white truncate">
                        {c.source_filename || `Text snippet (${c.id.slice(0, 8)})`}
                      </p>
                      <p className="text-xs text-muted font-mono">{formatDate(c.created_at)}</p>
                    </div>
                    <StatusBadge status={c.status} />
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs py-2 border-y border-border/40">
                    <div>
                      <span className="text-[10px] text-muted block uppercase">Original</span>
                      <span className="font-mono font-bold text-accent">
                        {c.originality_score.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block uppercase">Similar</span>
                      <span className="font-mono font-bold text-coral">
                        {(c.overall_similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted block uppercase">Matches</span>
                      <span className="font-mono text-muted">{c.total_matches}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onSelectCheck(c.id)}
                      className="text-xs border-border bg-panel text-accent hover:bg-panel-light"
                    >
                      <Eye size={13} className="mr-1" />
                      View Report
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDownloadCheck(c)}
                      className="h-8 w-8 text-muted hover:text-white"
                      aria-label="Download scan JSON"
                    >
                      <Download size={14} />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteTargetId(c.id)}
                      className="h-8 w-8 text-muted hover:text-red-400"
                      aria-label="Delete scan"
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2 text-xs text-muted">
                <span>
                  Showing {filteredChecks.length} of {total} scans
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="h-8 px-2 text-xs border-border bg-panel text-white hover:bg-panel-light"
                    aria-label="Previous page"
                  >
                    <ChevronLeft size={14} />
                  </Button>
                  <span className="font-mono text-white">
                    {page} / {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="h-8 px-2 text-xs border-border bg-panel text-white hover:bg-panel-light"
                    aria-label="Next page"
                  >
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Delete Confirmation Dialog */}
        <Dialog open={Boolean(deleteTargetId)} onOpenChange={(open) => !open && setDeleteTargetId(null)}>
          <DialogContent className="bg-panel border-border text-white sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <AlertTriangle size={18} className="text-red-400" />
                <span>Delete Plagiarism Scan?</span>
              </DialogTitle>
              <DialogDescription className="text-muted text-xs">
                This will permanently delete this scan result and its recorded passage matches from the database. This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="gap-2 sm:gap-0 mt-4">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDeleteTargetId(null)}
                className="text-xs text-muted hover:text-white"
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={handleDeleteConfirm}
                disabled={deleteMutation.isPending}
                className="text-xs bg-red-600 hover:bg-red-700 text-white"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete Permanently"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
