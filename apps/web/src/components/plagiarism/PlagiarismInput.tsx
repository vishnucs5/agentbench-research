import React, { useState } from "react"
import { Search, RotateCcw, Sparkles, Loader2, ShieldCheck, HelpCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import FileUploadZone from "./FileUploadZone"

interface PlagiarismInputProps {
  onSubmitText: (text: string, threshold: number, consent: boolean) => void
  onSubmitFile: (file: File, threshold: number, consent: boolean) => void
  isLoading: boolean
}

const SAMPLE_TEXT = `Recent deep learning approaches for network intrusion detection have demonstrated promising results on benchmark datasets such as CIC-IDS2017. However, cross-dataset generalization remains a significant challenge. Models frequently experience severe accuracy degradation when evaluated on previously unseen network topologies and packet distribution shifts. To address this limitation, hybrid convolutional and recurrent architectures have been proposed to capture both spatial flow characteristics and temporal dependencies.`

export default function PlagiarismInput({
  onSubmitText,
  onSubmitFile,
  isLoading,
}: PlagiarismInputProps) {
  const [activeTab, setActiveTab] = useState<"text" | "file">("text")
  const [text, setText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [threshold, setThreshold] = useState<number>(0.2)
  const [consentToStore, setConsentToStore] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const charCount = text.length
  const wordCount = text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0

  const handleClear = () => {
    setText("")
    setFile(null)
    setError(null)
  }

  const handleUseSample = () => {
    setText(SAMPLE_TEXT)
    setError(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (activeTab === "text") {
      if (!text.trim()) {
        setError("Please enter or paste content to check.")
        return
      }
      if (text.trim().length < 15) {
        setError("Text is too short. Please provide at least 15 characters for a meaningful scan.")
        return
      }
      onSubmitText(text.trim(), threshold, consentToStore)
    } else {
      if (!file) {
        setError("Please select or drop a document to scan.")
        return
      }
      onSubmitFile(file, threshold, consentToStore)
    }
  }

  const isSubmitDisabled =
    isLoading || (activeTab === "text" ? !text.trim() : !file)

  return (
    <Card className="bg-panel border-border shadow-sm">
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <Tabs
            value={activeTab}
            onValueChange={(val) => {
              setActiveTab(val as "text" | "file")
              setError(null)
            }}
          >
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <TabsList className="bg-panel-light border border-border p-1">
                <TabsTrigger
                  value="text"
                  className="data-[state=active]:bg-panel data-[state=active]:text-accent text-xs"
                >
                  Paste Text
                </TabsTrigger>
                <TabsTrigger
                  value="file"
                  className="data-[state=active]:bg-panel data-[state=active]:text-accent text-xs"
                >
                  Upload Document
                </TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-2">
                {activeTab === "text" && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleUseSample}
                    disabled={isLoading}
                    className="text-xs text-muted hover:text-accent hover:bg-panel-light gap-1.5"
                  >
                    <Sparkles size={14} />
                    <span>Use Sample Text</span>
                  </Button>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  disabled={isLoading || (!text && !file)}
                  className="text-xs text-muted hover:text-white hover:bg-panel-light gap-1.5"
                >
                  <RotateCcw size={14} />
                  <span>Clear</span>
                </Button>
              </div>
            </div>

            <TabsContent value="text" className="mt-0 space-y-2">
              <div className="relative">
                <Textarea
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value)
                    if (error) setError(null)
                  }}
                  placeholder="Paste your research draft, abstract, or literature text here to check for potentially similar passages against indexed papers..."
                  className="min-h-[180px] bg-panel-light/40 border-border text-white placeholder:text-muted/60 font-sans text-sm resize-y focus-visible:ring-accent"
                  disabled={isLoading}
                  aria-label="Text content for plagiarism check"
                />
              </div>
              <div className="flex items-center justify-between text-xs text-muted px-1">
                <span>
                  {wordCount.toLocaleString()} {wordCount === 1 ? "word" : "words"} ·{" "}
                  {charCount.toLocaleString()} characters
                </span>
                <span>Max 1,000,000 chars</span>
              </div>
            </TabsContent>

            <TabsContent value="file" className="mt-0">
              <FileUploadZone
                file={file}
                onFileSelect={(f) => {
                  setFile(f)
                  if (error) setError(null)
                }}
                disabled={isLoading}
              />
            </TabsContent>
          </Tabs>

          {/* Settings & Privacy Controls */}
          <div className="pt-2 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-6 flex-wrap">
              {/* Threshold sensitivity */}
              <div className="flex items-center gap-2">
                <label htmlFor="plagiarism-threshold" className="text-muted font-medium">
                  Sensitivity:
                </label>
                <select
                  id="plagiarism-threshold"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  disabled={isLoading}
                  className="bg-panel-light border border-border rounded-md px-2 py-1 text-white text-xs focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
                >
                  <option value={0.15}>High (15% overlap)</option>
                  <option value={0.2}>Standard (20% overlap)</option>
                  <option value={0.3}>Moderate (30% overlap)</option>
                  <option value={0.5}>Strict (50% overlap)</option>
                </select>
              </div>

              {/* Consent toggle */}
              <label className="flex items-center gap-2 cursor-pointer select-none text-muted hover:text-white transition-colors">
                <input
                  type="checkbox"
                  checked={consentToStore}
                  onChange={(e) => setConsentToStore(e.target.checked)}
                  disabled={isLoading}
                  className="rounded border-border bg-panel-light text-accent focus:ring-accent accent-[#CFFF4B]"
                />
                <span className="flex items-center gap-1">
                  <span>Store submission for future index</span>
                  <span title="If checked, your submission is retained to check future papers against it. If unchecked, it is discarded after analysis.">
                    <HelpCircle size={12} className="text-muted hover:text-white" />
                  </span>
                </span>
              </label>
            </div>

            {/* Privacy indicator */}
            <div className="flex items-center gap-1.5 text-muted">
              <ShieldCheck size={14} className="text-accent" />
              <span>API keys & secrets never leave server</span>
            </div>
          </div>

          {error && (
            <div className="p-3 text-xs rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              {error}
            </div>
          )}

          {/* Submission CTA */}
          <div className="flex justify-end pt-1">
            <Button
              type="submit"
              disabled={isSubmitDisabled}
              className="bg-accent text-black font-semibold hover:bg-accent/90 px-6 gap-2 w-full sm:w-auto"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Scanning Content...</span>
                </>
              ) : (
                <>
                  <Search size={16} />
                  <span>Check for Similarity</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
