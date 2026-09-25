import type {
  Project,
  RunTrace,
  PaginatedRuns,
  ProjectStats,
  PlagiarismCheck,
  PlagiarismReport,
  PlagiarismListResponse,
  SupportedFileTypes,
} from "@/types"

const API_BASE = ""

function getToken(): string | null {
  return localStorage.getItem("token")
}

export function setToken(token: string) {
  localStorage.setItem("token", token)
}

export function clearToken() {
  localStorage.removeItem("token")
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json()
}

// Auth
export const authApi = {
  login: (data: { email: string; password: string }) =>
    api<{ access_token: string; token_type: string }>("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  register: (data: {
    email: string; password: string; full_name: string; role?: string
  }) =>
    api<{ id: string; email: string }>("/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
}

// Projects
export const projectsApi = {
  list: () => api<Project[]>("/v1/projects"),
  get: (id: string) => api<Project>(`/v1/projects/${id}`),
  create: (data: { name: string; domain: string; retention_days?: number }) =>
    api<Project>("/v1/projects", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/v1/projects/${id}`, { method: "DELETE" }),
}

// Dashboard
export const dashboardApi = {
  stats: (projectId: string) =>
    api<ProjectStats>(`/v1/dashboard/projects/${projectId}/stats`),
}

// Papers
export const papersApi = {
  list: (projectId: string) =>
    api<{ papers: any[]; total: number; page: number; page_size: number }>(`/v1/projects/${projectId}/papers`),
}

// Trace Replay
export const traceApi = {
  listRuns: (projectId: string) =>
    api<PaginatedRuns>(`/v1/dashboard/projects/${projectId}/runs`),
  getRun: (runId: string) => api<RunTrace>(`/v1/dashboard/runs/${runId}/trace`),
}

// Plagiarism
export const plagiarismApi = {
  checkText: (data: {
    text: string
    project_id?: string | null
    threshold?: number | null
    consented_to_store?: boolean
  }) =>
    api<PlagiarismCheck>("/v1/plagiarism/check/text", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  checkFile: (formData: FormData) =>
    api<PlagiarismCheck>("/v1/plagiarism/check/file", {
      method: "POST",
      body: formData,
    }),

  listChecks: (params?: { page?: number; page_size?: number; status?: string | null }) => {
    const query = new URLSearchParams()
    if (params?.page) query.set("page", params.page.toString())
    if (params?.page_size) query.set("page_size", params.page_size.toString())
    if (params?.status) query.set("status", params.status)
    const qs = query.toString()
    return api<PlagiarismListResponse>(`/v1/plagiarism/checks${qs ? `?${qs}` : ""}`)
  },

  getReport: (checkId: string) =>
    api<PlagiarismReport>(`/v1/plagiarism/checks/${checkId}`),

  deleteCheck: (checkId: string) =>
    api<void>(`/v1/plagiarism/checks/${checkId}`, {
      method: "DELETE",
    }),

  getSupportedTypes: () =>
    api<SupportedFileTypes>("/v1/plagiarism/supported-types"),
}

// Health
export const healthApi = {
  check: () => api<any>("/healthz"),
}
