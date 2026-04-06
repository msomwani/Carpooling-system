"use client"

import { useAuth } from "@/lib/AuthContext"
import { useRole } from "@/lib/RoleContext"
import { Button } from "@/components/ui/button"
import { Car, User } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api"

export function RoleSwitcher() {
  const { user, getAuthHeaders } = useAuth()
  const { role } = useRole()

  const switchRole = async (newRole: "passenger" | "driver") => {
    // Optimistically update localStorage for instant UI response
    localStorage.setItem("user-role", newRole)
    // Force a re-render by dispatching a storage event (RoleContext picks this up)
    window.dispatchEvent(new StorageEvent("storage", { key: "user-role", newValue: newRole }))

    // Persist to backend
    try {
      const res = await fetch(`${API_URL}/users/me/role`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        credentials: "include",
        body: JSON.stringify({ role: newRole }),
      })
      if (!res.ok) {
        throw new Error(`Failed to update role: ${res.statusText}`)
      }
      // If we are logged in, we should ideally refresh the user object 
      // but for now, the RoleContext handles the UI side via storage events
    } catch (e) {
      console.error("Failed to update role in backend:", e)
    }
  }

  return (
    <div className="flex bg-muted p-1 rounded-full items-center">
      <Button
        variant={role === "passenger" ? "default" : "ghost"}
        size="sm"
        className={`rounded-full px-4 py-1 text-xs h-8 ${role === "passenger" ? "shadow-sm" : "text-muted-foreground"
          }`}
        onClick={() => switchRole("passenger")}
      >
        <User className="w-3 h-3 mr-1" />
        Passenger
      </Button>
      <Button
        variant={role === "driver" ? "default" : "ghost"}
        size="sm"
        className={`rounded-full px-4 py-1 text-xs h-8 ${role === "driver" ? "shadow-sm" : "text-muted-foreground"
          }`}
        onClick={() => switchRole("driver")}
      >
        <Car className="w-3 h-3 mr-1" />
        Driver
      </Button>
    </div>
  )
}
