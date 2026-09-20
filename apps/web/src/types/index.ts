export interface User {
  id: string
  email: string
  full_name: string
  role: "viewer" | "researcher" | "supervisor" | "admin"
}

export interface Project {
  id: string
  name: string
  domain: string
  retention_days: number
  created_at: string
  updated_at: string
  paper_count?: number
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
  id: string
  status: RunStatus
  latency_ms: number
  tool_calls: number
  evidence_count: number
  model: string
  created_at: string
}

export type RunStatus =
  | "created" | "planning" | "retrieving" | "extracting"
  | "synthesizing" | "verifying" | "completed" | "paused"
  | "failed" | "needs_review" | "cancelled"

export interface TraceEvent {
  id: string
  sequence_no: number
  event_type: string
  component: string
  status: string
  latency_ms: number
  input_summary: string
  output_summary: string
  evidence_ids: string[]
  metadata: Record<string, unknown>
}

export interface RunTrace {
  run_id: string
  project_id: string
  status: RunStatus
  total_latency_ms: number
  tool_calls: number
  evidence_ids: string[]
  model: string
  events: TraceEvent[]
  created_at: string
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
