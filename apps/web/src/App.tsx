import { useState } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/hooks/use-auth"
import { ProjectProvider } from "@/contexts/ProjectContext"
import AppShell from "@/components/layout/AppShell"
import { LoginOverlay } from "@/components/auth/LoginOverlay"
import { RegisterOverlay } from "@/components/auth/RegisterOverlay"
import Overview from "@/pages/Overview"
import Projects from "@/pages/Projects"
import TraceReplay from "@/pages/TraceReplay"
import Settings from "@/pages/Settings"

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
    <BrowserRouter>
      <AuthProvider>
        <AuthGate />
      </AuthProvider>
    </BrowserRouter>
  )
}
