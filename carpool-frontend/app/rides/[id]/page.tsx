"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Loader2, 
  MapPin, 
  Clock, 
  ChevronLeft, 
  User, 
  Car, 
  Calendar, 
  Users, 
  Wallet,
  Info
} from "lucide-react"
import { useAuth } from "@/lib/AuthContext"
import dynamic from "next/dynamic"

// Dynamically import the map to prevent SSR issues with Leaflet
const OpenMap = dynamic(
  () => import("@/components/OpenMap").then((mod) => mod.OpenMap),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[250px] bg-muted rounded-2xl flex items-center justify-center border">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }
)

type RideDetails = {
  ride: {
    id: string
    source: string
    source_lat: number | null
    source_lng: number | null
    destination: string
    destination_lat: number | null
    destination_lng: number | null
    departure_time: string
    available_seats: number
    price_per_seat: number
    status: string
    driver_id: string
    route_geometry: string | null
  }
  driver_name: string
  vehicle_make: string | null
  vehicle_model: string | null
  vehicle_color: string | null
  vehicle_license_plate: string | null
}

export default function RideDetailsPage() {
  const params = useParams()
  const id = params?.id as string
  const router = useRouter()
  const { user, getAuthHeaders } = useAuth()
  const [details, setDetails] = useState<RideDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bookingSeats, setBookingSeats] = useState(1)
  const [isBooking, setIsBooking] = useState(false)
  const [bookingError, setBookingError] = useState<string | null>(null)
  const [bookingStatus, setBookingStatus] = useState<{ has_booking: boolean, booking_id: string | null } | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)

  const fetchDetails = async () => {
    try {
      const response = await fetch(`/api/rides/${id}`)
      if (response.ok) {
        const data = await response.json()
        setDetails(data)
      } else {
        setError("Ride not found or could not be loaded.")
      }
    } catch (err) {
      setError("Network error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const fetchBookingStatus = async () => {
    if (!user) return
    try {
      const response = await fetch(`/api/bookings/status/${id}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setBookingStatus(data)
      }
    } catch (err) {
      console.error("Failed to fetch booking status", err)
    }
  }

  useEffect(() => {
    if (id) {
      fetchDetails()
      fetchBookingStatus()
    }
  }, [id, user])

  const handleBook = async () => {
    if (!user) {
      router.push('/login')
      return
    }

    setIsBooking(true)
    setBookingError(null)

    try {
      const response = await fetch("/api/bookings", {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Idempotency-Key": `${id}-${Date.now()}`
        },
        body: JSON.stringify({
          ride_id: id,
          seats: bookingSeats
        })
      })

      if (response.ok) {
        // Update local state immediately
        await Promise.all([
          fetchDetails(),
          fetchBookingStatus()
        ])
        router.push("/bookings")
      } else {
        const data = await response.json()
        setBookingError(data.detail || "Booking failed. Please try again.")
      }
    } catch (err) {
      setBookingError("Connection failed. Check your internet.")
    } finally {
      setIsBooking(false)
    }
  }

  const handleCancelRide = async () => {
    if (!confirm("Are you sure you want to cancel this ride? All confirmed passengers will be notified and refunded.")) return
    setIsCancelling(true)
    try {
      const response = await fetch(`/api/rides/${id}/cancel`, {
        method: "POST",
        headers: getAuthHeaders()
      })
      if (response.ok) {
        router.push("/bookings")
      } else {
        const data = await response.json()
        alert(data.detail || "Failed to cancel ride")
      }
    } catch (err) {
      alert("Failed to cancel ride")
    } finally {
      setIsCancelling(false)
    }
  }

  const handleCancelBooking = async () => {
    if (!bookingStatus?.booking_id) return
    if (!confirm("Are you sure you want to cancel your booking?")) return
    setIsCancelling(true)
    try {
      const response = await fetch(`/api/bookings/${bookingStatus.booking_id}/cancel`, {
        method: "POST",
        headers: getAuthHeaders()
      })
      if (response.ok) {
        router.push("/bookings")
      } else {
        const data = await response.json()
        alert(data.detail || "Failed to cancel booking")
      }
    } catch (err) {
      alert("Failed to cancel booking")
    } finally {
      setIsCancelling(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="font-medium text-muted-foreground">Loading ride details...</p>
        </div>
      </div>
    )
  }

  if (error || !details) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="max-w-md w-full p-8 text-center rounded-3xl border-dashed">
          <Info className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Oops!</h2>
          <p className="text-muted-foreground mb-6">{error || "Something went wrong"}</p>
          <Button onClick={() => router.push('/')} variant="default" className="rounded-xl w-full">
            Back to Search
          </Button>
        </Card>
      </div>
    )
  }

  const { ride } = details
  const departureDate = new Date(ride.departure_time)

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Sticky Header */}
      <header className="sticky top-0 bg-background/80 backdrop-blur-md z-40 border-b">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()} className="rounded-full">
            <ChevronLeft className="h-6 w-6" />
          </Button>
          <h1 className="font-bold text-lg">Ride Details</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Map Preview */}
        {ride.source_lat && ride.source_lng && (
          <div className="rounded-3xl overflow-hidden border shadow-sm h-48 relative">
            <OpenMap 
              pickup={{ lat: ride.source_lat, lng: ride.source_lng }}
              dropoff={ride.destination_lat && ride.destination_lng ? { lat: ride.destination_lat, lng: ride.destination_lng } : undefined}
              route={ride.route_geometry || undefined}
              zoom={12} 
            />
            <div className="absolute bottom-3 left-3 right-3 bg-background/90 backdrop-blur-sm p-2 rounded-xl border text-[10px] font-bold uppercase tracking-tight text-muted-foreground text-center">
              Routes around Vadodara-Halol Corridor
            </div>
          </div>
        )}

        {/* Route Card */}
        <Card className="rounded-3xl border-none shadow-sm overflow-hidden bg-card">
          <CardHeader className="bg-primary/5 border-b pb-4">
            <div className="flex justify-between items-center">
              <Badge variant="outline" className="bg-background text-primary border-primary/20 rounded-lg">
                Active Ride
              </Badge>
              <div className="text-right">
                <p className="text-[10px] font-black uppercase text-muted-foreground">Price per seat</p>
                <p className="text-2xl font-black text-primary leading-none">₹{ride.price_per_seat}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="relative flex gap-4">
              <div className="flex flex-col items-center gap-1 py-1">
                <div className="w-4 h-4 rounded-full border-4 border-primary bg-background" />
                <div className="w-0.5 flex-1 bg-muted-foreground/20 dashed-border" />
                <div className="w-4 h-4 rounded-full border-4 border-destructive bg-background" />
              </div>
              <div className="flex-1 space-y-8">
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Pickup From</p>
                  <p className="font-bold text-lg leading-tight">{ride.source}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Destination</p>
                  <p className="font-bold text-lg leading-tight">{ride.destination}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-muted flex items-center justify-center text-primary">
                  <Calendar className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Date</p>
                  <p className="font-bold text-sm" suppressHydrationWarning>{departureDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-muted flex items-center justify-center text-primary">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Time</p>
                  <p className="font-bold text-sm" suppressHydrationWarning>{departureDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Driver & Vehicle Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="rounded-3xl border shadow-sm p-5 space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                <User className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase">Offered by</p>
                <p className="font-bold text-lg">{details.driver_name}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-muted/50 p-3 rounded-2xl">
              <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-none rounded-lg">Verified Account</Badge>
              <span className="text-xs text-muted-foreground font-medium">Member</span>
            </div>
          </Card>

          <Card className="rounded-3xl border shadow-sm p-5 space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                <Car className="h-6 w-6" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase">Vehicle info</p>
                <p className="font-bold text-lg">{details.vehicle_make} {details.vehicle_model} <span className="text-muted-foreground text-sm">({details.vehicle_color})</span></p>
              </div>
            </div>
            <div className="bg-primary/5 p-3 rounded-2xl text-center border border-primary/10">
              <p className="text-xs font-bold text-primary tracking-widest uppercase">{details.vehicle_license_plate || "No Plate Info"}</p>
            </div>
          </Card>
        </div>

        {/* Booking/Management Action */}
        {user && (user.id === ride.driver_id || bookingStatus?.has_booking) ? (
          <div className="space-y-4 pt-4">
            {user.id === ride.driver_id && (
              <div className="bg-muted/50 p-4 rounded-2xl border border-dashed text-center">
                <p className="text-sm font-bold text-muted-foreground uppercase tracking-tight">Driver Mode</p>
                <p className="text-xs text-muted-foreground">You can cancel this ride, but details cannot be changed.</p>
              </div>
            )}
            <Button 
              variant="destructive"
              className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-destructive/20 active:scale-[0.98] transition-all"
              disabled={isCancelling || ride.status !== 'ACTIVE'}
              onClick={user.id === ride.driver_id ? handleCancelRide : handleCancelBooking}
            >
              {isCancelling ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Processing...
                </>
              ) : (
                user.id === ride.driver_id ? "Cancel Entire Ride" : "Cancel My Booking"
              )}
            </Button>
          </div>
        ) : (
          <Card className="rounded-3xl border-2 border-primary shadow-xl shadow-primary/5 overflow-hidden">
            <div className="p-6 bg-primary/5 border-b flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-white shadow-sm flex items-center justify-center text-primary">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Availability</p>
                  <p className="font-bold text-sm">{ride.available_seats} seats remaining</p>
                </div>
              </div>
              {ride.status !== 'ACTIVE' && (
                <Badge variant="secondary" className="rounded-lg h-6 px-3">{ride.status}</Badge>
              )}
            </div>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center justify-between gap-4 bg-muted/30 p-4 rounded-2xl">
                <div className="flex items-center gap-4">
                  <p className="font-bold text-sm">Seats</p>
                  <div className="flex items-center gap-2">
                    <Button 
                      variant="outline" 
                      size="icon" 
                      className="h-8 w-8 rounded-lg"
                      onClick={() => setBookingSeats(Math.max(1, bookingSeats - 1))}
                    >
                      -
                    </Button>
                    <span className="w-8 text-center font-black text-lg">{bookingSeats}</span>
                    <Button 
                      variant="outline" 
                      size="icon" 
                      className="h-8 w-8 rounded-lg"
                      onClick={() => setBookingSeats(Math.min(ride.available_seats, bookingSeats + 1))}
                    >
                      +
                    </Button>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Total</p>
                  <p className="text-xl font-black text-primary leading-none">₹{bookingSeats * ride.price_per_seat}</p>
                </div>
              </div>

              {bookingError && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-2xl text-xs font-bold text-center border border-destructive/20">
                  {bookingError}
                </div>
              )}

              <Button 
                className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-green-500/20 bg-[#15803d] hover:bg-[#166534] text-white transition-all active:scale-[0.98]"
                disabled={isBooking || ride.available_seats < 1 || ride.status !== 'ACTIVE'}
                onClick={handleBook}
              >
                {isBooking ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  ride.status !== 'ACTIVE' ? "Ride Unavailable" : "Confirm Booking"
                )}
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
