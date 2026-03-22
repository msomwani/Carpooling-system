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
  token: string | null
  isLoading: boolean
  logout: () => void
  login: (user: User, token: string) => void
  getAuthHeaders: () => Record<string, string>
}

const USER_KEY = "croc_ride_user"
const TOKEN_KEY = "croc_ride_token"

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Rehydrate from localStorage on mount
  useEffect(() => {
    try {
      const storedUser = localStorage.getItem(USER_KEY)
      const storedToken = localStorage.getItem(TOKEN_KEY)
      
      // If we have a user but no token, this is a stale session from the old auth system.
      // Clear it so the user is forced to log in again and get a proper JWT.
      if (storedUser && !storedToken) {
        localStorage.removeItem(USER_KEY)
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        setToken(null)
      } else {
        if (storedUser) setUser(JSON.parse(storedUser))
        if (storedToken) setToken(storedToken)
      }
    } catch {
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(TOKEN_KEY)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = (userData: User, accessToken: string) => {
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    localStorage.setItem(TOKEN_KEY, accessToken)
    setUser(userData)
    setToken(accessToken)
  }

  const logout = () => {
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setToken(null)
    router.push("/")
  }

  /** Returns headers with Authorization Bearer token for authenticates API calls */
  const getAuthHeaders = (): Record<string, string> => {
    const storedToken = token || localStorage.getItem(TOKEN_KEY)
    if (!storedToken) return { "Content-Type": "application/json" }
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${storedToken}`,
    }
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, logout, login, getAuthHeaders }}>
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
