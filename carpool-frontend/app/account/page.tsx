"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { useAuth } from "@/lib/AuthContext"
import { useRole } from "@/lib/RoleContext"
import { Card } from "@/components/ui/card"
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
  X,
  Award,
  TrendingUp,
  Wallet,
  ShieldCheck,
  Star,
  ChevronRight,
  Plus,
  Trash2,
  Car,
  Building2,
  AlertCircle,
  CheckCircle2,
  Landmark
} from "lucide-react"

type AnalyticsRole = "passenger" | "driver"

type PassengerAnalytics = {
  role: "passenger"
  window: "lifetime"
  stats: {
    total_bookings: number
    cancelled_bookings: number
    seats_booked: number
    total_spend_inr: number
  }
}

type DriverAnalytics = {
  role: "driver"
  window: "lifetime"
  stats: {
    rides_created: number
    rides_completed: number
    seats_shared: number
    gross_earnings_inr: number
  }
}

type PersonalAnalytics = PassengerAnalytics | DriverAnalytics

type StatCard = {
  label: string
  value: string
  icon: typeof Award
  color: string
  bg: string
}

type ProfileUserFields = {
  phone_number?: string | null
  age?: string | number | null
}

type Vehicle = {
  id: string
  make: string
  model: string
  color: string
  license_plate: string
  type: string
}

type PayoutAccount = {
  is_linked: boolean
  account_id: string | null
  account_status?: string
}

type PayoutForm = {
  legal_name: string
  email: string
  phone: string
  beneficiary_name: string
  account_number: string
  ifsc_code: string
}

