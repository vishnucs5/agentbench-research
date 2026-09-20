import { useAuth } from "@/hooks/use-auth"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export default function TopBar() {
  const { logout } = useAuth()

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border bg-panel px-6">
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">Project</span>
        <span className="rounded-md bg-secondary px-2 py-1 text-xs text-muted-foreground">
          Default
        </span>
      </div>

      <Button variant="outline" size="sm" className="ml-2 border-border text-xs">
        + New Project
      </Button>

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

        <div className="hidden items-center gap-2 text-[10px] text-muted-foreground lg:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Live API · SQLite · Qdrant Mock · MinIO Mock
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
