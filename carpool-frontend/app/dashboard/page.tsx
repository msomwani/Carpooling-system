"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Loader2, Users, Calendar, Search, Plus, AlertTriangle, Menu, X, Home, Car as CarIcon, User, BookOpen } from "lucide-react"
import Image from "next/image"

type Ride = {
  id: string
  source: string
  destination: string
  departure_time: string
  available_seats: number
  total_seats: number
  status: "ACTIVE" | "COMPLETED" | "CANCELLED"
}

type UserRole = "passenger" | "driver"

export default function DashboardPage() {
  const [rides, setRides] = useState<Ride[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [source, setSource] = useState("")
  const [destination, setDestination] = useState("")
  const [debugError, setDebugError] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<UserRole>("passenger")
  const [bookingRide, setBookingRide] = useState<string | null>(null)
  const [bookingSeats, setBookingSeats] = useState(1)
  const [bookingError, setBookingError] = useState<string | null>(null)

  const fetchRides = async () => {
    setIsLoading(true)
    setDebugError(null)
    
    try {
      const params = new URLSearchParams({
        lat: "22.3072",
        lng: "73.1812",
        radius_km: "50",
        source: source,
        destination: destination
      })

      const response = await fetch(`/api/rides/nearby?${params.toString()}`)
      
      if (response.ok) {
        const data = await response.json()
        setRides(data)
      } else {
        setDebugError("Could not load nearby rides from the backend.")
      }
    } catch (error) {
      setDebugError("Cannot connect to backend container.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    const savedRole = localStorage.getItem("userRole") as UserRole
    if (savedRole) {
      setUserRole(savedRole)
    }
    
    // Check for query params if coming from Home page search or deep link
    const urlParams = new URLSearchParams(window.location.search)
    const qSource = urlParams.get('source')
    const qDest = urlParams.get('destination')
    if (qSource) setSource(qSource)
    if (qDest) setDestination(qDest)
    
    if (qSource || qDest) {
        fetchRides()
    } else {
        // Initial fetch if no params (optional, can keep empty until search)
        fetchRides()
    }
  }, [])

  const toggleRole = (role: UserRole) => {
    setUserRole(role)
    localStorage.setItem("userRole", role)
  }

  const handleBook = async (rideId: string) => {
    setBookingRide(rideId)
    setBookingError(null)
  }

  const confirmBooking = async (rideId: string) => {
    setBookingError(null)
    try {
      const response = await fetch("/api/bookings/", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Idempotency-Key": `${rideId}-${Date.now()}`
        },
        body: JSON.stringify({
          ride_id: rideId,
          seats: bookingSeats
        })
      })

      if (response.ok) {
        alert("Booking confirmed!")
        setBookingRide(null)
        fetchRides()
      } else {
        const data = await response.json()
        setBookingError(data.detail || "Booking failed")
      }
    } catch (error) {
      setBookingError("Failed to book. Make sure you're logged in.")
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      {/* Top Bar - Clean & Modern */}
      <header className="bg-background border-b sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="relative w-8 h-8">
                <Image src="/croc_mascot.png" alt="Croc" fill className="object-contain" />
              </div>
            </Link>
            <span className="font-bold text-lg">Croc Ride</span>
          </div>
          
          <div className="flex items-center gap-4">
             <div className="flex items-center gap-1 bg-muted rounded-full p-1">
              <button
                onClick={() => toggleRole("passenger")}
                className={`flex items-center gap-1 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  userRole === "passenger" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Passenger
              </button>
              <button
                onClick={() => toggleRole("driver")}
                className={`flex items-center gap-1 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  userRole === "driver" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Driver
              </button>
            </div>
            <Link href="/account">
               <Button variant="ghost" size="icon" className="rounded-full">
                 <User className="h-5 w-5" />
               </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto p-4 space-y-6 pt-8">
        
        {/* Search Point Section - Zomato Style */}
        <section className="space-y-4">
          <div className="bg-background rounded-3xl p-6 shadow-xl border-none space-y-4">
            <h1 className="text-2xl font-black tracking-tight mb-2">Find your ride</h1>
            
            <div className="space-y-2">
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-primary" />
                <Input 
                  placeholder="Leaving from..." 
                  className="pl-10 h-14 rounded-2xl bg-muted/30 border-none text-base font-medium focus-visible:ring-primary"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                />
              </div>
              
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-destructive" />
                <Input 
                  placeholder="Going to..." 
                  className="pl-10 h-14 rounded-2xl bg-muted/30 border-none text-base font-medium focus-visible:ring-primary"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                />
              </div>
            </div>
            
            <Button 
                onClick={fetchRides} 
                className="w-full h-14 rounded-2xl text-lg font-black shadow-lg shadow-primary/20 bg-primary hover:bg-primary/90 transition-all active:scale-95"
                disabled={isLoading}
            >
              {isLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : "Search Rides"}
            </Button>
          </div>
        </section>

        {/* Results Section */}
        <section className="space-y-4 pb-24">
            {debugError && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-2xl text-sm font-medium flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    {debugError}
                </div>
            )}

            {isLoading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                    <Loader2 className="h-10 w-10 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground font-bold animate-pulse">Scanning routes...</p>
                </div>
            ) : rides.length === 0 ? (
                <div className="py-20 text-center space-y-3 opacity-60">
                    <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mx-auto">
                        <Search className="h-10 w-10" />
                    </div>
                    <p className="font-bold text-muted-foreground">No rides matched your search</p>
                    <p className="text-xs">Try different locations or broaden your search.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="flex items-center justify-between px-2">
                        <h2 className="text-sm font-black uppercase tracking-widest text-muted-foreground/60">Available Rides</h2>
                        <Badge variant="secondary" className="rounded-full px-3">{rides.length} Found</Badge>
                    </div>
                    
                    <div className="grid grid-cols-1 gap-4">
                        {rides.map((ride) => (
                            <Card key={ride.id} className="rounded-3xl border-none shadow-md overflow-hidden bg-background hover:shadow-lg transition-all group">
                                <CardHeader className="pb-3 bg-muted/10">
                                    <div className="flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                                <CarIcon className="h-4 w-4 text-primary" />
                                            </div>
                                            <span className="text-xs font-bold">Standard Trip</span>
                                        </div>
                                        <Badge className="bg-green-500/10 text-green-600 hover:bg-green-500/20 border-none font-black px-3 rounded-full uppercase text-[10px]">
                                            {ride.status}
                                        </Badge>
                                    </div>
                                </CardHeader>
                                <CardContent className="pt-4">
                                    <div className="flex items-start gap-4">
                                        <div className="flex flex-col items-center gap-1 mt-1">
                                            <div className="w-2 h-2 rounded-full bg-primary" />
                                            <div className="w-0.5 h-8 bg-muted-foreground/20" />
                                            <div className="w-2 h-2 rounded-full bg-destructive" />
                                        </div>
                                        <div className="flex-1 space-y-6">
                                            <div>
                                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1">Pick up</p>
                                                <p className="font-bold text-sm leading-tight">{ride.source}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-1">Drop off</p>
                                                <p className="font-bold text-sm leading-tight">{ride.destination}</p>
                                            </div>
                                        </div>
                                        <div className="text-right flex flex-col items-end justify-between self-stretch">
                                            <div className="bg-primary/5 p-2 rounded-2xl text-center min-w-[60px]">
                                                <p className="text-[9px] font-black text-muted-foreground uppercase mb-1">Price</p>
                                                <p className="text-base font-black text-primary">₹149</p>
                                            </div>
                                            <div className="flex items-center gap-1 text-muted-foreground">
                                                <Users className="h-3 w-3" />
                                                <span className="text-xs font-bold">{ride.available_seats} left</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="mt-6 flex items-center justify-between pt-4 border-t">
                                        <div className="flex items-center gap-2">
                                            <Calendar className="h-4 w-4 text-primary" />
                                            <span className="text-sm font-bold">
                                                {new Date(ride.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        {userRole === "passenger" ? (
                                            bookingRide === ride.id ? (
                                              <div className="flex gap-2">
                                                <Input 
                                                  type="number" 
                                                  min={1} 
                                                  max={ride.available_seats}
                                                  value={bookingSeats}
                                                  onChange={(e) => setBookingSeats(Number(e.target.value))}
                                                  className="w-14 h-9 rounded-xl text-center font-bold"
                                                />
                                                <Button size="sm" className="rounded-xl font-bold px-4" onClick={() => confirmBooking(ride.id)}>Confirm</Button>
                                                <Button size="sm" variant="ghost" className="rounded-xl font-bold" onClick={() => setBookingRide(null)}>X</Button>
                                              </div>
                                            ) : (
                                              <Button 
                                                className="rounded-2xl font-black px-8 py-5 text-sm shadow-md hover:shadow-lg transition-all" 
                                                onClick={() => handleBook(ride.id)}
                                                disabled={ride.available_seats < 1}
                                              >
                                                Book Seat
                                              </Button>
                                            )
                                        ) : (
                                            <span className="text-xs font-bold text-muted-foreground italic bg-muted px-4 py-2 rounded-full">Your Ride</span>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </div>
            )}
        </section>
      </main>
    </div>
  )
}
