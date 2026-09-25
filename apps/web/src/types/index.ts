export interface User {
  id: string
  email: string
  full_name: string
  role: "viewer" | "researcher" | "supervisor" | "admin"
}

export interface Project {
  id: string
  owner_id: string
  name: string
  domain: string
  retention_days: number
  created_at: string
  paper_count: number
  run_count: number
}

export interface Paper {
  id: string
  project_id: string
  title: string
  authors: string
  status: "uploaded" | "parsed" | "chunked" | "indexed" | "error"
  page_count: number
  parser: string
  sha256: string
  created_at: string
}

export interface ProjectStats {
  project_id: string
  project_name: string
  total_papers: number
  total_runs: number
  completed_runs: number
  failed_runs: number
  total_evidence: number
  avg_latency_ms: number
  recent_runs: RunListItem[]
}

export interface RunListItem {
  run_id: string
  project_id: string
  request_text: string
  status: RunStatus
  model_profile: string
  started_at: string
  completed_at: string | null
  total_latency_ms: number
  total_tool_calls: number
  evidence_count: number
}

export type RunStatus =
  | "created" | "planning" | "retrieving" | "extracting"
  | "synthesizing" | "verifying" | "completed" | "paused"
  | "failed" | "needs_review" | "cancelled"

export interface TraceEvent {
  event_id: string
  sequence_no: number
  event_type: string
  component: string
  action: string | null
  status: string
  latency_ms: number | null
  input_summary: Record<string, unknown>
  output_summary: Record<string, unknown>
  evidence_ids: string[]
  model_profile: string | null
  redaction_version: string
  created_at: string
}

export interface RunTrace {
  run_id: string
  project_id: string
  user_id: string
  request_text: string
  plan: Record<string, unknown>[]
  status: RunStatus
  model_profile: string
  started_at: string
  completed_at: string | null
  error_code: string | null
  trace_events: TraceEvent[]
  total_latency_ms: number
  total_tool_calls: number
  budgets: Record<string, unknown>
  evidence_ids: string[]
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

export interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
}

export interface PaginatedRuns {
  runs: RunListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Plagiarism Types
export type PlagiarismCheckStatus = "pending" | "processing" | "completed" | "failed"

export type PlagiarismSourceType = "internal" | "external_api"

export interface PlagiarismMatch {
  id: string
  source_type: PlagiarismSourceType
  matched_text: string
  source_text: string
  similarity_score: number
  confidence_score: number
  source_document_id?: string | null
  source_document_title?: string | null
  source_url?: string | null
  source_location?: string | null
  match_start_offset?: number | null
  match_end_offset?: number | null
  created_at: string
}

export interface PlagiarismCheck {
  id: string
  user_id: string
  project_id?: string | null
  source_filename?: string | null
  source_mime_type?: string | null
  source_size_bytes?: number | null
  status: PlagiarismCheckStatus
  overall_similarity: number
  originality_score: number
  total_matches: number
  provider_used: string
  error_message?: string | null
  consented_to_store: boolean
  created_at: string
  completed_at?: string | null
}

export interface PlagiarismReport {
  check: PlagiarismCheck
  matches: PlagiarismMatch[]
  summary: string
}

export interface PlagiarismListResponse {
  checks: PlagiarismCheck[]
  total: number
  page: number
  page_size: number
}

export interface SupportedFileTypes {
  mime_types: string[]
  extensions: string[]
  max_size_mb: number
}
