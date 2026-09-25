import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { plagiarismApi } from "@/lib/api"
import type {
  PlagiarismCheck,
  PlagiarismReport,
  PlagiarismListResponse,
  SupportedFileTypes,
} from "@/types"

export function usePlagiarismChecks(
  page: number = 1,
  pageSize: number = 20,
  status: string | null = null,
) {
  return useQuery<PlagiarismListResponse>({
    queryKey: ["plagiarism-checks", page, pageSize, status],
    queryFn: () => plagiarismApi.listChecks({ page, page_size: pageSize, status }),
    staleTime: 1000 * 30, // 30 seconds
  })
}

export function usePlagiarismReport(checkId: string | null) {
  return useQuery<PlagiarismReport | null>({
    queryKey: ["plagiarism-report", checkId],
    queryFn: () => (checkId ? plagiarismApi.getReport(checkId) : null),
    enabled: Boolean(checkId),
  })
}

export function usePlagiarismSupportedTypes() {
  return useQuery<SupportedFileTypes>({
    queryKey: ["plagiarism-supported-types"],
    queryFn: () => plagiarismApi.getSupportedTypes(),
    staleTime: 1000 * 60 * 60, // 1 hour
  })
}

export function useCheckTextMutation() {
  const queryClient = useQueryClient()
  return useMutation<
    PlagiarismCheck,
    Error,
    {
      text: string
      project_id?: string | null
      threshold?: number | null
      consented_to_store?: boolean
    }
  >({
    mutationFn: (data) => plagiarismApi.checkText(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plagiarism-checks"] })
    },
  })
}

export function useCheckFileMutation() {
  const queryClient = useQueryClient()
  return useMutation<PlagiarismCheck, Error, FormData>({
    mutationFn: (formData) => plagiarismApi.checkFile(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plagiarism-checks"] })
    },
  })
}

export function useDeleteCheckMutation() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (checkId) => plagiarismApi.deleteCheck(checkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plagiarism-checks"] })
    },
  })
}
