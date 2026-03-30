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
  CreditCard,
  Plus,
  Trash2,
  Car
} from "lucide-react"

export default function AccountPage() {
  const { user, isLoading, logout, getAuthHeaders } = useAuth()
  const router = useRouter()

  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    phone: "",
    age: "24" // Default mock age
  })

  const [vehicles, setVehicles] = useState<any[]>([])
  const [isAddingVehicle, setIsAddingVehicle] = useState(false)
  const [newVehicle, setNewVehicle] = useState({
    make: "",
    model: "",
    color: "",
    license_plate: "",
    type: "CAR"
  })
  const [isVehicleLoading, setIsVehicleLoading] = useState(false)
  const [vehicleError, setVehicleError] = useState<string | null>(null)

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

  useEffect(() => {
    if (user) {
      fetchVehicles()
    }
  }, [user])

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

  const fetchVehicles = async () => {
    try {
      const response = await fetch("/api/vehicles/me", {
        headers: getAuthHeaders(),
        credentials: "include",
      })
      if (response.ok) {
        const data = await response.json()
        setVehicles(data)
      }
    } catch (error) {
      console.error("Failed to fetch vehicles:", error)
    }
  }

  const validateLicensePlate = (plate: string) => {
    const normalized = plate.replace(/[^A-Z0-9]/gi, "").toUpperCase()
    const pattern = /^[A-Z]{2}[0-9]{2}[A-Z]{0,2}[0-9]{4}$/
    if (plate.length > 0 && !pattern.test(normalized)) {
      return "Invalid format (e.g. GJ06BS4147)"
    }
    return null
  }

  const handleAddVehicle = async (e: React.FormEvent) => {
    e.preventDefault()
    const error = validateLicensePlate(newVehicle.license_plate)
    if (error) {
      setVehicleError(error)
      return
    }

    setIsVehicleLoading(true)
    setVehicleError(null)
    try {
      const response = await fetch("/api/vehicles", {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify(newVehicle)
      })

      if (response.ok) {
        const added = await response.json()
        setVehicles([...vehicles, added])
        setIsAddingVehicle(false)
        setNewVehicle({ make: "", model: "", color: "", license_plate: "", type: "CAR" })
      }
    } catch (error) {
      console.error("Failed to add vehicle:", error)
    } finally {
      setIsVehicleLoading(false)
    }
  }

  const handleDeleteVehicle = async (id: string) => {
    try {
      const response = await fetch(`/api/vehicles/${id}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
        credentials: "include",
      })
      if (response.ok) {
        setVehicles(vehicles.filter((v) => v.id !== id))
      }
    } catch (error) {
      console.error("Failed to delete vehicle:", error)
    }
  }

  return (
    <div className="min-h-screen bg-muted/30 dark:bg-background pb-32">
      {/* Premium Header */}
      <header className="bg-background/80 backdrop-blur-xl border-b sticky top-0 z-50 px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="relative w-12 h-12">
              <Image
                src="/croc_mascot(y).png"
                alt="Croc"
                fill
                sizes="48px"
                className="object-contain"
              />
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
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-primary">
                    <div className="relative w-12 h-12">
                      <Image src="/croc_mascot(y).png" alt="Croc" fill sizes="48px" className="object-contain" />
                    </div>
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

        {/* Section 3: My Vehicles */}
        <section className="space-y-4">
          <div className="flex items-center justify-between px-2">
            <div>
              <h2 className="text-xl font-black tracking-tight">My Vehicles</h2>
              <p className="text-muted-foreground text-xs font-medium">Add vehicles to offer rides as a driver</p>
            </div>
            {!isAddingVehicle && (
              <Button onClick={() => setIsAddingVehicle(true)} variant="ghost" size="sm" className="h-8 rounded-full text-xs font-bold text-primary hover:bg-primary/5">
                <Plus className="h-3.5 w-3.5 mr-1" /> Add
              </Button>
            )}
          </div>

          {isAddingVehicle && (
            <Card className="rounded-[2rem] border-2 border-primary/20 shadow-sm bg-background p-6 animate-in zoom-in-95 duration-200">
              <form onSubmit={handleAddVehicle} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Make</Label>
                    <Input
                      placeholder="e.g. Maruti"
                      value={newVehicle.make}
                      onChange={(e) => setNewVehicle({ ...newVehicle, make: e.target.value })}
                      className="rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none"
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Model</Label>
                    <Input
                      placeholder="e.g. Swift"
                      value={newVehicle.model}
                      onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })}
                      className="rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none"
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Color</Label>
                    <Input
                      placeholder="e.g. White"
                      value={newVehicle.color}
                      onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })}
                      className="rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none"
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Number Plate</Label>
                    <Input
                      placeholder="GJ-06..."
                      value={newVehicle.license_plate}
                      onChange={(e) => {
                        setNewVehicle({ ...newVehicle, license_plate: e.target.value })
                        setVehicleError(validateLicensePlate(e.target.value))
                      }}
                      className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none uppercase ${vehicleError ? "border-destructive focus-visible:ring-destructive" : ""}`}
                      required
                    />
                    {vehicleError && <p className="text-[10px] font-bold text-destructive ml-1 animate-in fade-in slide-in-from-top-1">{vehicleError}</p>}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Vehicle Type</Label>
                  <div className="flex gap-4">
                    {["CAR", "BIKE"].map((type) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setNewVehicle({ ...newVehicle, type })}
                        className={`flex-1 h-10 rounded-xl text-xs font-bold transition-all border-2 ${newVehicle.type === type
                          ? "border-primary bg-primary/5 text-primary"
                          : "border-muted/30 text-muted-foreground hover:border-muted"
                          }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="ghost" className="flex-1 rounded-xl h-11 text-xs font-bold" onClick={() => setIsAddingVehicle(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" className="flex-1 rounded-xl h-11 text-xs font-bold" disabled={isVehicleLoading || !!vehicleError}>
                    {isVehicleLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Register Vehicle"}
                  </Button>
                </div>
              </form>
            </Card>
          )}

          <div className="grid gap-3">
            {vehicles.length === 0 && !isAddingVehicle ? (
              <div className="p-8 text-center rounded-[2rem] border border-dashed border-muted-foreground/20 bg-muted/5">
                <Car className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
                <p className="text-muted-foreground text-xs font-medium">No vehicles registered yet</p>
              </div>
            ) : (
              vehicles.map((v) => (
                <Card key={v.id} className="rounded-3xl border shadow-sm bg-background p-4 group hover:border-primary/30 transition-all">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-muted/30 rounded-2xl flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                      <Car className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-black tracking-tight">{v.make} {v.model}</p>
                        <Badge variant="secondary" className="bg-muted text-[8px] uppercase font-black px-1.5 py-0 h-4 rounded-md tracking-tighter opacity-70">
                          {v.type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground">
                        <span className="uppercase">{v.color}</span>
                        <span className="opacity-20">•</span>
                        <span className="uppercase tracking-widest">{v.license_plate}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 rounded-xl text-destructive/40 hover:bg-destructive/5 hover:text-destructive transition-colors group-hover:text-destructive"
                      onClick={() => handleDeleteVehicle(v.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
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
            <Image src="/croc_mascot(y).png" alt="Croc" width={14} height={14} />
            <p className="text-[9px] font-black uppercase tracking-[0.2em]">Croc Ride v1.2.4</p>
          </div>
          <p className="text-[7px] font-bold uppercase tracking-widest">© 2024 Croc Ride Inc.</p>
        </div>

      </main>
    </div>
  )
}
