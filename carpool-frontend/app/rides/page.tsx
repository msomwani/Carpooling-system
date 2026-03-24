"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Loader2, Search, MapPin, Clock, Users, Menu, X, Home, Car as CarIcon, User } from "lucide-react"
import { useAuth } from "@/lib/AuthContext"

type Ride = {
  id: string
  source: string
  destination: string
  departure_time: string
  available_seats: number
  price_per_seat: number
  total_seats: number
  status: "ACTIVE" | "COMPLETED" | "CANCELLED"
}

export default function RidesPage() {
  const router = useRouter()
  const [rides, setRides] = useState<Ride[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchSource, setSearchSource] = useState("")
  const [searchDest, setSearchDest] = useState("")
  const [debugError, setDebugError] = useState<string | null>(null)

  const { user, getAuthHeaders } = useAuth()

  const searchRides = async () => {
    setIsLoading(true)
    setDebugError(null)

    try {
      if (searchSource && searchDest) {
        const params = new URLSearchParams()
        params.set("source", searchSource)
        params.set("destination", searchDest)
        const response = await fetch(`/api/rides?${params.toString()}`)

        if (response.ok) {
          const data = await response.json()
          setRides(data)
        } else {
          const errorData = await response.json().catch(() => null)
          setDebugError(`Error: ${JSON.stringify(errorData)}`)
        }
      } else {
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
          setRides([])
        }
      }
    } catch (error) {
      setDebugError("Cannot connect to server.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    searchRides()
  }, [])

  const handleRideClick = (rideId: string) => {
    router.push(`/rides/${rideId}`)
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
                  src="/croc_mascot(y).png"
                  alt="Croc"
                  fill
                  sizes="32px"
                  className="object-contain"
                />
              </div>
            </Link>
            <Link href="/">
              <span className="font-bold text-lg">Croc Ride</span>
            </Link>
          </div>

        </div>
      </header>


      <div className="max-w-6xl mx-auto p-6 pb-24">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Find a Ride</h1>
          <p className="text-muted-foreground">Search for rides from Vadodara to Halol</p>
        </div>

        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">From</label>
                <Input
                  placeholder="e.g., Fatehgunj, GIDC..."
                  value={searchSource}
                  onChange={(e) => setSearchSource(e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">To</label>
                <Input
                  placeholder="e.g., Halol, GIDC..."
                  value={searchDest}
                  onChange={(e) => setSearchDest(e.target.value)}
                />
              </div>
              <div className="flex items-end">
                <Button onClick={searchRides} className="w-full">
                  <Search className="mr-2 h-4 w-4" /> Search
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {debugError && (
          <div className="mb-6 p-4 border border-destructive rounded-lg text-destructive">
            {debugError}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-40 gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Finding rides...</p>
          </div>
        ) : rides.length === 0 ? (
          <Card className="p-8 text-center">
            <h3 className="text-lg font-semibold">No rides found</h3>
            <p className="text-muted-foreground text-sm mt-1">
              {searchSource || searchDest ? "Try different locations." : "No rides available in your area."}
            </p>
            <div className="mt-4 flex justify-center gap-3">
              <Button variant="outline" onClick={searchRides}>Refresh</Button>
              <Link href="/rides/create">
                <Button>Offer a Ride</Button>
              </Link>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{rides.length} rides found</p>
            {rides.map((ride) => (
              <Card key={ride.id} className="hover:shadow-md transition-all">
                <CardContent className="pt-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <Badge variant="secondary">{ride.status}</Badge>
                        <span className="text-sm text-muted-foreground">
                          {ride.available_seats}/{ride.total_seats} seats • ₹{ride.price_per_seat}
                        </span>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-primary"></div>
                          <span className="font-medium">{ride.source}</span>
                        </div>
                        <span className="text-muted-foreground">→</span>
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full bg-destructive"></div>
                          <span className="font-medium">{ride.destination}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-3 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {new Date(ride.departure_time).toLocaleString("en-IN", {
                            weekday: "short",
                            day: "numeric",
                            month: "short",
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                    </div>
                    <Button
                      className="rounded-xl font-bold px-6"
                      onClick={() => handleRideClick(ride.id)}
                    >
                      View Details
                    </Button>
                  </div>
                </CardContent>
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
          <Link href="/rides" className="flex flex-col items-center gap-1 p-2 text-primary">
            <CarIcon className="h-5 w-5" />
            <span className="text-xs">Rides</span>
          </Link>
          <Link href="/account" className="flex flex-col items-center gap-1 p-2">
            <User className="h-5 w-5" />
            <span className="text-xs">Account</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
