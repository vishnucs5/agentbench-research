import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { searchApi } from "@/lib/api"
import { useProject } from "@/contexts/ProjectContext"
import type { SearchResponse } from "@/types"
import {
  Search,
  FileText,
  Copy,
  Check,
  Loader2,
  Layers,
} from "lucide-react"

interface SearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialQuery?: string
}

export function SearchDialog({
  open,
  onOpenChange,
  initialQuery = "",
}: SearchDialogProps) {
  const { selectedProject } = useProject()
  const { toast } = useToast()

  const [query, setQuery] = useState(initialQuery)
  const [searchType, setSearchType] = useState<"hybrid" | "semantic" | "bm25">("hybrid")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
    }
  }, [initialQuery])

  useEffect(() => {
    if (open && query.trim() && !result) {
      handleSearch()
    }
  }, [open])

  async function handleSearch() {
    if (!query.trim()) return

    setLoading(true)
    try {
      const res = await searchApi.search({
        query: query.trim(),
        search_type: searchType,
        top_k: 10,
        project_id: selectedProject?.id ?? null,
      })
      setResult(res)
    } catch (err) {
      toast({
        title: "Search failed",
        description: err instanceof Error ? err.message : "Failed to execute search",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  function handleCopy(evidenceId: string) {
    navigator.clipboard.writeText(evidenceId)
    setCopiedId(evidenceId)
    toast({ title: "Copied to clipboard", description: evidenceId })
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[720px] max-h-[85vh] flex flex-col bg-[#101A26] border-[#1E293B] text-white p-0 overflow-hidden">
        <DialogHeader className="sr-only">
          <DialogTitle>Search Evidence Chunks</DialogTitle>
        </DialogHeader>

        {/* Search Input Bar */}
        <div className="p-4 border-b border-[#1E293B] bg-[#0A1017] space-y-3">
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-[#CFFF4B] shrink-0" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch()
              }}
              placeholder="Search evidence chunks... (e.g. transformer anomaly detection)"
              className="border-none bg-transparent text-white placeholder:text-[#64748B] focus-visible:ring-0 text-base"
              autoFocus
            />
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin text-[#CFFF4B] shrink-0" />
            ) : (
              <Button
                size="sm"
                onClick={handleSearch}
                className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold h-8 text-xs shrink-0"
              >
                Search
              </Button>
            )}
          </div>

          {/* Search Type Filters */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5">
              <span className="text-[#64748B] text-[11px] uppercase tracking-wider font-semibold">Mode:</span>
              {(["hybrid", "semantic", "bm25"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSearchType(type)}
                  className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize transition ${
                    searchType === type
                      ? "bg-[#CFFF4B] text-black"
                      : "bg-[#1E293B] text-[#94A3B8] hover:text-white"
                  }`}
                >
                  {type === "hybrid" ? "Hybrid (BM25 + Semantic)" : type}
                </button>
              ))}
            </div>

            {result && (
              <span className="text-[#64748B] text-[11px]">
                {result.total} hits · {result.took_ms} ms
              </span>
            )}
          </div>
        </div>

        {/* Results Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 text-[#64748B] space-y-2">
              <Loader2 className="h-8 w-8 animate-spin text-[#CFFF4B]" />
              <p className="text-sm">Retrieving grounded evidence chunks...</p>
            </div>
          )}

          {!loading && result && result.hits.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center text-[#64748B]">
              <Layers className="h-10 w-10 mb-2 opacity-40" />
              <p className="text-white font-medium text-sm">No evidence found</p>
              <p className="text-xs text-[#64748B] mt-1 max-w-sm">
                Try broadening your query keywords or upload a new research PDF to ingest chunks.
              </p>
            </div>
          )}

          {!loading && !result && (
            <div className="flex flex-col items-center justify-center py-12 text-center text-[#64748B]">
              <Search className="h-10 w-10 mb-2 opacity-30 text-[#CFFF4B]" />
              <p className="text-white font-medium text-sm">Hybrid Retrieval Engine</p>
              <p className="text-xs text-[#64748B] mt-1 max-w-sm">
                Queries are matched using dual BM25 lexical token matching and dense 384d semantic embeddings.
              </p>
            </div>
          )}

          {!loading && result && result.hits.map((hit) => (
            <div
              key={hit.evidence_id}
              className="p-4 rounded-xl bg-[#0A1017] border border-[#1E293B] space-y-2 hover:border-[#64748B]/50 transition"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5 text-[#CFFF4B]" />
                      {hit.paper_title || "Research Document"}
                    </span>
                    <Badge
                      variant="outline"
                      className="text-[10px] border-[#1E293B] text-[#94A3B8] bg-[#101A26]"
                    >
                      Page {hit.page_number} {hit.section_label ? `· ${hit.section_label}` : ""}
                    </Badge>
                  </div>
                  <p className="text-[10px] font-mono text-[#64748B]">
                    ID: {hit.evidence_id}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge
                    variant="outline"
                    className="text-[10px] font-mono border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  >
                    score {hit.score.toFixed(3)}
                  </Badge>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(hit.evidence_id)}
                    className="h-7 w-7 p-0 text-[#64748B] hover:text-white"
                  >
                    {copiedId === hit.evidence_id ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              </div>

              <p className="text-xs text-[#CBD5E1] leading-relaxed font-mono bg-[#101A26] p-2.5 rounded-lg border border-[#1E293B]/60">
                {hit.text}
              </p>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
