import { useState } from "react"
import { useAuth } from "@/hooks/use-auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"

interface LoginOverlayProps {
  onSwitchToRegister: () => void
}

export function LoginOverlay({ onSwitchToRegister }: LoginOverlayProps) {
  const { login } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
      <Card className="w-full max-w-md border-border bg-panel">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-accent">
            AgentBench Research
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Evidence-grounded autonomous research agent · Network Intrusion Detection
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="demo@test.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Demo1234!"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Signing in...
                </span>
              ) : (
                "Sign in & Launch"
              )}
            </Button>
          </form>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Demo: demo@test.com / Demo1234!
            </span>
          </div>
          <div className="mt-3 flex gap-2">
            <Badge variant="secondary">OpenRouter</Badge>
            <Badge variant="secondary">Hybrid Retrieval</Badge>
          </div>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            No account?{" "}
            <button
              type="button"
              onClick={onSwitchToRegister}
              className="text-accent hover:underline"
            >
              Create one
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
