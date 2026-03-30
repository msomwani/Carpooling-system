"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { useRouter } from "next/navigation"

interface User {
  id: string
  name: string
  email: string
  role: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  logout: () => void
  login: (user: User) => void
  getAuthHeaders: () => Record<string, string>
}

const USER_KEY = "croc_ride_user"
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Rehydrate user profile from localStorage on mount.
  // NOTE: Only the non-sensitive user object (name, email, role) is stored in
  // localStorage. The JWT itself lives exclusively in an HTTP-only cookie that
  // JavaScript cannot read or steal via XSS.
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem(USER_KEY)
      if (storedUser) setUser(JSON.parse(storedUser))
    } catch {
      localStorage.removeItem(USER_KEY)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /** Called after a successful Google login. Stores only public user info; token is in the cookie. */
  const login = (userData: User) => {
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    setUser(userData)
  }

  const logout = async () => {
    // Tell the server to expire the HTTP-only cookie.
    // JavaScript cannot delete HTTP-only cookies itself — the server must do it.
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        credentials: "include", // required to send/receive cookies cross-origin
      })
    } catch {
      // Best-effort — proceed with local cleanup even if the request fails.
    }
    localStorage.removeItem(USER_KEY)
    setUser(null)
    router.push("/")
  }

  /**
   * Returns headers for authenticated API calls.
   * 
   * The JWT is in an HTTP-only cookie, so there is no Authorization header.
   * Instead, callers MUST use `credentials: "include"` in fetch so the browser
   * automatically attaches the cookie to every request.
   */
  const getAuthHeaders = (): Record<string, string> => {
    return { "Content-Type": "application/json" }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, logout, login, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
