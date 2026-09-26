import { useState, useRef } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { papersApi } from "@/lib/api"
import { useProject } from "@/contexts/ProjectContext"
import { queryClient } from "@/lib/query-client"
import { FileUp, UploadCloud, CheckCircle2, Loader2 } from "lucide-react"

interface UploadPaperDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function UploadPaperDialog({
  open,
  onOpenChange,
  onSuccess,
}: UploadPaperDialogProps) {
  const { selectedProject } = useProject()
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState("")
  const [authors, setAuthors] = useState("")
  const [uploading, setUploading] = useState(false)
  const [statusMessage, setStatusMessage] = useState("")
  const [isDragOver, setIsDragOver] = useState(false)

  function handleFileSelect(selectedFile: File) {
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      toast({
        title: "Invalid file type",
        description: "Only PDF files are supported for paper ingestion.",
        variant: "destructive",
      })
      return
    }
    if (selectedFile.size > 100 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Maximum file size is 100 MB.",
        variant: "destructive",
      })
      return
    }
    setFile(selectedFile)
    if (!title) {
      // Auto-populate title from filename minus .pdf extension
      setTitle(selectedFile.name.replace(/\.pdf$/i, "").replace(/[-_]/g, " "))
    }
  }

  async function handleUpload() {
    if (!selectedProject) {
      toast({
        title: "No project selected",
        description: "Please select a project before uploading papers.",
        variant: "destructive",
      })
      return
    }
    if (!file) {
      toast({
        title: "No file selected",
        description: "Please select a PDF paper to upload.",
        variant: "destructive",
      })
      return
    }

    setUploading(true)
    setStatusMessage("Uploading and extracting pages...")

    try {
      const formData = new FormData()
      formData.append("file", file)
      if (title.trim()) formData.append("title", title.trim())
      if (authors.trim()) {
        const authorList = authors.split(",").map((a) => a.trim()).filter(Boolean)
        formData.append("authors", JSON.stringify(authorList))
      }

      const res = await papersApi.upload(selectedProject.id, formData)

      setStatusMessage("Indexing evidence chunks...")
      toast({
        title: "Paper uploaded & indexed",
        description: res.status === "duplicate"
          ? "Duplicate paper detected — existing index preserved."
          : `Successfully ingested "${title || file.name}".`,
      })

      // Invalidate project stats and papers queries
      queryClient.invalidateQueries({ queryKey: ["stats", selectedProject.id] })
      queryClient.invalidateQueries({ queryKey: ["papers", selectedProject.id] })
      queryClient.invalidateQueries({ queryKey: ["projects"] })

      // Reset form
      setFile(null)
      setTitle("")
      setAuthors("")
      setStatusMessage("")
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed"
      toast({
        title: "Upload failed",
        description: msg,
        variant: "destructive",
      })
      setStatusMessage("")
    } finally {
      setUploading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(val) => !uploading && onOpenChange(val)}>
      <DialogContent className="sm:max-w-[520px] bg-[#101A26] border-[#1E293B] text-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-white">
            <FileUp className="h-5 w-5 text-[#CFFF4B]" />
            Upload Research Paper
          </DialogTitle>
          <DialogDescription className="text-[#64748B]">
            Upload a PDF into{" "}
            <span className="font-semibold text-white">
              {selectedProject?.name ?? "selected project"}
            </span>
            . Pages are parsed, chunked, and indexed for hybrid retrieval.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-3">
          {/* Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragOver(true)
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragOver(false)
              if (e.dataTransfer.files?.[0]) {
                handleFileSelect(e.dataTransfer.files[0])
              }
            }}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              isDragOver
                ? "border-[#CFFF4B] bg-[#CFFF4B]/5"
                : file
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "border-[#1E293B] hover:border-[#64748B] bg-[#0A1017]"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  handleFileSelect(e.target.files[0])
                }
              }}
            />

            {file ? (
              <div className="flex flex-col items-center gap-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-400" />
                <p className="font-medium text-white text-sm">{file.name}</p>
                <p className="text-xs text-[#64748B]">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB · PDF
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                  }}
                  className="text-xs text-red-400 hover:underline mt-1"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <UploadCloud className="h-8 w-8 text-[#64748B]" />
                <p className="font-medium text-white text-sm">
                  Drag & drop your PDF here, or{" "}
                  <span className="text-[#CFFF4B] underline">browse</span>
                </p>
                <p className="text-xs text-[#64748B]">
                  PDF only · Up to 100 MB · SHA-256 deduplicated
                </p>
              </div>
            )}
          </div>

          {/* Metadata Inputs */}
          <div className="space-y-2">
            <Label htmlFor="paper-title" className="text-xs text-[#94A3B8]">
              Title (optional, auto-extracted if empty)
            </Label>
            <Input
              id="paper-title"
              placeholder="e.g. Deep Learning for Network Intrusion Detection"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={uploading}
              className="bg-[#0A1017] border-[#1E293B] text-white text-sm placeholder:text-[#64748B]"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="paper-authors" className="text-xs text-[#94A3B8]">
              Authors (comma-separated, optional)
            </Label>
            <Input
              id="paper-authors"
              placeholder="e.g. A. Rahman, L. Chen"
              value={authors}
              onChange={(e) => setAuthors(e.target.value)}
              disabled={uploading}
              className="bg-[#0A1017] border-[#1E293B] text-white text-sm placeholder:text-[#64748B]"
            />
          </div>

          {/* Status Feedback */}
          {statusMessage && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#CFFF4B]/10 border border-[#CFFF4B]/20 text-xs text-[#CFFF4B]">
              <Loader2 className="h-4 w-4 animate-spin shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={uploading}
            className="text-[#64748B] hover:text-white"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleUpload}
            disabled={!file || uploading}
            className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold"
          >
            {uploading ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Ingesting...
              </span>
            ) : (
              "Ingest & Process PDF"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
