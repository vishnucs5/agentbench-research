import React, { useRef, useState } from "react"
import { UploadCloud, FileText, X, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface FileUploadZoneProps {
  file: File | null
  onFileSelect: (file: File | null) => void
  disabled?: boolean
  maxSizeMb?: number
  allowedExtensions?: string[]
}

const DEFAULT_EXTENSIONS = [".txt", ".pdf", ".docx"]
const DEFAULT_MAX_SIZE_MB = 10

export default function FileUploadZone({
  file,
  onFileSelect,
  disabled = false,
  maxSizeMb = DEFAULT_MAX_SIZE_MB,
  allowedExtensions = DEFAULT_EXTENSIONS,
}: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const validateFile = (selectedFile: File): boolean => {
    setValidationError(null)
    const ext = "." + selectedFile.name.split(".").pop()?.toLowerCase()
    if (!allowedExtensions.includes(ext)) {
      setValidationError(
        `Unsupported file type "${ext}". Supported formats: ${allowedExtensions.join(", ")}`
      )
      return false
    }

    const maxBytes = maxSizeMb * 1024 * 1024
    if (selectedFile.size > maxBytes) {
      setValidationError(
        `File is too large (${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB). Maximum allowed size is ${maxSizeMb} MB.`
      )
      return false
    }

    if (selectedFile.size === 0) {
      setValidationError("Selected file is empty.")
      return false
    }

    return true
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (disabled) return
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
    if (disabled) return

    const droppedFiles = e.dataTransfer.files
    if (droppedFiles && droppedFiles.length > 0) {
      const selected = droppedFiles[0]
      if (selected && validateFile(selected)) {
        onFileSelect(selected)
      }
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0]
      if (selected && validateFile(selected)) {
        onFileSelect(selected)
      }
    }
  }

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation()
    onFileSelect(null)
    setValidationError(null)
    if (inputRef.current) {
      inputRef.current.value = ""
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        id="plagiarism-file-upload"
        className="sr-only"
        accept={allowedExtensions.join(",")}
        onChange={handleInputChange}
        disabled={disabled}
        aria-label="Upload document file"
      />

      {!file ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && inputRef.current?.click()}
          role="button"
          tabIndex={disabled ? -1 : 0}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && !disabled) {
              e.preventDefault()
              inputRef.current?.click()
            }
          }}
          className={cn(
            "flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl transition-all cursor-pointer text-center group",
            isDragOver
              ? "border-accent bg-accent/5 ring-2 ring-accent/20"
              : "border-border bg-panel-light/30 hover:border-accent/50 hover:bg-panel-light/50",
            disabled && "opacity-50 cursor-not-allowed"
          )}
        >
          <div className="h-12 w-12 rounded-full bg-accent/10 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform text-accent">
            <UploadCloud size={24} />
          </div>
          <p className="text-sm font-medium text-white mb-1">
            Drag and drop your document here, or{" "}
            <span className="text-accent underline underline-offset-4">browse</span>
          </p>
          <p className="text-xs text-muted mb-2">
            Supports {allowedExtensions.join(", ")} up to {maxSizeMb} MB
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            className="mt-2 text-xs border-border bg-panel text-white hover:bg-panel-light"
            onClick={(e) => {
              e.stopPropagation()
              inputRef.current?.click()
            }}
          >
            Browse Files
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 rounded-xl border border-border bg-panel-light/60">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="h-10 w-10 shrink-0 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
              <FileText size={20} />
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-medium text-white truncate">{file.name}</p>
              <p className="text-xs text-muted">{formatFileSize(file.size)}</p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={handleRemove}
            disabled={disabled}
            className="text-muted hover:text-white hover:bg-panel"
            aria-label="Remove uploaded file"
          >
            <X size={18} />
          </Button>
        </div>
      )}

      {validationError && (
        <div className="flex items-center gap-2 p-3 text-xs rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle size={14} className="shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  )
}
