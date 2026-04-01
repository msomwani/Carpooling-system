"use client"

import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import dynamic from "next/dynamic"
import {
  Loader2,
  Clock,
  ChevronLeft,
  User,
  Car,
  Calendar,
  Users,
  Info,
  CheckCircle2,
  Navigation,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/lib/AuthContext"

const OpenMap = dynamic(
  () => import("@/components/OpenMap").then((mod) => mod.OpenMap),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[250px] bg-muted rounded-2xl flex items-center justify-center border">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    ),
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
    total_seats: number
    price_per_seat: number
    status: "SCHEDULED" | "STARTED" | "COMPLETED" | "CANCELLED" | "MISSED_START"
    driver_id: string
    route_geometry: string | null
    actual_started_at: string | null
    actual_completed_at: string | null
    completed_by: "DRIVER" | "SYSTEM" | null
  }
  driver_name: string
  vehicle_make: string | null
  vehicle_model: string | null
  vehicle_color: string | null
  vehicle_license_plate: string | null
}

type BookingStatus = {
  has_booking: boolean
  booking_id: string | null
  status: "PENDING_PAYMENT" | "PAID_HELD" | "CONFIRMED" | "REFUNDED" | "CANCELLED" | null
  trip_status: "BOOKED" | "READY_AT_PICKUP" | "BOARDED" | "DROPPED" | "NO_SHOW" | null
  boarded_seats: number
  passenger_ready_at: string | null
  passenger_boarding_confirmed_at: string | null
  can_mark_ready: boolean
  can_confirm_boarding: boolean
  can_cancel: boolean
}

type ManifestBooking = {
  booking_id: string
  passenger_name: string
  seats_booked: number
  boarded_seats: number
  trip_status: "BOOKED" | "READY_AT_PICKUP" | "BOARDED" | "DROPPED" | "NO_SHOW"
  passenger_ready_at: string | null
  passenger_boarding_confirmed_at: string | null
  payment_status: "PENDING_PAYMENT" | "PAID_HELD" | "CONFIRMED" | "REFUNDED" | "CANCELLED"
}

type RazorpayPaymentResponse = {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

type RazorpayCheckoutOptions = {
  key: string
  amount: number
  currency: string
  name: string
  description: string
  order_id: string
  handler: (paymentResponse: RazorpayPaymentResponse) => void | Promise<void>
  prefill: {
    name?: string
    email?: string
  }
  theme: {
    color: string
  }
  modal: {
    ondismiss: () => void
  }
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayCheckoutOptions) => { open: () => void }
  }
}

