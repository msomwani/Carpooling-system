"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Calendar, MapPin, X, History, User, Car, Clock, ChevronRight, RefreshCw } from "lucide-react"
import { useRole } from "@/lib/RoleContext"
import { useAuth } from "@/lib/AuthContext"
import { RoleSwitcher } from "@/components/RoleSwitcher"

type BookingHistoryItem = {
  event_id: string
  booking_id: string
  ride_id: string
  action: string
  occurred_at: string
  correlation_id: string | null
}

type DriverRide = {
  id: string
  source: string
  destination: string
  departure_time: string
  available_seats: number
  price_per_seat: number
  total_seats: number
  status: "ACTIVE" | "COMPLETED" | "CANCELLED"
  source_lat: number
  source_lng: number
  destination_lat: number
  destination_lng: number
  vehicle_id: string | null
}

export default function BookingsPage() {
  const { role } = useRole()
  const { getAuthHeaders } = useAuth()
  const [bookings, setBookings] = useState<BookingHistoryItem[]>([])
  const [driverRides, setDriverRides] = useState<DriverRide[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isUnauthorized, setIsUnauthorized] = useState(false)
  const [cancelling, setCancelling] = useState<string | null>(null)
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
  }, [])

  const fetchPassengerData = async () => {
    setIsLoading(true)
    setError(null)
    setIsUnauthorized(false)
    try {
      const response = await fetch("/api/bookings/history", {
        headers: getAuthHeaders(),
      })
      if (response.ok) {
        const data = await response.json()
        setBookings(data)
      } else if (response.status === 401) {
        setIsUnauthorized(true)
      } else {
        setError("Could not load your booking history.")
      }
    } catch (error) {
      setError("Cannot connect to server.")
    } finally {
      setIsLoading(false)
    }
  }

  const fetchDriverData = async () => {
    setIsLoading(true)
    setError(null)
    setIsUnauthorized(false)
    try {
      const response = await fetch("/api/rides/me", {
        headers: getAuthHeaders(),
      })
      if (response.ok) {
        const data = await response.json()
        setDriverRides(data)
      } else if (response.status === 401) {
        setIsUnauthorized(true)
      } else {
        setError("Could not load your offered rides.")
      }
    } catch (error) {
      setError("Cannot connect to server.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (role === "passenger") {
      fetchPassengerData()
    } else {
      fetchDriverData()
    }
  }, [role])

  const handleCancelBooking = async (bookingId: string) => {
    if (!confirm("Are you sure you want to cancel this booking?")) return
    setCancelling(bookingId)
    try {
      const response = await fetch(`/api/bookings/${bookingId}/cancel`, {
        method: "POST",
        headers: getAuthHeaders(),
      })
      if (response.ok) fetchPassengerData()
    } catch (error) {
      alert("Failed to cancel booking")
    } finally {
      setCancelling(null)
    }
  }

  const getBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED":
      case "ACTIVE":
        return <Badge className="bg-green-500 rounded-lg">Active</Badge>
      case "COMPLETED":
        return <Badge className="bg-blue-500 rounded-lg">Done</Badge>
      case "CANCELLED":
        return <Badge variant="destructive" className="rounded-lg">Cancelled</Badge>
      default:
        return <Badge variant="secondary" className="rounded-lg">{status}</Badge>
    }
  }

  if (!isMounted) return null

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="sticky top-0 bg-background/80 backdrop-blur-md z-40 border-b">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="relative w-12 h-12">
              <Image
                src="/croc_mascot(y).png"
                alt="Croc"
                fill
                sizes="48px"
                className="object-contain"
              />
            </div>
            <span className="font-bold text-lg hidden sm:inline">Croc Ride</span>
          </Link>
          <RoleSwitcher />
          <div className="w-8" /> {/* Spacer */}
        </div>
      </header>

      <div className="max-w-xl mx-auto p-4">
        <div className="mb-6 mt-2">
          <h1 className="text-2xl font-bold">{role === "passenger" ? "My Bookings" : "My Offered Rides"}</h1>
          <p className="text-muted-foreground text-sm">
            {role === "passenger" ? "Rides you've booked as a passenger" : "Rides you're sharing as a driver"}
          </p>
        </div>

        {isUnauthorized && role === "passenger" ? (
          <Card className="p-10 text-center rounded-3xl border shadow-lg bg-orange-50/10 border-orange-200/50">
            <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4 text-orange-600">
              <User className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-bold">Sign in required</h3>
            <p className="text-muted-foreground text-sm mt-1">Please sign in to view your bookings history.</p>
            <Link href="/login">
              <Button className="mt-6 rounded-xl px-8 font-bold bg-orange-600 hover:bg-orange-700 shadow-lg shadow-orange-600/20">
                Sign In Now
              </Button>
            </Link>
          </Card>
        ) : error && (
          <Card className="mb-6 border-destructive/50 bg-destructive/10">
            <CardContent className="p-4 text-destructive text-sm font-medium flex items-center gap-2">
              <X className="w-4 h-4" /> {error}
            </CardContent>
          </Card>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading your history...</p>
          </div>
        ) : (role === "passenger" ? bookings.length === 0 : driverRides.length === 0) ? (
          <Card className="p-10 text-center rounded-3xl border-dashed border-2 bg-muted/30">
            <div className="w-16 h-16 bg-background rounded-full flex items-center justify-center mx-auto mb-4 border shadow-sm text-muted-foreground">
              <History className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-bold">Nothing here yet</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {role === "passenger" ? "Go to home to find and book a ride!" : "Start by offering your first ride!"}
            </p>
            <Link href="/">
              <Button className="mt-6 rounded-xl px-8 font-bold shadow-lg shadow-primary/20">
                {role === "passenger" ? "Find Rides" : "Offer Ride"}
              </Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-4">
            {role === "passenger" ? (
              bookings.map((booking) => (
                <Card key={booking.event_id} className="rounded-3xl border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Booking ID</span>
                        <code className="text-xs bg-muted px-2 py-0.5 rounded-lg">{booking.booking_id.slice(0, 8)}</code>
                      </div>
                      {getBadge(booking.action)}
                    </div>

                    <div className="flex items-center gap-4 py-2 border-y border-dashed my-4">
                      <div className="w-10 h-10 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
                        <Car className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-bold truncate">Ride ID: {booking.ride_id.slice(0, 8)}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(booking.occurred_at).toLocaleString("en-IN", {
                            day: "numeric", month: "short", hour: "numeric", minute: "2-digit"
                          })}
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 mt-4">
                      <Link href={`/rides/${booking.ride_id}`} className="flex-1">
                        <Button variant="outline" size="sm" className="w-full rounded-xl font-bold">
                          View Details
                        </Button>
                      </Link>
                      {booking.action === "CONFIRMED" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="rounded-xl text-destructive hover:bg-destructive/10"
                          onClick={() => handleCancelBooking(booking.booking_id)}
                          disabled={cancelling === booking.booking_id}
                        >
                          {cancelling === booking.booking_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              driverRides.map((ride) => (
                <Card key={ride.id} className="rounded-3xl border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1.5">
                          <Badge variant="outline" className="rounded-lg font-bold border-primary/20 text-primary">
                            {ride.available_seats}/{ride.total_seats} Seats • ₹{ride.price_per_seat}
                          </Badge>
                        </div>
                      </div>
                      {getBadge(ride.status)}
                    </div>

                    <div className="space-y-3 mb-6">
                      <div className="flex items-start gap-3">
                        <div className="flex flex-col items-center gap-1 mt-1">
                          <div className="w-2 h-2 rounded-full bg-primary" />
                          <div className="w-0.5 h-4 bg-border" />
                          <div className="w-2 h-2 rounded-full bg-destructive" />
                        </div>
                        <div className="flex-1">
                          <div className="text-sm font-bold truncate">{ride.source}</div>
                          <div className="text-sm font-bold truncate mt-2">{ride.destination}</div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t">
                      <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(ride.departure_time).toLocaleDateString("en-IN", {
                          day: "numeric", month: "short", hour: "numeric", minute: "2-digit"
                        })}
                      </div>
                      <div className="flex gap-2">
                        <Link href={`/rides/${ride.id}`} className="flex-1">
                          <Button size="sm" variant="ghost" className="w-full text-primary font-bold group">
                            Details <ChevronRight className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-1" />
                          </Button>
                        </Link>
                        <Link 
                          href={`/rides/create?source=${encodeURIComponent(ride.source)}&destination=${encodeURIComponent(ride.destination)}&source_lat=${ride.source_lat}&source_lng=${ride.source_lng}&destination_lat=${ride.destination_lat}&destination_lng=${ride.destination_lng}&seats=${ride.total_seats}&price=${ride.price_per_seat}&vehicle_id=${ride.vehicle_id || ""}`}
                          className="flex-1"
                        >
                          <Button size="sm" variant="outline" className="w-full rounded-xl font-bold border-primary/20 text-primary hover:bg-primary/5">
                            <RefreshCw className="w-3 h-3 mr-1" /> Repeat
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
