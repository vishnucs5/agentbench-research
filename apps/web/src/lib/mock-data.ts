export const MOCK_STATS = {
  total_papers: 0,
  total_runs: 0,
  completed_runs: 0,
  failed_runs: 0,
  total_evidence: 0,
  avg_latency_ms: 0,
  recent_runs: [],
}

export const MOCK_PIPELINE = [
  { phase: 0, name: "Foundation", status: "done" as const },
  { phase: 1, name: "Ingestion", status: "done" as const },
  { phase: 2, name: "Retrieval", status: "done" as const },
  { phase: 3, name: "Extraction", status: "done" as const },
  { phase: 4, name: "Synthesis", status: "done" as const },
  { phase: 5, name: "Verification", status: "done" as const },
  { phase: 6, name: "Evaluation", status: "done" as const },
  { phase: 7, name: "Dashboard", status: "active" as const },
]
