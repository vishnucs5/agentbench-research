import React, { createContext, useCallback, useContext, useEffect, useState } from "react"
import { authApi, setToken, clearToken } from "@/lib/api"

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
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setTokenState(res.access_token)
  }, [])

  const register = useCallback(
    async (email: string, password: string, fullName: string, role?: string) => {
      await authApi.register({ email, password, full_name: fullName, role })
      const res = await authApi.login({ email, password })
      setToken(res.access_token)
      setTokenState(res.access_token)
    },
    [],
  )

  const logout = useCallback(() => {
    clearToken()
    setTokenState(null)
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem("token")
    if (stored) setTokenState(stored)
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
