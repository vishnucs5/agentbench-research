import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Search,
  Zap,
  Layers,
  ShieldCheck,
  FileBarChart,
  BarChart3,
  GitBranch,
  Settings,
  ExternalLink,
} from "lucide-react"
import { Separator } from "@/components/ui/separator"

interface NavItem {
  label: string
  path: string
  icon: React.ReactNode
}

const workspaceNav: NavItem[] = [
  { label: "Overview", path: "/", icon: <LayoutDashboard size={18} /> },
  { label: "Projects", path: "/projects", icon: <FolderOpen size={18} /> },
  { label: "Papers", path: "/papers", icon: <FileText size={18} /> },
  { label: "Retrieval", path: "/retrieval", icon: <Search size={18} /> },
  { label: "Extraction", path: "/extraction", icon: <Zap size={18} /> },
  { label: "Synthesis", path: "/synthesis", icon: <Layers size={18} /> },
  { label: "Verification", path: "/verification", icon: <ShieldCheck size={18} /> },
  { label: "Reports", path: "/reports", icon: <FileBarChart size={18} /> },
  { label: "Evaluation", path: "/evaluation", icon: <BarChart3 size={18} /> },
  { label: "Trace Replay", path: "/trace", icon: <GitBranch size={18} /> },
]

const systemNav: NavItem[] = [
  { label: "Settings", path: "/settings", icon: <Settings size={18} /> },
  { label: "API Docs", path: "/api-docs", icon: <ExternalLink size={18} /> },
]

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      end={item.path === "/"}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
          isActive
            ? "bg-accent/10 text-accent border-l-2 border-accent"
            : "text-muted-foreground hover:bg-panel-light hover:text-foreground border-l-2 border-transparent"
        }`
      }
    >
      {item.icon}
      <span>{item.label}</span>
    </NavLink>
  )
}

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-full w-[260px] flex-col border-r border-border bg-panel">
      <div className="flex flex-col gap-1 px-4 pt-5 pb-3">
        <h1 className="text-lg font-bold text-accent">AgentBench Research</h1>
        <p className="text-xs text-muted-foreground">Research v0.1.0</p>
        <span className="mt-1 inline-flex w-fit items-center rounded-md bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
          openrouter · balanced
        </span>
      </div>

      <Separator className="bg-border" />

      <nav className="flex-1 overflow-y-auto px-3 py-3">
        <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Workspace
        </p>
        <div className="flex flex-col gap-0.5">
          {workspaceNav.map((item) => (
            <SidebarLink key={item.path} item={item} />
          ))}
        </div>

        <Separator className="my-3 bg-border" />

        <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          System
        </p>
        <div className="flex flex-col gap-0.5">
          {systemNav.map((item) => (
            <SidebarLink key={item.path} item={item} />
          ))}
        </div>
      </nav>

      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
            R
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">Researcher</span>
            <span className="text-[10px] text-muted-foreground">Admin</span>
          </div>
          <span className="ml-auto h-2 w-2 rounded-full bg-green-500" />
        </div>
      </div>
    </aside>
  )
}
