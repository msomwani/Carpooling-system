"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import Link from "next/link"
import { useAuth } from "@/lib/AuthContext"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Loader2,
  LogOut,
  User,
  Mail,
  Phone,
  Edit2,
  Check,
  X,
  Award,
  TrendingUp,
  Wallet,
  ShieldCheck,
  Star,
  Settings,
  ChevronRight,
  Bell,
  CreditCard
} from "lucide-react"

export default function AccountPage() {
  const { user, isLoading, logout } = useAuth()
  const router = useRouter()

  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    phone: "",
    age: "24" // Default mock age
  })

  // Mock analytics data
  const stats = [
    { label: "Completed", value: "12", icon: Award, color: "text-primary", bg: "bg-primary/10" },
    { label: "Created", value: "5", icon: TrendingUp, color: "text-blue-500", bg: "bg-blue-500/10" },
    { label: "Earnings", value: "₹1,250", icon: Wallet, color: "text-green-500", bg: "bg-green-500/10" },
    { label: "Miles", value: "450", icon: Star, color: "text-orange-500", bg: "bg-orange-500/10" }
  ]

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login")
    } else if (user) {
      setProfile({
        name: user.name || "",
        email: user.email || "",
        phone: (user as any).phone_number || "",
        age: (user as any).age || "24"
      })
    }
  }, [user, isLoading, router])

  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-muted-foreground font-medium animate-pulse">Loading profile...</p>
        </div>
      </div>
    )
  }

  const handleSave = () => {
    console.log("Profile update requested:", profile)
    setIsEditing(false)
  }

  return (
    <div className="min-h-screen bg-muted/30 dark:bg-background pb-32">
      {/* Premium Header */}
      <header className="bg-background/80 backdrop-blur-xl border-b sticky top-0 z-50 px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="relative w-7 h-7">
              <Image src="/croc_mascot.png" alt="Croc" fill className="object-contain" />
            </div>
            <h1 className="text-lg font-bold">Croc Ride</h1>
          </div>
        </div>

      </header>

      <main className="max-w-xl mx-auto p-4 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

        {/* Section 1: Analytics */}
        <section className="space-y-4">
          <div className="px-2">
            <h2 className="text-xl font-black tracking-tight">Analytics</h2>
            <p className="text-muted-foreground text-xs font-medium">Your performance and impact at a glance</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {stats.map((stat, i) => (
              <Card key={i} className="rounded-3xl border-none shadow-sm bg-background p-5 hover:shadow-md transition-shadow">
                <div className="flex flex-col gap-3">
                  <div className={`${stat.bg} ${stat.color} w-9 h-9 rounded-xl flex items-center justify-center`}>
                    <stat.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none mb-1">{stat.label}</p>
                    <p className={`text-xl font-black ${stat.color} tracking-tighter`}>{stat.value}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Section 2: Personal Details */}
        <section className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <div>
              <h2 className="text-xl font-black tracking-tight">Personal Details</h2>
              <p className="text-muted-foreground text-xs font-medium">Manage your personal information</p>
            </div>
            {!isEditing ? (
              <Button onClick={() => setIsEditing(true)} variant="ghost" size="sm" className="h-8 rounded-full text-xs font-bold text-primary hover:bg-primary/5">
                <Edit2 className="h-3.5 w-3.5 mr-1" /> Edit
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button onClick={() => setIsEditing(false)} variant="ghost" size="sm" className="h-8 rounded-full text-xs font-bold text-muted-foreground">
                  Cancel
                </Button>
                <Button onClick={handleSave} size="sm" className="h-8 rounded-full text-xs font-bold px-4">
                  Save
                </Button>
              </div>
            )}
          </div>

          <Card className="rounded-[2.5rem] border shadow-sm bg-background overflow-hidden">
            <div className="p-6 space-y-6">
              {/* Profile Header */}
              <div className="flex items-center gap-4 pb-2">
                <div className="relative">
                  <div className="w-16 h-16 rounded-2xl bg-muted/30 flex items-center justify-center text-primary border shadow-inner">
                    <User className="h-8 w-8 opacity-40" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 bg-background p-1 rounded-full shadow-lg border">
                    <ShieldCheck className="h-3 w-3 text-green-500" />
                  </div>
                </div>
                <div className="space-y-1">
                  <h3 className="text-lg font-black tracking-tight">{profile.name || "Croc Rider"}</h3>
                  <Badge variant="secondary" className="bg-primary/10 text-primary border-none font-bold px-2 py-0 rounded-full text-[9px] uppercase tracking-wider">Gold Member</Badge>
                </div>
              </div>

              <div className="grid gap-6">
                {[
                  { label: "Full Name", value: profile.name, key: "name", icon: User },
                  { label: "Age", value: profile.age, key: "age", icon: TrendingUp }, // Using TrendingUp for age as representative
                  { label: "Email Address", value: profile.email, key: "email", icon: Mail },
                  { label: "Phone Number", value: profile.phone, key: "phone", icon: Phone }
                ].map((field) => (
                  <div key={field.key} className="flex items-center gap-4 group">
                    <div className="w-10 h-10 bg-muted/50 rounded-xl flex items-center justify-center text-muted-foreground group-hover:scale-110 transition-transform">
                      <field.icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 border-b border-muted/50 pb-3">
                      <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{field.label}</Label>
                      {isEditing ? (
                        <Input
                          value={field.value}
                          onChange={(e) => setProfile({ ...profile, [field.key]: e.target.value })}
                          className="h-8 border-none bg-transparent p-0 text-sm font-bold focus-visible:ring-0"
                        />
                      ) : (
                        <p className="text-sm font-bold">{field.value || "Not Provided"}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </section>

        {/* Logout Button - Positioned above nav bar area */}
        <div className="pt-4">
          <Button
            onClick={logout}
            variant="ghost"
            className="w-full h-14 rounded-2xl text-destructive hover:bg-destructive/5 font-black flex items-center justify-between px-6 border border-destructive/10 bg-background shadow-sm"
          >
            <div className="flex items-center gap-4">
              <div className="w-9 h-9 bg-destructive/10 rounded-xl flex items-center justify-center">
                <LogOut className="h-4 w-4" />
              </div>
              <span className="text-sm">Logout Session</span>
            </div>
            <ChevronRight className="h-4 w-4 opacity-40" />
          </Button>
        </div>

        {/* Version Info */}
        <div className="text-center opacity-40 pb-4">
          <div className="flex items-center justify-center gap-2 grayscale mb-1">
            <Image src="/croc_mascot.png" alt="Croc" width={14} height={14} />
            <p className="text-[9px] font-black uppercase tracking-[0.2em]">Croc Ride v1.2.4</p>
          </div>
          <p className="text-[7px] font-bold uppercase tracking-widest">© 2024 Croc Ride Inc.</p>
        </div>

      </main>
    </div>
  )
}
