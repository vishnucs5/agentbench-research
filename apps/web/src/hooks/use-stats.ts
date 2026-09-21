import { useQuery } from "@tanstack/react-query"
import { dashboardApi } from "@/lib/api"
import type { ProjectStats } from "@/types"

export function useStats(projectId: string | null) {
  return useQuery<ProjectStats>({
    queryKey: ["stats", projectId],
    queryFn: () => dashboardApi.stats(projectId!),
    enabled: !!projectId,
  })
}
