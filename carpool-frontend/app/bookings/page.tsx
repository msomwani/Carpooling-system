"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Calendar, MapPin, X, History, User, Car } from "lucide-react"

type BookingHistoryItem = {
  event_id: string
  booking_id: string
  ride_id: string
  action: string
  occurred_at: string
  correlation_id: string | null
}

export default function BookingsPage() {
  const [bookings, setBookings] = useState<BookingHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState<string | null>(null)

  const fetchBookings = async () => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch("/api/bookings/history")
      
      if (response.ok) {
        const data = await response.json()
        setBookings(data)
      } else {
        const errorData = await response.json().catch(() => null)
        setError(`Error: ${JSON.stringify(errorData)}`)
      }
    } catch (error) {
      setError("Cannot connect to server. Make sure you're logged in.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchBookings()
  }, [])

  const handleCancel = async (bookingId: string) => {
    if (!confirm("Are you sure you want to cancel this booking?")) return
    
    setCancelling(bookingId)
    try {
      const response = await fetch(`/api/bookings/${bookingId}/cancel`, {
        method: "POST"
      })
      
      if (response.ok) {
        fetchBookings()
      } else {
        const errorData = await response.json().catch(() => null)
        alert(`Failed to cancel: ${JSON.stringify(errorData)}`)
      }
    } catch (error) {
      alert("Failed to cancel booking")
    } finally {
      setCancelling(null)
    }
  }

  const getActionBadge = (action: string) => {
    switch (action) {
      case "CONFIRMED":
        return <Badge className="bg-green-500">Confirmed</Badge>
      case "CANCELLED":
        return <Badge variant="destructive">Cancelled</Badge>
      default:
        return <Badge variant="secondary">{action}</Badge>
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b sticky top-0 bg-background">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="relative w-10 h-10">
                <Image 
                  src="/croc_mascot.png" 
                  alt="Croc Ride Mascot" 
                  fill
                  className="object-contain"
                />
              </div>
            </Link>
            <Link href="/">
              <span className="font-bold text-xl">Croc Ride</span>
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">Dashboard</Button>
            </Link>
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">My Bookings</h1>
          <p className="text-muted-foreground">View your ride booking history</p>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive rounded-lg text-destructive">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading your bookings...</p>
          </div>
        ) : bookings.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <History className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No booking history</h3>
            <p className="text-muted-foreground text-sm mt-1">Find a ride and book your first trip!</p>
            <Link href="/rides">
              <Button className="mt-4">Find Rides</Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-4">
            {bookings.map((booking) => (
              <Card key={booking.event_id}>
                <CardContent className="pt-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        {getActionBadge(booking.action)}
                        <span className="text-xs text-muted-foreground">
                          Booking ID: {booking.booking_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          <Car className="h-4 w-4 text-muted-foreground" />
                          <span className="font-mono text-xs">Ride: {booking.ride_id}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {new Date(booking.occurred_at).toLocaleString("en-IN", {
                            weekday: "short",
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                    {booking.action === "CONFIRMED" && (
                      <Button 
                        variant="outline" 
                        onClick={() => handleCancel(booking.booking_id)}
                        disabled={cancelling === booking.booking_id}
                      >
                        {cancelling === booking.booking_id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <>
                            <X className="mr-2 h-4 w-4" /> Cancel
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
