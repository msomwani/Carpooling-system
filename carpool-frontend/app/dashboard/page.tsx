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
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [debugError, setDebugError] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<UserRole>("passenger")
  const [bookingRide, setBookingRide] = useState<string | null>(null)
  const [bookingSeats, setBookingSeats] = useState(1)
  const [bookingError, setBookingError] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  const fetchRides = async () => {
    setIsLoading(true)
    setDebugError(null)
    
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
        const errorData = await response.json().catch(() => null)
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
    fetchRides()
  }, [])

  const toggleRole = (role: UserRole) => {
    setUserRole(role)
    localStorage.setItem("userRole", role)
    setMenuOpen(false)
  }

  const filteredRides = rides.filter((ride) => 
    ride.source.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ride.destination.toLowerCase().includes(searchTerm.toLowerCase())
  )

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

  const handleLogout = () => {
    localStorage.clear()
    window.location.href = '/'
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Top Bar */}
      <header className="border-b sticky top-0 bg-background z-40">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="relative w-8 h-8">
                <Image 
                  src="/croc_mascot.png" 
                  alt="Croc" 
                  fill
                  className="object-contain"
                />
              </div>
            </Link>
            <Link href="/">
              <span className="font-bold text-lg">Croc Ride</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden md:flex items-center gap-1 bg-muted rounded-full p-1">
              <button
                onClick={() => toggleRole("passenger")}
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition ${
                  userRole === "passenger" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                <User className="h-3 w-3" /> Passenger
              </button>
              <button
                onClick={() => toggleRole("driver")}
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition ${
                  userRole === "driver" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                <CarIcon className="h-3 w-3" /> Driver
              </button>
            </div>
            <button onClick={() => setMenuOpen(!menuOpen)} className="p-2">
              <Menu className="h-6 w-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Side Menu */}
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setMenuOpen(false)}>
          <div className="absolute right-0 top-0 h-full w-64 bg-background shadow-lg" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 flex justify-between items-center border-b">
              <span className="font-semibold">Account</span>
              <button onClick={() => setMenuOpen(false)}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-4 border-b">
              <div className="flex items-center gap-2 mb-3">
                <span className="font-medium">Mode:</span>
              </div>
              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant={userRole === "passenger" ? "default" : "outline"}
                  onClick={() => toggleRole("passenger")}
                >
                  Passenger
                </Button>
                <Button 
                  size="sm" 
                  variant={userRole === "driver" ? "default" : "outline"}
                  onClick={() => toggleRole("driver")}
                >
                  Driver
                </Button>
              </div>
            </div>
            <nav className="p-4 space-y-2">
              <Link href="/" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Home
              </Link>
              <Link href="/rides" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Find Rides
              </Link>
              <Link href="/rides/create" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Offer a Ride
              </Link>
              <Link href="/bookings" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                My Bookings
              </Link>
              <Link href="/analytics" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Analytics
              </Link>
              <hr className="my-4" />
              <button className="block w-full text-left p-3 rounded-lg hover:bg-muted" onClick={handleLogout}>
                Sign Out
              </button>
            </nav>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto p-6 pb-24">
        <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">
              {userRole === "driver" ? "Driver Dashboard" : "Dashboard"}
            </h1>
            <p className="text-muted-foreground text-sm">
              {userRole === "driver" ? "Manage your rides" : "Find rides and bookings"}
            </p>
          </div>
          
          <div className="flex items-center gap-2 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search..." 
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            {userRole === "driver" && (
              <Link href="/rides/create">
                <Button>
                  <Plus className="mr-2 h-4 w-4" /> Offer Ride
                </Button>
              </Link>
            )}
          </div>
        </div>

        {debugError && (
          <div className="mb-4 p-3 border border-destructive rounded-lg flex items-center gap-2 text-sm">
            <AlertTriangle className="h-4 w-4" />
            {debugError}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-2">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        ) : filteredRides.length === 0 ? (
          <Card className="p-8 text-center">
            <h3 className="font-semibold">No rides found</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {userRole === "driver" ? "Create your first ride!" : "No rides in your area."}
            </p>
            {userRole === "driver" ? (
              <Link href="/rides/create">
                <Button className="mt-4">Offer a Ride</Button>
              </Link>
            ) : (
              <Button className="mt-4" variant="outline" onClick={fetchRides}>Refresh</Button>
            )}
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredRides.map((ride) => (
              <Card key={ride.id}>
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-center">
                    <Badge variant="secondary" className="text-xs">{ride.status}</Badge>
                    <span className="text-xs">{ride.total_seats} seats</span>
                  </div>
                  <CardTitle className="text-sm font-bold flex flex-col gap-1 mt-2">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                      {ride.source}
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full bg-destructive" />
                      {ride.destination}
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground pb-2">
                  <div className="flex items-center justify-between border-t pt-2">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {new Date(ride.departure_time).toLocaleString("en-IN", {
                        day: "numeric",
                        month: "short",
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </div>
                    <div className="flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      {ride.available_seats}
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="pt-0">
                  {userRole === "passenger" ? (
                    bookingRide === ride.id ? (
                      <div className="w-full space-y-2">
                        {bookingError && <p className="text-xs text-destructive">{bookingError}</p>}
                        <div className="flex gap-2">
                          <Input 
                            type="number" 
                            min={1} 
                            max={ride.available_seats}
                            value={bookingSeats}
                            onChange={(e) => setBookingSeats(Number(e.target.value))}
                            className="w-16 h-8"
                          />
                          <Button size="sm" onClick={() => confirmBooking(ride.id)}>Confirm</Button>
                          <Button size="sm" variant="outline" onClick={() => setBookingRide(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <Button 
                        className="w-full text-xs" 
                        size="sm"
                        onClick={() => handleBook(ride.id)}
                        disabled={ride.available_seats < 1}
                      >
                        {ride.available_seats > 0 ? "Book" : "Full"}
                      </Button>
                    )
                  ) : (
                    <div className="w-full text-center text-xs text-muted-foreground">
                      Your ride
                    </div>
                  )}
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Navigation for Mobile */}
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t md:hidden">
        <div className="flex justify-around items-center h-16">
          <Link href="/" className="flex flex-col items-center gap-1 p-2">
            <Home className="h-5 w-5" />
            <span className="text-xs">Home</span>
          </Link>
          <Link href="/rides" className="flex flex-col items-center gap-1 p-2">
            <CarIcon className="h-5 w-5" />
            <span className="text-xs">Rides</span>
          </Link>
          <Link href="/bookings" className="flex flex-col items-center gap-1 p-2">
            <BookOpen className="h-5 w-5" />
            <span className="text-xs">Bookings</span>
          </Link>
          <button onClick={() => setMenuOpen(true)} className="flex flex-col items-center gap-1 p-2">
            <User className="h-5 w-5" />
            <span className="text-xs">Account</span>
          </button>
        </div>
      </div>
    </div>
  )
}
