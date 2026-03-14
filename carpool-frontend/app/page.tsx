"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Loader2, Search, MapPin, Clock, Menu, X, Plus } from "lucide-react"
import { useRole } from "@/lib/RoleContext"
import { RoleSwitcher } from "@/components/RoleSwitcher"
// Make sure this points to the new OpenMap file we created!
// import { OpenMap } from "@/components/GoogleMap"
import dynamic from "next/dynamic"
// import { Loader2 } from "lucide-react"

// Dynamically import the map and disable Server-Side Rendering (SSR)
const OpenMap = dynamic(
  () => import("@/components/GoogleMap").then((mod) => mod.OpenMap),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[300px] bg-muted rounded-2xl flex items-center justify-center border">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }
)

type Ride = {
  id: string
  source: string
  destination: string
  departure_time: string
  available_seats: number
  total_seats: number
  status: "ACTIVE" | "COMPLETED" | "CANCELLED"
}

export default function LandingPage() {
  const router = useRouter()
  const { role } = useRole()
  const [rides, setRides] = useState<Ride[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [debugError, setDebugError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [isMounted, setIsMounted] = useState(false)

  // Only run client-side logic after mount to prevent hydration errors
  useEffect(() => {
    setIsMounted(true)
  }, [])

  const fetchRides = async () => {
    setIsLoading(true)
    setDebugError(null)
    setSearched(true)

    try {
      const params = new URLSearchParams({
        lat: "22.3072",
        lng: "73.1812",
        radius_km: "50",
        role: "source"
      })

      const response = await fetch(`/api/rides/nearby?${params.toString()}`)

      if (response.ok) {
        const data = await response.json()
        setRides(data)
      } else {
        setDebugError("Could not load rides. Please try again.")
      }
    } catch (error) {
      setDebugError("Cannot connect to server.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchRides()
  }, [])

  const filteredRides = rides.filter((ride) =>
    ride.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ride.destination.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isMounted) return null

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Top Header */}
      <header className="sticky top-0 bg-background/80 backdrop-blur-md z-40 border-b">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative w-8 h-8">
              <Image src="/croc_mascot.png" alt="Croc" fill className="object-contain" />
            </div>
            <span className="font-bold text-lg hidden sm:inline">Croc Ride</span>
          </div>

          <RoleSwitcher />

          <button onClick={() => setMenuOpen(!menuOpen)} className="p-1 hover:bg-muted rounded-full">
            <Menu className="h-6 w-6" />
          </button>
        </div>
      </header>

      {/* Side Menu */}
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex justify-end" onClick={() => setMenuOpen(false)}>
          <div className="h-full w-4/5 max-w-sm bg-background shadow-2xl animate-in slide-in-from-right" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 flex justify-between items-center border-b">
              <div className="flex items-center gap-2">
                <Image src="/croc_mascot.png" alt="Croc" width={32} height={32} />
                <span className="font-bold text-xl">Croc Ride</span>
              </div>
              <button onClick={() => setMenuOpen(false)} className="p-2 hover:bg-muted rounded-full">
                <X className="h-6 w-6" />
              </button>
            </div>
            <nav className="p-6 space-y-4">
              <Link href="/rides" className="flex items-center p-3 rounded-xl hover:bg-muted transition-colors font-medium">Find Rides</Link>
              <Link href="/rides/create" className="flex items-center p-3 rounded-xl hover:bg-muted transition-colors font-medium">Offer a Ride</Link>
              <Link href="/dashboard" className="flex items-center p-3 rounded-xl hover:bg-muted transition-colors font-medium">Dashboard</Link>
              <div className="h-px bg-border my-6" />
              <Link href="/login" className="flex items-center p-3 rounded-xl hover:bg-muted transition-colors font-medium text-muted-foreground">Sign In</Link>
              <Link href="/signup" className="flex items-center justify-center p-4 rounded-xl bg-primary text-primary-foreground font-bold shadow-lg shadow-primary/20">Get Started</Link>
            </nav>
          </div>
        </div>
      )}

      {/* Map Section - Rapido Style */}
      <div className="relative h-[45vh] sm:h-[55vh] overflow-hidden">
        {/* REPLACED GOOGLE MAP WITH OPENMAP */}
        <OpenMap center={{ lat: 22.3072, lng: 73.1812 }} zoom={13} />

        {/* Floating Search Bar */}
        <div className="absolute top-4 left-4 right-4 z-10 sm:max-w-md sm:mx-auto">
          <Card className="shadow-2xl border-none bg-background/90 backdrop-blur-sm">
            <CardContent className="p-3">
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <Input
                    placeholder={role === "passenger" ? "Where to?" : "Start a ride..."}
                    className="pl-10 h-12 bg-transparent border-none focus-visible:ring-0 text-base"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                {role === "driver" && (
                  <Button size="icon" className="h-10 w-10 rounded-full" onClick={() => router.push('/rides/create')}>
                    <Plus className="h-6 w-6" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Content Section */}
      <section className="px-4 -mt-10 relative z-20">
        <div className="max-w-6xl mx-auto">
          {role === "passenger" ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Nearby Rides</h2>
                <Button variant="ghost" size="sm" onClick={fetchRides} className="text-primary hover:text-primary/80">Refresh</Button>
              </div>

              {debugError && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-xl text-sm font-medium text-center">
                  {debugError}
                </div>
              )}

              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3 bg-card rounded-3xl border shadow-sm">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground font-medium">Finding rides for you...</p>
                </div>
              ) : filteredRides.length === 0 ? (
                <Card className="p-8 text-center rounded-3xl border-dashed border-2 bg-muted/50">
                  <div className="w-16 h-16 bg-background rounded-full flex items-center justify-center mx-auto mb-4 border shadow-sm text-primary">
                    <MapPin className="w-8 h-8" />
                  </div>
                  <h3 className="font-bold text-lg">No rides in this area</h3>
                  <p className="text-muted-foreground text-sm mt-1 max-w-[240px] mx-auto">Try searching for a different location or check back later.</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredRides.map((ride) => (
                    <Card key={ride.id} className="rounded-3xl shadow-sm hover:shadow-md transition-shadow cursor-pointer border-none overflow-hidden" onClick={() => router.push('/login')}>
                      <CardHeader className="pb-3 bg-muted/30">
                        <div className="flex justify-between items-center bg-background/50 backdrop-blur-sm p-2 rounded-2xl">
                          <Badge variant="secondary" className="rounded-xl px-3 bg-primary/10 text-primary border-none">{ride.available_seats} seats free</Badge>
                          <span className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground">{ride.status}</span>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-4 pb-4">
                        <div className="space-y-3">
                          <div className="flex items-start gap-3">
                            <div className="flex flex-col items-center gap-1 mt-1">
                              <div className="w-2 h-2 rounded-full bg-primary" />
                              <div className="w-0.5 h-6 bg-border" />
                              <div className="w-2 h-2 rounded-full bg-destructive" />
                            </div>
                            <div className="flex-1 space-y-4">
                              <div className="text-sm font-semibold truncate leading-none">{ride.source}</div>
                              <div className="text-sm font-semibold truncate leading-none pt-1">{ride.destination}</div>
                            </div>
                          </div>

                          <div className="pt-2 flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                              <Clock className="h-4 w-4 text-primary" />
                              <span className="text-xs font-medium">
                                {new Date(ride.departure_time).toLocaleString("en-IN", {
                                  hour: "numeric",
                                  minute: "2-digit",
                                  day: "numeric",
                                  month: "short",
                                })}
                              </span>
                            </div>
                            <Button size="sm" className="rounded-xl px-6 font-bold">Book</Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-card rounded-3xl p-8 border shadow-sm text-center">
              <div className="w-20 h-20 bg-primary/10 rounded-3xl flex items-center justify-center mx-auto mb-6 text-primary rotate-3">
                <Plus className="w-10 h-10" />
              </div>
              <h2 className="text-2xl font-bold mb-3">Ready to Drive?</h2>
              <p className="text-muted-foreground mb-8 max-w-sm mx-auto">
                Help fellow commuters and save fuel costs. Create a ride on your regular route.
              </p>
              <Button size="lg" className="w-full sm:w-auto px-10 rounded-2xl text-lg h-14 font-bold shadow-xl shadow-primary/20" onClick={() => router.push('/rides/create')}>
                Create Ride Now
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Corridor Info */}
      <section className="py-12 px-4">
        <div className="max-w-6xl mx-auto grid grid-cols-2 gap-4">
          <Card className="bg-secondary/20 border-none rounded-3xl p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-secondary rounded-2xl flex items-center justify-center mb-3 shadow-md">
              <Badge className="bg-white text-secondary-foreground hover:bg-white border-none shadow-none">98%</Badge>
            </div>
            <h4 className="font-bold text-sm">Safe Rides</h4>
            <p className="text-[10px] text-muted-foreground">Verified identity</p>
          </Card>
          <Card className="bg-accent/30 border-none rounded-3xl p-6 flex flex-col items-center text-center">
            <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center mb-3 shadow-md">
              <Badge className="bg-white text-accent-foreground hover:bg-white border-none shadow-none">₹50+</Badge>
            </div>
            <h4 className="font-bold text-sm">Save Fuel</h4>
            <p className="text-[10px] text-muted-foreground">Split costs daily</p>
          </Card>
        </div>
      </section>
    </div>
  )
}