export default function AccountPage() {
  const { user, isLoading, logout, getAuthHeaders } = useAuth()
  const { role } = useRole()
  const router = useRouter()

  const [isEditing, setIsEditing] = useState(false)
  const [profile, setProfile] = useState({
    name: "",
    email: "",
        phone: "",
        age: "24" // Default mock age
  })

  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [isAddingVehicle, setIsAddingVehicle] = useState(false)
  const [newVehicle, setNewVehicle] = useState<{
    make: string
    model: string
    color: string
    license_plate: string
    type: "CAR" | "BIKE"
  }>({
    make: "",
    model: "",
    color: "",
    license_plate: "",
    type: "CAR"
  })
  const [isVehicleLoading, setIsVehicleLoading] = useState(false)
  const [vehicleError, setVehicleError] = useState<string | null>(null)
  const [analytics, setAnalytics] = useState<PersonalAnalytics | null>(null)
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(false)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)

  // Payout account state
  const [payoutAccount, setPayoutAccount] = useState<PayoutAccount | null>(null)
  const [isPayoutLoading, setIsPayoutLoading] = useState(false)
  const [isAddingPayout, setIsAddingPayout] = useState(false)
  const [payoutError, setPayoutError] = useState<string | null>(null)
  const [payoutFieldErrors, setPayoutFieldErrors] = useState<Partial<PayoutForm>>({})
  const [payoutForm, setPayoutForm] = useState<PayoutForm>({
    legal_name: "",
    email: "",
    phone: "",
    beneficiary_name: "",
    account_number: "",
    ifsc_code: "",
  })

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login")
    } else if (user) {
      const profileUser = user as typeof user & ProfileUserFields
      setProfile({
        name: profileUser.name || "",
        email: profileUser.email || "",
        phone: profileUser.phone_number || "",
        age: profileUser.age ? String(profileUser.age) : "24"
      })
    }
  }, [user, isLoading, router])

  useEffect(() => {
    if (!user) return

    const fetchVehicles = async () => {
      try {
        const response = await fetch("/api/vehicles/me", {
          headers: getAuthHeaders(),
          credentials: "include",
        })
        if (response.ok) {
          const data = await response.json()
          setVehicles(data as Vehicle[])
        }
      } catch (error) {
        console.error("Failed to fetch vehicles:", error)
      }
    }

    fetchVehicles()
  }, [user, getAuthHeaders])

  useEffect(() => {
    if (!user || role !== "driver") return

    const fetchPayoutAccount = async () => {
      setIsPayoutLoading(true)
      try {
        const response = await fetch("/api/payments/payout-account", {
          headers: getAuthHeaders(),
          credentials: "include",
        })
        if (response.ok) {
          const data = await response.json()
          setPayoutAccount(data as PayoutAccount)
        }
      } catch (error) {
        console.error("Failed to fetch payout account:", error)
      } finally {
        setIsPayoutLoading(false)
      }
    }

    fetchPayoutAccount()
  }, [user, role, getAuthHeaders])

  useEffect(() => {
    if (!user) return

    let isActive = true

    const fetchAnalytics = async () => {
      setIsAnalyticsLoading(true)
      setAnalyticsError(null)
      setAnalytics(null)

      try {
        const response = await fetch(`/api/analytics/me?role=${role}`, {
          headers: getAuthHeaders(),
          credentials: "include",
        })

        if (!isActive) return

        if (response.ok) {
          const data = await response.json()
          setAnalytics(data)
        } else {
          setAnalyticsError("Could not load your analytics.")
        }
      } catch {
        if (isActive) {
          setAnalyticsError("Could not load your analytics.")
        }
      } finally {
        if (isActive) {
          setIsAnalyticsLoading(false)
        }
      }
    }

    fetchAnalytics()

    return () => {
      isActive = false
    }
  }, [user, role, getAuthHeaders])

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount)

  const getAnalyticsCards = (activeRole: AnalyticsRole, data: PersonalAnalytics | null): StatCard[] => {
    if (!data) {
      if (activeRole === "driver") {
        return [
          { label: "Rides Created", value: "...", icon: TrendingUp, color: "text-blue-500", bg: "bg-blue-500/10" },
          { label: "Rides Completed", value: "...", icon: Award, color: "text-primary", bg: "bg-primary/10" },
          { label: "Seats Shared", value: "...", icon: Star, color: "text-orange-500", bg: "bg-orange-500/10" },
          { label: "Gross Earnings", value: "...", icon: Wallet, color: "text-green-500", bg: "bg-green-500/10" },
        ]
      }

      return [
        { label: "Bookings", value: "...", icon: Award, color: "text-primary", bg: "bg-primary/10" },
        { label: "Cancelled", value: "...", icon: X, color: "text-red-500", bg: "bg-red-500/10" },
        { label: "Seats Booked", value: "...", icon: Star, color: "text-orange-500", bg: "bg-orange-500/10" },
        { label: "Total Spend", value: "...", icon: Wallet, color: "text-green-500", bg: "bg-green-500/10" },
      ]
    }

    if (data.role === "driver") {
      return [
        {
          label: "Rides Created",
          value: String(data.stats.rides_created),
          icon: TrendingUp,
          color: "text-blue-500",
          bg: "bg-blue-500/10",
        },
        {
          label: "Rides Completed",
          value: String(data.stats.rides_completed),
          icon: Award,
          color: "text-primary",
          bg: "bg-primary/10",
        },
        {
          label: "Seats Shared",
          value: String(data.stats.seats_shared),
          icon: Star,
          color: "text-orange-500",
          bg: "bg-orange-500/10",
        },
        {
          label: "Gross Earnings",
          value: formatCurrency(data.stats.gross_earnings_inr),
          icon: Wallet,
          color: "text-green-500",
          bg: "bg-green-500/10",
        },
      ]
    }

    return [
      {
        label: "Bookings",
        value: String(data.stats.total_bookings),
        icon: Award,
        color: "text-primary",
        bg: "bg-primary/10",
      },
      {
        label: "Cancelled",
        value: String(data.stats.cancelled_bookings),
        icon: X,
        color: "text-red-500",
        bg: "bg-red-500/10",
      },
      {
        label: "Seats Booked",
        value: String(data.stats.seats_booked),
        icon: Star,
        color: "text-orange-500",
        bg: "bg-orange-500/10",
      },
      {
        label: "Total Spend",
        value: formatCurrency(data.stats.total_spend_inr),
        icon: Wallet,
        color: "text-green-500",
        bg: "bg-green-500/10",
      },
    ]
  }

  const stats = getAnalyticsCards(role, analytics)

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

  // Per-field validators — return null if valid, string if invalid
  const validators = {
    legal_name: (v: string) =>
      v.trim().length < 2 ? "Name must be at least 2 characters" :
      /[^a-zA-Z\s'.\-]/.test(v) ? "Name must not contain numbers or special characters" : null,
    phone: (v: string) =>
      !/^\d{10}$/.test(v) ? "Enter a valid 10-digit Indian mobile number" : null,
    email: (v: string) =>
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? "Enter a valid email address" : null,
    beneficiary_name: (v: string) =>
      v.trim().length < 2 ? "Account holder name must be at least 2 characters" :
      /[^a-zA-Z\s'.\-]/.test(v) ? "Name must not contain numbers or special characters" : null,
    account_number: (v: string) =>
      !/^\d{9,18}$/.test(v) ? `Account number must be 9–18 digits (you entered ${v.length})` : null,
    ifsc_code: (v: string) =>
      v.length < 11 ? `IFSC must be exactly 11 characters (you entered ${v.length})` :
      !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(v) ? "Invalid IFSC format — e.g. HDFC0001234 (4 letters, 0, 6 alphanumeric)" : null,
  }

  const validatePayoutField = (field: keyof PayoutForm, value: string) => {
    const err = validators[field]?.(value) ?? null
    setPayoutFieldErrors(prev => ({ ...prev, [field]: err }))
    return err
  }

  const hasPayoutFieldErrors = () =>
    Object.values(payoutFieldErrors).some(Boolean)

  const handleSetupPayout = async (e: React.FormEvent) => {
    e.preventDefault()
    setPayoutError(null)
    // Run all validations before submit
    const errs: Partial<PayoutForm> = {}
    let hasErr = false
    for (const key of Object.keys(validators) as (keyof PayoutForm)[]) {
      const err = validators[key](payoutForm[key])
      if (err) { errs[key] = err; hasErr = true }
    }
    if (hasErr) { setPayoutFieldErrors(errs); return }

    setIsPayoutLoading(true)
    try {
      const response = await fetch("/api/payments/payout-account", {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          ...payoutForm,
          legal_name: payoutForm.legal_name.trim(),
          beneficiary_name: payoutForm.beneficiary_name.trim(),
          ifsc_code: payoutForm.ifsc_code.toUpperCase(),
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        // Surface specific backend error
        setPayoutError(data.detail || "Failed to link account. Check your details and try again.")
        return
      }
      setPayoutAccount({ is_linked: true, account_id: data.account_id, account_status: "created" })
      setIsAddingPayout(false)
      setPayoutFieldErrors({})
      setPayoutForm({ legal_name: "", email: "", phone: "", beneficiary_name: "", account_number: "", ifsc_code: "" })
    } catch {
      setPayoutError("Network error — could not reach the server. Please check your connection and try again.")
    } finally {
      setIsPayoutLoading(false)
    }
  }

  const handleRemovePayoutAccount = async () => {
    setIsPayoutLoading(true)
    setPayoutError(null)
    try {
      const response = await fetch("/api/payments/payout-account", {
        method: "DELETE",
        headers: getAuthHeaders(),
        credentials: "include",
      })
      if (response.ok) {
        setPayoutAccount({ is_linked: false, account_id: null })
      }
    } catch {
      setPayoutError("Failed to remove account.")
    } finally {
      setIsPayoutLoading(false)
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
          {analyticsError ? (
            <Card className="rounded-[2rem] border border-destructive/20 bg-destructive/5 p-5">
              <p className="text-sm font-bold text-destructive">{analyticsError}</p>
            </Card>
          ) : (
          <div className="grid grid-cols-2 gap-4">
            {stats.map((stat, i) => (
              <Card key={i} className="rounded-3xl border-none shadow-sm bg-background p-5 hover:shadow-md transition-shadow">
                <div className="flex flex-col gap-3">
                  <div className={`${stat.bg} ${stat.color} w-9 h-9 rounded-xl flex items-center justify-center`}>
                    <stat.icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none mb-1">{stat.label}</p>
                    <div className="flex items-center gap-2">
                      <p className={`text-xl font-black ${stat.color} tracking-tighter`}>{stat.value}</p>
                      {isAnalyticsLoading && (
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
          )}
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
                          readOnly={field.key === "email"}
                          onChange={(e) => setProfile({ ...profile, [field.key]: e.target.value })}
                          className={`h-8 border-none bg-transparent p-0 text-sm font-bold focus-visible:ring-0 ${field.key === "email" ? "text-muted-foreground/50 cursor-not-allowed" : ""}`}
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
                    {(["CAR", "BIKE"] as const).map((type) => (
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

        {/* Section 4: Payout Settings — drivers only */}
        {role === "driver" && (
          <section className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <div>
                <h2 className="text-xl font-black tracking-tight">Payout Settings</h2>
                <p className="text-muted-foreground text-xs font-medium">Your bank account for ride earnings</p>
              </div>
              {!isAddingPayout && !payoutAccount?.is_linked && (
                <Button
                  onClick={() => {
                    setPayoutForm({ legal_name: profile.name, email: profile.email, phone: profile.phone, beneficiary_name: profile.name, account_number: "", ifsc_code: "" })
                    setIsAddingPayout(true)
                    setPayoutError(null)
                  }}
                  variant="ghost"
                  size="sm"
                  className="h-8 rounded-full text-xs font-bold text-primary hover:bg-primary/5"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" /> Set Up
                </Button>
              )}
            </div>

            {/* Linked State */}
            {payoutAccount?.is_linked && (
              <Card className="rounded-[2rem] border-none shadow-sm bg-background overflow-hidden">
                <div className="p-6 space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-green-500/10 flex items-center justify-center">
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-black tracking-tight">Bank Account Linked</p>
                        <Badge variant="secondary" className="bg-green-500/10 text-green-600 border-none font-bold px-2 py-0 rounded-full text-[9px] uppercase tracking-wider">
                          {payoutAccount.account_status === "activated" ? "Active" : "Pending Verification"}
                        </Badge>
                      </div>
                      <p className="text-[11px] font-bold text-muted-foreground font-mono mt-0.5">
                        {payoutAccount.account_id}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleRemovePayoutAccount}
                      disabled={isPayoutLoading}
                      className="h-8 rounded-xl text-[10px] font-bold text-destructive/60 hover:text-destructive hover:bg-destructive/5"
                    >
                      {isPayoutLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Remove"}
                    </Button>
                  </div>
                  <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3">
                    <p className="text-[10px] font-bold text-amber-600">
                      Razorpay will verify your bank account via penny drop (₹1 transfer). This may take a few minutes.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Not linked state */}
            {!payoutAccount?.is_linked && !isAddingPayout && (
              <Card className="rounded-[2rem] border border-dashed border-muted-foreground/20 bg-muted/5">
                <div className="p-8 text-center">
                  {isPayoutLoading ? (
                    <Loader2 className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3 animate-spin" />
                  ) : (
                    <>
                      <Landmark className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
                      <p className="text-muted-foreground text-xs font-medium">No payout account linked</p>
                      <p className="text-muted-foreground/60 text-[10px] font-medium mt-1">Required to create rides and receive earnings</p>
                    </>
                  )}
                </div>
              </Card>
            )}

            {/* Add payout account form */}
            {isAddingPayout && (
              <Card className="rounded-[2rem] border-2 border-primary/20 shadow-sm bg-background p-6 animate-in zoom-in-95 duration-200">
                <form onSubmit={handleSetupPayout} className="space-y-5">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                      <Building2 className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-black">Link Bank Account</p>
                      <p className="text-[10px] text-muted-foreground font-medium">Verified via Razorpay Route — your earnings are secure</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Legal Name</Label>
                      <Input
                        id="payout-legal-name"
                        placeholder="As on PAN card"
                        value={payoutForm.legal_name}
                        onChange={(e) => {
                          const v = e.target.value.replace(/[^a-zA-Z\s'.\-]/g, "")
                          setPayoutForm({ ...payoutForm, legal_name: v })
                          validatePayoutField("legal_name", v)
                        }}
                        className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none ${payoutFieldErrors.legal_name ? "border-destructive" : ""}`}
                        maxLength={100}
                        required
                      />
                      {payoutFieldErrors.legal_name && <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.legal_name}</p>}
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Phone</Label>
                      <Input
                        id="payout-phone"
                        placeholder="10-digit mobile"
                        value={payoutForm.phone}
                        inputMode="numeric"
                        onChange={(e) => {
                          const v = e.target.value.replace(/\D/g, "").slice(0, 10)
                          setPayoutForm({ ...payoutForm, phone: v })
                          validatePayoutField("phone", v)
                        }}
                        className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none ${payoutFieldErrors.phone ? "border-destructive" : ""}`}
                        maxLength={10}
                        required
                      />
                      {payoutFieldErrors.phone && <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.phone}</p>}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Email for Razorpay</Label>
                    <Input
                      id="payout-email"
                      type="email"
                      placeholder="your@email.com"
                      value={payoutForm.email}
                      onChange={(e) => {
                        setPayoutForm({ ...payoutForm, email: e.target.value })
                        validatePayoutField("email", e.target.value)
                      }}
                      className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none ${payoutFieldErrors.email ? "border-destructive" : ""}`}
                      maxLength={255}
                      required
                    />
                    {payoutFieldErrors.email && <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.email}</p>}
                  </div>

                  <div className="border-t border-muted/30 pt-4 space-y-3">
                    <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest px-1">Bank Details</p>
                    <div className="space-y-1">
                      <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Account Holder Name</Label>
                      <Input
                        id="payout-beneficiary-name"
                        placeholder="Exactly as on your bank passbook"
                        value={payoutForm.beneficiary_name}
                        onChange={(e) => {
                          const v = e.target.value.replace(/[^a-zA-Z\s'.\-]/g, "")
                          setPayoutForm({ ...payoutForm, beneficiary_name: v })
                          validatePayoutField("beneficiary_name", v)
                        }}
                        className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none ${payoutFieldErrors.beneficiary_name ? "border-destructive" : ""}`}
                        maxLength={100}
                        required
                      />
                      {payoutFieldErrors.beneficiary_name && <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.beneficiary_name}</p>}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">Account Number</Label>
                        <Input
                          id="payout-account-number"
                          placeholder="9–18 digits"
                          value={payoutForm.account_number}
                          inputMode="numeric"
                          onChange={(e) => {
                            const v = e.target.value.replace(/\D/g, "").slice(0, 18)
                            setPayoutForm({ ...payoutForm, account_number: v })
                            validatePayoutField("account_number", v)
                          }}
                          className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none ${payoutFieldErrors.account_number ? "border-destructive" : ""}`}
                          maxLength={18}
                          required
                        />
                        {payoutFieldErrors.account_number
                          ? <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.account_number}</p>
                          : <p className="text-[9px] text-muted-foreground ml-1">{payoutForm.account_number.length}/18 digits used</p>
                        }
                      </div>
                      <div className="space-y-1">
                        <Label className="text-[10px] font-black text-muted-foreground uppercase tracking-widest ml-1">IFSC Code</Label>
                        <Input
                          id="payout-ifsc"
                          placeholder="HDFC0001234"
                          value={payoutForm.ifsc_code}
                          onChange={(e) => {
                            const val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 11)
                            setPayoutForm({ ...payoutForm, ifsc_code: val })
                            validatePayoutField("ifsc_code", val)
                          }}
                          className={`rounded-xl h-10 border-muted/30 focus-visible:ring-primary shadow-none uppercase ${payoutFieldErrors.ifsc_code ? "border-destructive" : ""}`}
                          maxLength={11}
                          required
                        />
                        {payoutFieldErrors.ifsc_code
                          ? <p className="text-[9px] text-destructive font-bold ml-1">{payoutFieldErrors.ifsc_code}</p>
                          : <p className="text-[9px] text-muted-foreground ml-1">{payoutForm.ifsc_code.length}/11 characters</p>
                        }
                      </div>
                    </div>
                  </div>

                  {/* API-level error (from backend / network) */}
                  {payoutError && (
                    <div className="flex items-start gap-2 bg-destructive/5 border border-destructive/10 rounded-xl p-3">
                      <AlertCircle className="h-3.5 w-3.5 text-destructive flex-shrink-0 mt-0.5" />
                      <p className="text-[10px] font-bold text-destructive">{payoutError}</p>
                    </div>
                  )}

                  <div className="flex gap-3 pt-1">
                    <Button
                      type="button"
                      variant="ghost"
                      className="flex-1 rounded-xl h-11 text-xs font-bold"
                      onClick={() => { setIsAddingPayout(false); setPayoutError(null); setPayoutFieldErrors({}) }}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      className="flex-1 rounded-xl h-11 text-xs font-bold"
                      disabled={isPayoutLoading || hasPayoutFieldErrors()}
                    >
                      {isPayoutLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Link Bank Account"}
                    </Button>
                  </div>
                </form>
              </Card>
            )}
          </section>
        )}

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
