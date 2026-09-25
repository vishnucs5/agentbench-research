import { useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { queryClient } from "@/lib/query-client"
import { AuthProvider, useAuth } from "@/hooks/use-auth"
import { ProjectProvider } from "@/contexts/ProjectContext"
import AppShell from "@/components/layout/AppShell"
import { LoginOverlay } from "@/components/auth/LoginOverlay"
import { RegisterOverlay } from "@/components/auth/RegisterOverlay"
import Overview from "@/pages/Overview"
import Projects from "@/pages/Projects"
import TraceReplay from "@/pages/TraceReplay"
import Settings from "@/pages/Settings"
import PlagiarismChecker from "@/pages/PlagiarismChecker"

function AuthGate() {
  const { isAuthenticated } = useAuth()
  const [showRegister, setShowRegister] = useState(false)

  if (isAuthenticated) {
    return (
      <ProjectProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Overview />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/trace" element={<TraceReplay />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/dashboard/plagiarism-checker" element={<PlagiarismChecker />} />
            <Route path="/plagiarism" element={<Navigate to="/dashboard/plagiarism-checker" replace />} />
            <Route path="/plagiarism-checker" element={<Navigate to="/dashboard/plagiarism-checker" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ProjectProvider>
    )
  }

  return showRegister ? (
    <RegisterOverlay onSwitchToLogin={() => setShowRegister(false)} />
  ) : (
    <LoginOverlay onSwitchToRegister={() => setShowRegister(true)} />
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AuthGate />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
