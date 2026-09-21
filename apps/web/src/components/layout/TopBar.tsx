import { useAuth } from "@/hooks/use-auth"
import { useProject } from "@/contexts/ProjectContext"
import { useWebSocket } from "@/hooks/use-websocket"
import LiveIndicator from "@/components/dashboard/LiveIndicator"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { FolderOpen } from "lucide-react"

export default function TopBar() {
  const { logout } = useAuth()
  const { projects, selectedProject, setSelectedProject } = useProject()
  const { isConnected } = useWebSocket(selectedProject?.id ?? null)

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border bg-panel px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">Project</span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-md bg-secondary px-2 py-1 text-xs text-muted-foreground hover:bg-secondary/80">
              <FolderOpen className="h-3 w-3" />
              {selectedProject?.name ?? "Select project"}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="border-border bg-panel w-56">
            {projects.length === 0 ? (
              <DropdownMenuItem className="text-xs text-muted-foreground" disabled>
                No projects available
              </DropdownMenuItem>
            ) : (
              projects.map((project) => (
                <DropdownMenuItem
                  key={project.id}
                  onClick={() => setSelectedProject(project)}
                  className={`text-xs ${selectedProject?.id === project.id ? "text-accent" : "text-muted-foreground"}`}
                >
                  <FolderOpen className="h-3 w-3 mr-2" />
                  {project.name}
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="ml-auto flex items-center gap-4">
        <div className="relative hidden w-72 md:block">
          <Input
            placeholder="Ask over papers... (hybrid retrieval)"
            className="h-8 border-border bg-background pl-8 text-xs"
          />
          <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-border bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">
            ⌘K
          </kbd>
        </div>

        <div className="hidden items-center gap-2 lg:flex">
          <LiveIndicator isConnected={isConnected} />
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
              R
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="border-border bg-panel">
            <DropdownMenuItem className="text-xs text-muted-foreground" disabled>
              Researcher
            </DropdownMenuItem>
            <DropdownMenuItem onClick={logout} className="text-xs text-destructive">
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
