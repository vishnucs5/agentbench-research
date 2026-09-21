import { useQuery } from "@tanstack/react-query"
import { traceApi } from "@/lib/api"
import type { PaginatedRuns, RunTrace } from "@/types"

interface UseRunsOptions {
  projectId: string | null
  page?: number
  pageSize?: number
  status?: string[]
  search?: string
}

export function useRuns({
  projectId,
  page = 1,
  pageSize = 20,
  status,
  search,
}: UseRunsOptions) {
  return useQuery<PaginatedRuns>({
    queryKey: ["runs", projectId, page, pageSize, status, search],
    queryFn: async () => {
      // Build query params
      const params = new URLSearchParams()
      params.set("page", page.toString())
      params.set("page_size", pageSize.toString())
      if (status?.length) params.set("status", status.join(","))
      if (search) params.set("search", search)

      const res = await fetch(
        `/v1/dashboard/projects/${projectId}/runs?${params}`
      )
      return res.json()
    },
    enabled: !!projectId,
  })
}

export function useRunTrace(runId: string | null) {
  return useQuery<RunTrace>({
    queryKey: ["trace", runId],
    queryFn: () => traceApi.getRun(runId!),
    enabled: !!runId,
  })
}
