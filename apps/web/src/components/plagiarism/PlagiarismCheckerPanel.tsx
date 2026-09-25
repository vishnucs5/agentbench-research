import { useState, useRef } from "react"
import {
  Download,
  Printer,
  RotateCcw,
  History,
  FileCheck,
  AlertCircle,
  FileSearch,
} from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import PlagiarismInput from "./PlagiarismInput"
import ScanProgress from "./ScanProgress"
import ScoreSummary from "./ScoreSummary"
import SimilarityChart from "./SimilarityChart"
import MatchingPassage from "./MatchingPassage"
import ScanHistory from "./ScanHistory"
import {
  useCheckTextMutation,
  useCheckFileMutation,
  usePlagiarismReport,
} from "@/hooks/use-plagiarism"

interface PlagiarismCheckerPanelProps {
  embedded?: boolean
}

export default function PlagiarismCheckerPanel({
  embedded: _embedded = false,
}: PlagiarismCheckerPanelProps) {
  const [activeCheckId, setActiveCheckId] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const historyRef = useRef<HTMLDivElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLDivElement>(null)

  const checkTextMutation = useCheckTextMutation()
  const checkFileMutation = useCheckFileMutation()

  const {
    data: report,
    isLoading: isReportLoading,
    error: reportError,
  } = usePlagiarismReport(activeCheckId)

  const isScanning = checkTextMutation.isPending || checkFileMutation.isPending

  const handleTextSubmit = (text: string, threshold: number, consent: boolean) => {
    setErrorMessage(null)
    checkTextMutation.mutate(
      {
        text,
        threshold,
        consented_to_store: consent,
      },
      {
        onSuccess: (check) => {
          setActiveCheckId(check.id)
          setTimeout(() => {
            resultsRef.current?.scrollIntoView({ behavior: "smooth" })
          }, 100)
        },
        onError: (err) => {
          setErrorMessage(
            err.message || "Failed to scan text content. Please check input and retry."
          )
        },
      }
    )
  }

  const handleFileSubmit = (file: File, threshold: number, consent: boolean) => {
    setErrorMessage(null)
    const formData = new FormData()
    formData.append("file", file)
    formData.append("threshold", threshold.toString())
    formData.append("consented_to_store", consent.toString())

    checkFileMutation.mutate(formData, {
      onSuccess: (check) => {
        setActiveCheckId(check.id)
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth" })
        }, 100)
      },
      onError: (err) => {
        setErrorMessage(
          err.message || "Failed to analyze document. Please check file format and retry."
        )
      },
    })
  }

  const handleStartNewCheck = () => {
    setActiveCheckId(null)
    setErrorMessage(null)
    setTimeout(() => {
      inputRef.current?.scrollIntoView({ behavior: "smooth" })
    }, 50)
  }

  const handleScrollToHistory = () => {
    historyRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const handleDownloadFullReport = () => {
    if (!report) return
    const content = JSON.stringify(report, null, 2)
    const blob = new Blob([content], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `plagiarism-report-${report.check.id.slice(0, 8)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handlePrintReport = () => {
    window.print()
  }

  return (
    <div className="space-y-8">
      {/* Input Section */}
      <div ref={inputRef}>
        <PlagiarismInput
          onSubmitText={handleTextSubmit}
          onSubmitFile={handleFileSubmit}
          isLoading={isScanning}
        />
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <div className="flex-1 text-xs space-y-1">
            <p className="font-semibold text-white">Scan Request Failed</p>
            <p>{errorMessage}</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setErrorMessage(null)}
            className="text-xs border-red-500/30 text-red-400 hover:bg-red-500/10 h-7"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Scan Progress State */}
      {isScanning && (
        <div>
          <ScanProgress />
        </div>
      )}

      {/* Active Results View */}
      {activeCheckId && (
        <div ref={resultsRef} className="space-y-6 pt-2">
          {isReportLoading ? (
            <div className="p-12 text-center text-xs text-muted font-mono animate-pulse bg-panel rounded-xl border border-border">
              Retrieving compiled similarity report...
            </div>
          ) : reportError ? (
            <div className="p-6 rounded-xl bg-panel border border-border text-center space-y-3">
              <AlertCircle size={24} className="mx-auto text-red-400" />
              <p className="text-sm text-white">Failed to load detailed report</p>
              <p className="text-xs text-muted">{reportError.message}</p>
              <Button
                size="sm"
                variant="outline"
                onClick={handleStartNewCheck}
                className="text-xs border-border bg-panel text-white hover:bg-panel-light"
              >
                Back to Input
              </Button>
            </div>
          ) : report ? (
            <div className="space-y-6">
              {/* Report Header & Actions bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-panel border border-border">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                    <FileCheck size={18} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      Analysis Report:{" "}
                      <span className="font-mono text-accent">
                        {report.check.source_filename || `Scan #${report.check.id.slice(0, 8)}`}
                      </span>
                    </h3>
                    <p className="text-xs text-muted">
                      Provider: <span className="text-white/80">{report.check.provider_used}</span> · Completed{" "}
                      {report.check.completed_at
                        ? new Date(report.check.completed_at).toLocaleTimeString()
                        : "Just now"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadFullReport}
                    className="text-xs border-border bg-panel text-white hover:bg-panel-light gap-1.5 h-8"
                  >
                    <Download size={13} />
                    <span>Download Report</span>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handlePrintReport}
                    className="text-xs border-border bg-panel text-white hover:bg-panel-light gap-1.5 h-8"
                  >
                    <Printer size={13} />
                    <span>Print</span>
                  </Button>
                  <Button
                    type="button"
                    variant="default"
                    size="sm"
                    onClick={handleStartNewCheck}
                    className="text-xs bg-accent text-black font-semibold hover:bg-accent/90 gap-1.5 h-8"
                  >
                    <RotateCcw size={13} />
                    <span>New Check</span>
                  </Button>
                </div>
              </div>

              {/* Score Summary Metrics */}
              <ScoreSummary
                originalityScore={report.check.originality_score}
                overallSimilarity={report.check.overall_similarity}
                totalMatches={report.check.total_matches}
                status={report.check.status}
              />

              {/* Visualization & Summary Text */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <SimilarityChart
                    originalityScore={report.check.originality_score}
                    similarityScore={report.check.overall_similarity}
                  />
                </div>

                {/* Synthesis summary note */}
                <Card className="bg-panel border-border p-6 flex flex-col justify-between">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted mb-2">
                      Scan Summary
                    </p>
                    <h4 className="text-sm font-semibold text-white mb-3">
                      Automated Assessment
                    </h4>
                    <p className="text-xs text-white/90 leading-relaxed">
                      {report.summary}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted">
                    <span>Evidence-Grounded Review</span>
                    <button
                      type="button"
                      onClick={handleScrollToHistory}
                      className="text-accent hover:underline flex items-center gap-1"
                    >
                      <History size={11} />
                      <span>History</span>
                    </button>
                  </div>
                </Card>
              </div>

              {/* Matching Passages Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted">
                      Detailed Evidence
                    </p>
                    <h3 className="text-base font-semibold text-white">
                      Detected Overlapping Passages ({report.matches.length})
                    </h3>
                  </div>
                  <span className="text-xs text-muted font-mono">
                    Manual verification recommended
                  </span>
                </div>

                {report.matches.length === 0 ? (
                  <Card className="bg-panel border-border p-8 text-center">
                    <FileSearch size={32} className="mx-auto text-accent mb-2" />
                    <h4 className="text-sm font-semibold text-white">
                      No Potentially Similar Passages Found
                    </h4>
                    <p className="text-xs text-muted max-w-md mx-auto mt-1">
                      No overlapping text fragments matched the indexed corpus or external references above the {((report.check.overall_similarity || 0.2) * 100).toFixed(0)}% sensitivity threshold.
                    </p>
                  </Card>
                ) : (
                  <div className="space-y-3">
                    {report.matches.map((match, idx) => (
                      <MatchingPassage key={match.id || idx} match={match} index={idx} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Scan History Section (Included directly on the same page) */}
      <div ref={historyRef} className="pt-4">
        <ScanHistory
          onSelectCheck={(id) => {
            setActiveCheckId(id)
            setTimeout(() => {
              resultsRef.current?.scrollIntoView({ behavior: "smooth" })
            }, 100)
          }}
          currentCheckId={activeCheckId}
          onStartNewCheck={handleStartNewCheck}
        />
      </div>
    </div>
  )
}
