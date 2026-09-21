import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react"
import { projectsApi } from "@/lib/api"
import type { Project } from "@/types"

interface ProjectContextValue {
  projects: Project[]
  selectedProject: Project | null
  setSelectedProject: (project: Project | null) => void
  loading: boolean
  error: string | null
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

const STORAGE_KEY = "selected_project_id"

function filterDemoProjects(projects: Project[]): Project[] {
  return projects.filter((p) => p.name !== "Demo NIDS Project")
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProjectState] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (projects.length > 0 && !selectedProject) {
      const savedId = localStorage.getItem(STORAGE_KEY)
      const saved = projects.find((p) => p.id === savedId)
      if (saved) {
        setSelectedProjectState(saved)
      } else {
        setSelectedProjectState(projects[0] ?? null)
      }
    }
  }, [projects, selectedProject])

  const setSelectedProject = useCallback((project: Project | null) => {
    setSelectedProjectState(project)
    if (project) {
      localStorage.setItem(STORAGE_KEY, project.id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  async function loadProjects() {
    try {
      setLoading(true)
      setError(null)
      const data = await projectsApi.list()
      const filtered = filterDemoProjects(data)
      setProjects(filtered)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects")
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProjectContext.Provider
      value={{ projects, selectedProject, setSelectedProject, loading, error }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error("useProject must be used within a ProjectProvider")
  }
  return context
}
