"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home, Calendar, User } from "lucide-react"

export function BottomNav() {
  const pathname = usePathname()
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
  }, [])

  if (!isMounted) return null

  const tabs = [
    { name: "Home", icon: Home, href: "/" },
    { name: "Booking", icon: Calendar, href: "/bookings" },
    { name: "Account", icon: User, href: "/login" }, // Assuming /login leads to account or login
  ]

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-background border-t pb-safe">
      <div className="flex justify-around items-center h-16 max-w-md mx-auto">
        {tabs.map((tab) => {
          const isActive = pathname === tab.href
          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={`flex flex-col items-center justify-center w-full h-full gap-1 transition-colors ${
                isActive ? "text-primary" : "text-muted-foreground hover:text-primary/70"
              }`}
            >
              <tab.icon className={`h-6 w-6 ${isActive ? "fill-primary/10" : ""}`} />
              <span className="text-[10px] font-medium leading-none">{tab.name}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
