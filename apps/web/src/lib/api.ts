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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `API error ${res.status}`)
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
  list: () => api<{ items: any[] }>("/v1/projects"),
  get: (id: string) => api<any>(`/v1/projects/${id}`),
  create: (data: { name: string; domain: string; retention_days?: number }) =>
    api<any>("/v1/projects", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/v1/projects/${id}`, { method: "DELETE" }),
}

// Dashboard
export const dashboardApi = {
  stats: (projectId: string) =>
    api<any>(`/v1/dashboard/projects/${projectId}/stats`),
}

// Papers
export const papersApi = {
  list: (projectId: string) =>
    api<{ items: any[] }>(`/v1/projects/${projectId}/papers`),
}

// Trace Replay
export const traceApi = {
  listRuns: (projectId: string) =>
    api<{ items: any[] }>(`/v1/dashboard/projects/${projectId}/runs`),
  getRun: (runId: string) => api<any>(`/v1/dashboard/runs/${runId}/trace`),
}

// Health
export const healthApi = {
  check: () => api<any>("/healthz"),
}
