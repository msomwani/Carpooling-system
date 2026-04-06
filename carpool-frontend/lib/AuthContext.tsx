"use client"

import React, { createContext, useContext, useState, useEffect, useRef } from "react"
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
    // ----- Global fetch interceptor for JWT refresh -----
    // Save the original fetch function so we can restore it later and also use it inside logout.
    const original = window.fetch.bind(window)
    // Expose the original fetch to the logout function via the ref.
    originalFetchRef.current = original
    // Use a ref to hold the refresh promise so we only have one in‑flight request.
    let refreshPromise: Promise<void> | null = null
    // Helper to decide whether we should attach credentials.
    const shouldAddCredentials = (url: string): boolean => {
      // Only add credentials for our own API calls (relative paths or API_URL base).
      return url.startsWith('/') || url.startsWith(API_URL)
    }
    // @ts-ignore – we are monkey‑patching the global fetch.
    window.fetch = async (input: RequestInfo, init: RequestInit = {}): Promise<Response> => {
      // Resolve the URL string for later checks.
      const url = typeof input === 'string' ? input : input.url

      // Bypass interceptor for logout endpoint to avoid deadlock.
      if (url.endsWith('/auth/logout')) {
        return original(input, init)
      }

      // Attach credentials only for our own API endpoints.
      if (shouldAddCredentials(url)) {
        init.credentials = "include"
      }

      let response = await original(input, init)

      // If we get a 401 on our own API (but not on the refresh endpoint), try to refresh the token.
      if (response.status === 401 && shouldAddCredentials(url) && !url.endsWith('/auth/refresh-token')) {
        // Ensure only a single refresh request runs at a time.
        if (!refreshPromise) {
          refreshPromise = (async () => {
            try {
              const refreshRes = await original(`${API_URL}/auth/refresh-token`, {
                method: "POST",
                // Credentials already needed for the refresh endpoint.
                credentials: "include",
              })
              if (!refreshRes.ok) {
                // Refresh failed – log the user out.
                logout()
                return
              }
              // Refresh succeeded – nothing else to do here.
            } catch {
              // Network or other error – also log out.
              logout()
            } finally {
              // Reset for next possible refresh.
              refreshPromise = null
            }
          })()
        }
        // Wait for the refresh to finish before retrying.
        await refreshPromise
        // Retry the original request after a successful refresh.
        response = await original(input, init)
      }
      return response
    }
    // Cleanup on unmount: restore original fetch.
    return () => {
      // @ts-ignore
      window.fetch = original
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** Called after a successful Google login. Stores only public user info; token is in the cookie. */
  const login = (userData: User) => {
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    setUser(userData)
  }

  // Store a reference to the *original* fetch function so we can bypass the interceptor when needed.
  const originalFetchRef = React.useRef<(input: RequestInfo, init?: RequestInit) => Promise<Response>>(() => Promise.reject());

  const logout = async () => {
    // Tell the server to expire the HTTP-only cookie using the *original* fetch to avoid the interceptor.
    try {
      await originalFetchRef.current(`${API_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      })
    } catch {
      // Best‑effort – continue with local cleanup even if the request fails.
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
