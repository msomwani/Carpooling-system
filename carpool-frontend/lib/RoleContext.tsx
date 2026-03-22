"use client"

import React, { createContext, useContext, useState, useEffect } from "react"

type Role = "passenger" | "driver"

interface RoleContextType {
  role: Role
  setRole: (role: Role) => void
}

const RoleContext = createContext<RoleContextType | undefined>(undefined)

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<Role>("passenger")

  // Load from localStorage on mount
  useEffect(() => {
    const savedRole = localStorage.getItem("user-role") as Role
    if (savedRole && (savedRole === "passenger" || savedRole === "driver")) {
      setRole(savedRole)
    }

    // React to programmatic StorageEvent dispatches from RoleSwitcher
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "user-role" && e.newValue && (e.newValue === "passenger" || e.newValue === "driver")) {
        setRole(e.newValue as Role)
      }
    }
    window.addEventListener("storage", handleStorage)
    return () => window.removeEventListener("storage", handleStorage)
  }, [])

  const handleSetRole = (newRole: Role) => {
    setRole(newRole)
    localStorage.setItem("user-role", newRole)
  }

  return (
    <RoleContext.Provider value={{ role, setRole: handleSetRole }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole() {
  const context = useContext(RoleContext)
  if (context === undefined) {
    throw new Error("useRole must be used within a RoleProvider")
  }
  return context
}
