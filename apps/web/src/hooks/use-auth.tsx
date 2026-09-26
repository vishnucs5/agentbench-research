import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { api, authApi, setToken, clearToken } from "@/lib/api"
import { queryClient } from "@/lib/query-client"

interface AuthContextValue {
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string, role?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => {
    return localStorage.getItem("token")
  })

  const isAuthenticated = token !== null

  const login = useCallback(async (email: string, password: string) => {
    clearToken()
    queryClient.clear()
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setTokenState(res.access_token)
    try {
      const me = await api<{ id: string; email: string; full_name: string; role: string }>("/v1/auth/me")
      localStorage.setItem("user", JSON.stringify(me))
    } catch {
      localStorage.setItem("user", JSON.stringify({ email, full_name: "Researcher" }))
    }
  }, [])

  const register = useCallback(
    async (email: string, password: string, fullName: string, role?: string) => {
      await authApi.register({ email, password, full_name: fullName, role })
      queryClient.clear()
      const res = await authApi.login({ email, password })
      setToken(res.access_token)
      setTokenState(res.access_token)
      try {
        const me = await api<{ id: string; email: string; full_name: string; role: string }>("/v1/auth/me")
        localStorage.setItem("user", JSON.stringify(me))
      } catch {
        localStorage.setItem("user", JSON.stringify({ email, full_name: fullName }))
      }
    },
    [],
  )

  const logout = useCallback(() => {
    clearToken()
    setTokenState(null)
    localStorage.removeItem("user")
    queryClient.clear()
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem("token")
    if (stored) {
      setTokenState(stored)
      if (!localStorage.getItem("user")) {
        api<{ id: string; email: string; full_name?: string; role?: string }>("/v1/auth/me")
          .then((me: { id: string; email: string; full_name?: string; role?: string }) => {
            localStorage.setItem("user", JSON.stringify(me))
          })
          .catch(() => {})
      }
    }

    const handleUnauthorized = () => {
      clearToken()
      setTokenState(null)
      localStorage.removeItem("user")
      queryClient.clear()
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized)
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
