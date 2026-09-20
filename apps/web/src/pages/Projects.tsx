import { useEffect, useState } from "react"
import { projectsApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { FolderOpen, FolderSearch } from "lucide-react"

interface Project {
  id: string
  name: string
  domain: string
  retention_days: number
  paper_count?: number
  created_at?: string
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({
    name: "",
    domain: "network-intrusion-detection",
    retention_days: 90,
  })
  const { toast } = useToast()

  useEffect(() => {
    loadProjects()
  }, [])

  async function loadProjects() {
    try {
      setLoading(true)
      const res = await projectsApi.list()
      setProjects(res.items ?? [])
    } catch (err) {
      toast({
        title: "Failed to load projects",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate() {
    if (!form.name.trim()) {
      toast({ title: "Project name is required", variant: "destructive" })
      return
    }
    try {
      setCreating(true)
      const created = await projectsApi.create({
        name: form.name.trim(),
        domain: form.domain,
        retention_days: form.retention_days,
      })
      setProjects((prev) => [...prev, created])
      setDialogOpen(false)
      setForm({ name: "", domain: "network-intrusion-detection", retention_days: 90 })
      toast({ title: "Project created", description: `"${created.name}" is ready.` })
    } catch (err) {
      toast({
        title: "Failed to create project",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      })
    } finally {
      setCreating(false)
    }
  }

  function formatDate(iso?: string) {
    if (!iso) return "—"
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#CFFF4B]">
            PROJECTS
          </p>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-[#64748B]">
            Workspaces with retention · Domain: network-intrusion-detection
          </p>
        </div>
        <Button
          className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold"
          onClick={() => setDialogOpen(true)}
        >
          + New Project
        </Button>
      </div>

      {/* Loading State */}
      {loading && (
        <Card className="bg-[#101A26] border-[#1E293B] p-6">
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-4 w-[180px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[120px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[80px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[60px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[100px] bg-[#1E293B]" />
                <Skeleton className="h-4 w-[70px] bg-[#1E293B]" />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!loading && projects.length === 0 && (
        <Card className="bg-[#101A26] border-[#1E293B] p-12 flex flex-col items-center justify-center text-center">
          <FolderSearch className="h-12 w-12 text-[#64748B] mb-4" />
          <p className="text-white font-medium mb-1">No projects yet</p>
          <p className="text-[#64748B] text-sm">
            Create one to start researching.
          </p>
        </Card>
      )}

      {/* Projects Table */}
      {!loading && projects.length > 0 && (
        <Card className="bg-[#101A26] border-[#1E293B]">
          <Table>
            <TableHeader>
              <TableRow className="border-[#1E293B] hover:bg-transparent">
                <TableHead className="text-[#64748B] font-semibold">Name</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Domain</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Retention</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Papers</TableHead>
                <TableHead className="text-[#64748B] font-semibold">Last Activity</TableHead>
                <TableHead className="text-[#64748B] font-semibold text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id} className="border-[#1E293B]">
                  <TableCell className="font-medium text-white">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="h-4 w-4 text-[#CFFF4B]" />
                      {project.name}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className="border-[#1E293B] text-[#94A3B8] bg-transparent"
                    >
                      {project.domain}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-[#94A3B8]">
                    {project.retention_days}d
                  </TableCell>
                  <TableCell className="text-[#94A3B8]">
                    {project.paper_count ?? 0}
                  </TableCell>
                  <TableCell className="text-[#94A3B8]">
                    {formatDate(project.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-[#CFFF4B] hover:text-[#CFFF4B] hover:bg-[#CFFF4B]/10"
                    >
                      Open
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* New Project Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="bg-[#101A26] border-[#1E293B] text-white">
          <DialogHeader>
            <DialogTitle className="text-white">New Project</DialogTitle>
            <DialogDescription className="text-[#64748B]">
              Create a new research workspace.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="project-name" className="text-[#94A3B8]">
                Project Name
              </Label>
              <Input
                id="project-name"
                placeholder="e.g., NIDS Survey 2026"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="bg-[#0D1420] border-[#1E293B] text-white placeholder:text-[#64748B]"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="project-domain" className="text-[#94A3B8]">
                Domain
              </Label>
              <Input
                id="project-domain"
                value={form.domain}
                onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
                className="bg-[#0D1420] border-[#1E293B] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="project-retention" className="text-[#94A3B8]">
                Retention (days)
              </Label>
              <Input
                id="project-retention"
                type="number"
                min={1}
                value={form.retention_days}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    retention_days: parseInt(e.target.value, 10) || 90,
                  }))
                }
                className="bg-[#0D1420] border-[#1E293B] text-white"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setDialogOpen(false)}
              className="text-[#64748B] hover:text-white"
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={creating}
              className="bg-[#CFFF4B] text-black hover:bg-[#CFFF4B]/90 font-semibold"
            >
              {creating ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