export default function RideDetailsPage() {
  const params = useParams()
  const id = params?.id as string
  const router = useRouter()
  const { user, getAuthHeaders } = useAuth()

  const [details, setDetails] = useState<RideDetails | null>(null)
  const [bookingStatus, setBookingStatus] = useState<BookingStatus | null>(null)
  const [manifest, setManifest] = useState<ManifestBooking[]>([])
  const [boardedDrafts, setBoardedDrafts] = useState<Record<string, number>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [bookingSeats, setBookingSeats] = useState(1)
  const [isBooking, setIsBooking] = useState(false)
  const [isActing, setIsActing] = useState<string | null>(null)
  const [bookingError, setBookingError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const bookingAttemptKeyRef = useRef<string | null>(null)
  const bookingInFlightRef = useRef(false)

  const ride = details?.ride
  const isDriver = Boolean(user && ride && user.id === ride.driver_id)

  const createBookingAttemptKey = () => {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
      return `${id}-${crypto.randomUUID()}`
    }
    return `${id}-${Math.random().toString(36).slice(2)}-${Date.now()}`
  }

  const getBookingAttemptKey = () => {
    if (!bookingAttemptKeyRef.current) {
      bookingAttemptKeyRef.current = createBookingAttemptKey()
    }
    return bookingAttemptKeyRef.current
  }

  const resetBookingAttemptKey = () => {
    bookingAttemptKeyRef.current = null
  }

  const normalizeCancelBookingError = (message: string) => {
    if (message.includes("Failed to process refund with Razorpay")) {
      return "Cancellation could not be completed because Razorpay could not process the refund right now. Please try again shortly."
    }

    return message
  }

  const getApiErrorMessage = async (response: Response, fallback: string) => {
    try {
      const data = await response.json()
      if (typeof data?.detail === "string" && data.detail.trim()) {
        return data.detail
      }
    } catch {
      // Ignore parse failures and fall back to the provided message.
    }

    return fallback
  }

  const getCurrentLocation = async () => {
    if (!navigator.geolocation) {
      throw new Error("Location access is not available in this browser.")
    }
    return new Promise<{ lat: number; lng: number }>((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          }),
        () => reject(new Error("Location permission is required for this action.")),
        { enableHighAccuracy: true, timeout: 10000 }
      )
    })
  }

  const syncBoardedDrafts = (rows: ManifestBooking[]) => {
    setBoardedDrafts((current) => {
      const next = { ...current }
      for (const row of rows) {
        if (!(row.booking_id in next)) {
          next[row.booking_id] = row.boarded_seats > 0 ? row.boarded_seats : row.seats_booked
        }
      }
      return next
    })
  }

  const fetchDetails = async () => {
    const response = await fetch(`/api/rides/${id}`)
    if (!response.ok) {
      throw new Error("Ride not found or could not be loaded.")
    }
    const data = await response.json()
    setDetails(data)
    return data as RideDetails
  }

  const fetchBookingStatus = async () => {
    if (!user) return
    const response = await fetch(`/api/bookings/status/${id}`, {
      headers: getAuthHeaders(),
      credentials: "include",
    })
    if (response.ok) {
      const data = await response.json()
      setBookingStatus(data)
    }
  }

  const fetchManifest = async () => {
    if (!user) return
    const response = await fetch(`/api/rides/${id}/manifest`, {
      headers: getAuthHeaders(),
      credentials: "include",
    })
    if (response.ok) {
      const data = await response.json()
      setManifest(data)
      syncBoardedDrafts(data)
    }
  }

  const refreshPageData = async () => {
    try {
      setError(null)
      const rideData = await fetchDetails()
      if (user) {
        if (user.id === rideData.ride.driver_id) {
          await fetchManifest()
          setBookingStatus(null)
        } else {
          await fetchBookingStatus()
          setManifest([])
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    setIsLoading(true)
    refreshPageData()
  }, [id, user])

  useEffect(() => {
    if (!ride || ride.status !== "STARTED") return
    const timer = window.setInterval(() => {
      refreshPageData()
    }, 15000)
    return () => window.clearInterval(timer)
  }, [ride?.status, user, id])

  const handleBook = async () => {
    if (!user) {
      router.push("/login")
      return
    }

    if (bookingInFlightRef.current) {
      return
    }

    bookingInFlightRef.current = true
    setIsBooking(true)
    setBookingError(null)

    try {
      const response = await fetch("/api/bookings", {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Idempotency-Key": getBookingAttemptKey(),
        },
        credentials: "include",
        body: JSON.stringify({
          ride_id: id,
          seats: bookingSeats,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        setBookingError(data.detail || "Booking failed. Please try again.")
        setIsBooking(false)
        return
      }

      const bookingData = await response.json()
      const totalAmount = Math.round(bookingSeats * details!.ride.price_per_seat)

      if (isNaN(totalAmount) || totalAmount <= 0) {
        setBookingError("Invalid payment amount calculation.")
        setIsBooking(false)
        return
      }

      const orderResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/payments/create-order`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
        body: JSON.stringify({ booking_id: bookingData.booking_id }),
      })

      if (!orderResponse.ok) {
        setBookingError(await getApiErrorMessage(orderResponse, "Payment initialization failed. Please try again."))
        setIsBooking(false)
        return
      }

      const order = await orderResponse.json()

      const options: RazorpayCheckoutOptions = {
        key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID ?? "",
        amount: order.amount,
        currency: "INR",
        name: "Croc Ride",
        description: `${bookingSeats} seat(s) from ${details!.ride.source} to ${details!.ride.destination}`,
        order_id: order.id,
        handler: async function (paymentResponse: RazorpayPaymentResponse) {
          try {
            const verifyResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/payments/verify`, {
              method: "POST",
              headers: getAuthHeaders(),
              credentials: "include",
              body: JSON.stringify({
                razorpay_order_id: paymentResponse.razorpay_order_id,
                razorpay_payment_id: paymentResponse.razorpay_payment_id,
                razorpay_signature: paymentResponse.razorpay_signature,
                booking_id: bookingData.booking_id,
              }),
            })
            if (verifyResponse.ok) {
              await refreshPageData()
              resetBookingAttemptKey()
              setIsBooking(false)
            } else {
              setBookingError(await getApiErrorMessage(verifyResponse, "Payment verification failed. Please contact support."))
              setIsBooking(false)
            }
          } catch (error) {
            console.error("Payment verification error:", error)
            setBookingError("An error occurred during verification.")
            setIsBooking(false)
          }
        },
        prefill: {
          name: user?.name,
          email: user?.email,
        },
        theme: { color: "#15803d" },
        modal: {
          ondismiss: () => {
            setIsBooking(false)
          },
        },
      }

      const rzp = new window.Razorpay(options)
      rzp.open()
    } catch {
      setBookingError("Connection failed. Check your internet.")
      setIsBooking(false)
    } finally {
      bookingInFlightRef.current = false
    }
  }

  const handleDriverLocationAction = async (action: "start" | "complete") => {
    setActionError(null)
    setIsActing(action)
    try {
      const location = await getCurrentLocation()
      const endpoint = action === "start" ? "start" : "complete"
      const response = await fetch(`/api/rides/${id}/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        credentials: "include",
        body: JSON.stringify(location),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || `Failed to ${action} ride`)
      }
      await refreshPageData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : `Failed to ${action} ride`)
    } finally {
      setIsActing(null)
    }
  }

  const handleBookingAction = async (endpoint: string, loadingKey: string, body?: Record<string, unknown>) => {
    if (!bookingStatus?.booking_id) return
    setActionError(null)
    setIsActing(loadingKey)
    try {
      const response = await fetch(`/api/bookings/${bookingStatus.booking_id}/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        credentials: "include",
        body: body ? JSON.stringify(body) : undefined,
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || "Action failed")
      }
      await refreshPageData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Action failed")
    } finally {
      setIsActing(null)
    }
  }

  const handleBoardPassenger = async (bookingId: string) => {
    setActionError(null)
    setIsActing(`board-${bookingId}`)
    try {
      const boardedSeats = boardedDrafts[bookingId]
      const response = await fetch(`/api/bookings/${bookingId}/board`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        credentials: "include",
        body: JSON.stringify({ boarded_seats: boardedSeats }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || "Failed to board passenger")
      }
      await refreshPageData()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to board passenger")
    } finally {
      setIsActing(null)
    }
  }

  const handleCancelRide = async () => {
    if (!confirm("Cancel this scheduled ride? Confirmed passengers will be refunded.")) return
    setIsActing("cancel-ride")
    setActionError(null)
    try {
      const response = await fetch(`/api/rides/${id}/cancel`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
      })
      if (response.ok) {
        router.push("/bookings")
      } else {
        const data = await response.json()
        throw new Error(data.detail || "Failed to cancel ride")
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to cancel ride")
    } finally {
      setIsActing(null)
    }
  }

  const handleCancelBooking = async () => {
    if (!bookingStatus?.booking_id) return
    if (!confirm("Cancel this booking?")) return
    setIsActing("cancel-booking")
    setActionError(null)
    try {
      const response = await fetch(`/api/bookings/${bookingStatus.booking_id}/cancel`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
      })
      if (response.ok) {
        router.push("/bookings")
      } else {
        const data = await response.json()
        throw new Error(normalizeCancelBookingError(data.detail || "Failed to cancel booking"))
      }
    } catch (err) {
      setActionError(normalizeCancelBookingError(err instanceof Error ? err.message : "Failed to cancel booking"))
    } finally {
      setIsActing(null)
    }
  }

  const getRideBadge = (status: RideDetails["ride"]["status"]) => {
    switch (status) {
      case "SCHEDULED":
        return <Badge className="bg-amber-500 text-white border-none rounded-lg">Scheduled</Badge>
      case "STARTED":
        return <Badge className="bg-green-600 text-white border-none rounded-lg">Started</Badge>
      case "COMPLETED":
        return <Badge className="bg-blue-600 text-white border-none rounded-lg">Completed</Badge>
      case "MISSED_START":
        return <Badge className="bg-orange-500 text-white border-none rounded-lg">Missed Start</Badge>
      case "CANCELLED":
        return <Badge variant="destructive" className="rounded-lg">Cancelled</Badge>
    }
  }

  const getTripLabel = () => {
    if (!bookingStatus?.trip_status) return "No trip action yet"
    return bookingStatus.trip_status.replaceAll("_", " ")
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
          <Button onClick={() => router.push("/")} variant="default" className="rounded-xl w-full">
            Back to Search
          </Button>
        </Card>
      </div>
    )
  }

  const departureDate = new Date(ride!.departure_time)

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="sticky top-0 bg-background/80 backdrop-blur-md z-40 border-b">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()} className="rounded-full">
            <ChevronLeft className="h-6 w-6" />
          </Button>
          <h1 className="font-bold text-lg">Ride Details</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {ride!.source_lat && ride!.source_lng && (
          <div className="rounded-3xl overflow-hidden border shadow-sm h-48 relative">
            <OpenMap
              pickup={{ lat: ride!.source_lat, lng: ride!.source_lng }}
              dropoff={ride!.destination_lat && ride!.destination_lng ? { lat: ride!.destination_lat, lng: ride!.destination_lng } : undefined}
              route={ride!.route_geometry || undefined}
              zoom={12}
            />
            <div className="absolute bottom-3 left-3 right-3 bg-background/90 backdrop-blur-sm p-2 rounded-xl border text-[10px] font-bold uppercase tracking-tight text-muted-foreground text-center">
              Route verification uses the ride source and destination points
            </div>
          </div>
        )}

        <Card className="rounded-3xl border-none shadow-sm overflow-hidden bg-card">
          <CardHeader className="bg-primary/5 border-b pb-4">
            <div className="flex justify-between items-center">
              {getRideBadge(ride!.status)}
              <div className="text-right">
                <p className="text-[10px] font-black uppercase text-muted-foreground">Price per seat</p>
                <p className="text-2xl font-black text-primary leading-none">₹{ride!.price_per_seat}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="relative flex gap-4">
              <div className="flex flex-col items-center gap-1 py-1">
                <div className="w-4 h-4 rounded-full border-4 border-primary bg-background" />
                <div className="w-0.5 flex-1 bg-muted-foreground/20" />
                <div className="w-4 h-4 rounded-full border-4 border-destructive bg-background" />
              </div>
              <div className="flex-1 space-y-8">
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Pickup From</p>
                  <p className="font-bold text-lg leading-tight">{ride!.source}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Destination</p>
                  <p className="font-bold text-lg leading-tight">{ride!.destination}</p>
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
                  <p className="font-bold text-sm" suppressHydrationWarning>
                    {departureDate.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-muted flex items-center justify-center text-primary">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Time</p>
                  <p className="font-bold text-sm" suppressHydrationWarning>
                    {departureDate.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

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
                <p className="font-bold text-lg">
                  {details.vehicle_make} {details.vehicle_model} <span className="text-muted-foreground text-sm">({details.vehicle_color})</span>
                </p>
              </div>
            </div>
            <div className="bg-primary/5 p-3 rounded-2xl text-center border border-primary/10">
              <p className="text-xs font-bold text-primary tracking-widest uppercase">{details.vehicle_license_plate || "No Plate Info"}</p>
            </div>
          </Card>
        </div>

        {actionError && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-2xl text-sm font-medium border border-destructive/20">
            {actionError}
          </div>
        )}

        {isDriver ? (
          <Card className="rounded-3xl border-2 border-primary/20 shadow-sm overflow-hidden">
            <CardHeader className="bg-primary/5 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold uppercase text-muted-foreground">Driver Mode</p>
                  <p className="font-bold text-lg">
                    {ride!.status === "SCHEDULED"
                      ? "Start the ride near pickup"
                      : ride!.status === "STARTED"
                      ? "Board passengers and complete the ride"
                      : "Ride lifecycle summary"}
                  </p>
                </div>
                {getRideBadge(ride!.status)}
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-5">
              {ride!.status === "SCHEDULED" && (
                <>
                  <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                    Starting the ride will use your current location and verify you are near the pickup point.
                  </div>
                  <div className="grid gap-3">
                    <Button
                      className="h-12 rounded-2xl font-bold"
                      disabled={isActing === "start"}
                      onClick={() => handleDriverLocationAction("start")}
                    >
                      {isActing === "start" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Navigation className="mr-2 h-4 w-4" />}
                      Start Ride
                    </Button>
                    <Button
                      variant="destructive"
                      className="h-12 rounded-2xl font-bold"
                      disabled={isActing === "cancel-ride"}
                      onClick={handleCancelRide}
                    >
                      {isActing === "cancel-ride" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Cancel Scheduled Ride
                    </Button>
                  </div>
                </>
              )}

              {ride!.status === "STARTED" && (
                <>
                  <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                    Passengers must tap <span className="font-semibold">I&apos;m here</span> first. Then you can mark their boarded seat count.
                  </div>
                  <div className="space-y-3">
                    {manifest.length === 0 ? (
                      <div className="rounded-2xl bg-muted/50 p-4 text-sm text-muted-foreground">No paid passengers to verify yet.</div>
                    ) : (
                      manifest.map((entry) => (
                        <div key={entry.booking_id} className="rounded-2xl border p-4 space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-bold">{entry.passenger_name}</p>
                              <p className="text-xs text-muted-foreground">
                                Payment: {entry.payment_status} • Trip: {entry.trip_status.replaceAll("_", " ")}
                              </p>
                            </div>
                            <Badge variant="outline" className="rounded-lg">
                              {entry.boarded_seats}/{entry.seats_booked} boarded
                            </Badge>
                          </div>

                          <div className="grid grid-cols-[1fr_auto] gap-3 items-end">
                            <div>
                              <p className="text-[10px] uppercase font-bold text-muted-foreground mb-2">Boarded Seats</p>
                              <Input
                                type="number"
                                min={1}
                                max={entry.seats_booked}
                                value={boardedDrafts[entry.booking_id] ?? entry.seats_booked}
                                onChange={(e) =>
                                  setBoardedDrafts((current) => ({
                                    ...current,
                                    [entry.booking_id]: Number(e.target.value),
                                  }))
                                }
                              />
                            </div>
                            <Button
                              className="rounded-xl font-bold"
                              disabled={
                                isActing === `board-${entry.booking_id}` ||
                                entry.trip_status === "BOOKED" ||
                                entry.payment_status === "REFUNDED" ||
                                entry.payment_status === "CANCELLED"
                              }
                              onClick={() => handleBoardPassenger(entry.booking_id)}
                            >
                              {isActing === `board-${entry.booking_id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : "Mark Boarded"}
                            </Button>
                          </div>

                          {entry.passenger_ready_at && (
                            <p className="text-xs text-green-700">Passenger marked ready at pickup.</p>
                          )}
                          {entry.passenger_boarding_confirmed_at && (
                            <p className="text-xs text-blue-700">Passenger confirmed boarding.</p>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  <Button
                    className="w-full h-12 rounded-2xl font-bold"
                    disabled={isActing === "complete"}
                    onClick={() => handleDriverLocationAction("complete")}
                  >
                    {isActing === "complete" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                    Complete Ride
                  </Button>
                </>
              )}

              {ride!.status !== "SCHEDULED" && ride!.status !== "STARTED" && (
                <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                  {ride!.status === "COMPLETED" && `Ride completed${ride!.completed_by ? ` by ${ride!.completed_by.toLowerCase()}` : ""}.`}
                  {ride!.status === "MISSED_START" && "This ride was marked as missed start and held payments were refunded."}
                  {ride!.status === "CANCELLED" && "This ride was cancelled before it started."}
                </div>
              )}
            </CardContent>
          </Card>
        ) : bookingStatus?.has_booking ? (
          <Card className="rounded-3xl border-2 border-primary/20 shadow-sm overflow-hidden">
            <CardHeader className="bg-primary/5 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold uppercase text-muted-foreground">Your Ride Status</p>
                  <p className="font-bold text-lg">{getTripLabel()}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Payment</p>
                  <p className="font-bold">{bookingStatus.status}</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                {ride!.status === "SCHEDULED" && "Wait for the driver to start the ride. Once it starts, you can mark yourself ready at pickup."}
                {ride!.status === "STARTED" && "Use the buttons below to check in and confirm boarding."}
                {ride!.status === "COMPLETED" && "This ride has been completed and settled."}
                {ride!.status === "MISSED_START" && "This ride did not start on time. Held payment has been refunded."}
              </div>

              <div className="text-sm text-muted-foreground">
                Boarded seats: <span className="font-semibold text-foreground">{bookingStatus.boarded_seats}</span>
              </div>

              <div className="grid gap-3">
                {bookingStatus.can_mark_ready && (
                  <Button
                    className="h-12 rounded-2xl font-bold"
                    disabled={isActing === "ready"}
                    onClick={() => handleBookingAction("ready", "ready")}
                  >
                    {isActing === "ready" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    I&apos;m Here
                  </Button>
                )}

                {bookingStatus.can_confirm_boarding && (
                  <Button
                    variant="outline"
                    className="h-12 rounded-2xl font-bold"
                    disabled={isActing === "confirm-boarding"}
                    onClick={() => handleBookingAction("confirm-boarding", "confirm-boarding")}
                  >
                    {isActing === "confirm-boarding" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    I Boarded
                  </Button>
                )}

                {bookingStatus.can_cancel && (
                  <Button
                    variant="destructive"
                    className="h-12 rounded-2xl font-bold"
                    disabled={isActing === "cancel-booking"}
                    onClick={handleCancelBooking}
                  >
                    {isActing === "cancel-booking" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Cancel My Booking
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="rounded-3xl border-2 border-primary shadow-xl shadow-primary/5 overflow-hidden">
            <div className="p-6 bg-primary/5 border-b flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-white shadow-sm flex items-center justify-center text-primary">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Availability</p>
                  <p className="font-bold text-sm">{ride!.available_seats} seats remaining</p>
                </div>
              </div>
              {getRideBadge(ride!.status)}
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
                      onClick={() => setBookingSeats(Math.min(ride!.available_seats, bookingSeats + 1))}
                    >
                      +
                    </Button>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Total</p>
                  <p className="text-xl font-black text-primary leading-none">₹{bookingSeats * ride!.price_per_seat}</p>
                </div>
              </div>

              {bookingError && (
                <div className="p-4 bg-destructive/10 text-destructive rounded-2xl text-xs font-bold text-center border border-destructive/20">
                  {bookingError}
                </div>
              )}

              <Button
                className="w-full h-14 rounded-2xl text-lg font-bold shadow-lg shadow-green-500/20 bg-[#15803d] hover:bg-[#166534] text-white transition-all active:scale-[0.98]"
                disabled={isBooking || ride!.available_seats < 1 || ride!.status !== "SCHEDULED"}
                onClick={handleBook}
              >
                {isBooking ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Processing...
                  </>
                ) : ride!.status !== "SCHEDULED" ? (
                  "Ride Unavailable"
                ) : (
                  "Confirm Booking"
                )}
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
