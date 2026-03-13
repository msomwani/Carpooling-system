"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Loader2, Search, Shield, Wallet, MapPin, Clock, Menu, X, Home, Car as CarIcon, User } from "lucide-react"

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
  const [rides, setRides] = useState<Ride[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [debugError, setDebugError] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

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
          <button onClick={() => setMenuOpen(!menuOpen)} className="p-2">
            <Menu className="h-6 w-6" />
          </button>
        </div>
      </header>

      {/* Side Menu */}
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setMenuOpen(false)}>
          <div className="absolute right-0 top-0 h-full w-64 bg-background shadow-lg" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 flex justify-between items-center border-b">
              <span className="font-semibold">Menu</span>
              <button onClick={() => setMenuOpen(false)}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="p-4 space-y-2">
              <Link href="/rides" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Find Rides
              </Link>
              <Link href="/rides/create" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Offer a Ride
              </Link>
              <Link href="/dashboard" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Dashboard
              </Link>
              <hr className="my-4" />
              <Link href="/login" className="block p-3 rounded-lg hover:bg-muted" onClick={() => setMenuOpen(false)}>
                Sign In
              </Link>
              <Link href="/signup" className="block p-3 rounded-lg bg-primary text-primary-foreground" onClick={() => setMenuOpen(false)}>
                Get Started
              </Link>
            </nav>
          </div>
        </div>
      )}

      <section className="py-12 lg:py-16 bg-secondary/30">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center max-w-3xl mx-auto mb-8">
            <div className="relative w-24 h-24 mx-auto mb-4">
              <Image 
                src="/croc_mascot.png" 
                alt="Croc Ride" 
                fill
                className="object-contain"
              />
            </div>
            <h1 className="text-3xl lg:text-4xl font-bold tracking-tight mb-2">
              Daily Commute, <span className="text-primary">Reimagined</span>
            </h1>
            <p className="text-muted-foreground mb-2">
              Vadodara ↔ Halol corridor
            </p>
            <p className="text-sm text-muted-foreground mb-6">
              GIDC, Fatehgunj, Gotri to Halol Industrial Area
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button size="lg" onClick={() => document.getElementById('search-rides')?.scrollIntoView({ behavior: 'smooth' })}>
                Find a Ride <Search className="ml-2 h-4 w-4" />
              </Button>
              <Link href="/rides/create">
                <Button size="lg" variant="outline" className="w-full sm:w-auto">
                  Offer a Ride
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4 mt-8">
            <div className="text-center p-4">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Wallet className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-sm">Save Money</h3>
              <p className="text-xs text-muted-foreground">Split fuel costs</p>
            </div>
            <div className="text-center p-4">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-sm">Verified Users</h3>
              <p className="text-xs text-muted-foreground">Google sign-in</p>
            </div>
            <div className="text-center p-4">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                <MapPin className="h-5 w-5 text-primary" />
              </div>
              <h3 className="font-semibold text-sm">Local Routes</h3>
              <p className="text-xs text-muted-foreground">GIDC, Halol & more</p>
            </div>
          </div>
        </div>
      </section>

      <section id="search-rides" className="py-10">
        <div className="max-w-6xl mx-auto px-4">
          <div className="text-center mb-6">
            <h2 className="text-xl font-bold">Find a Ride Now</h2>
          </div>

          <div className="flex items-center gap-2 max-w-md mx-auto mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input 
                placeholder="Search locations..." 
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Button onClick={fetchRides}>Search</Button>
          </div>

          {debugError && (
            <div className="mb-4 p-3 border rounded-lg flex items-center gap-2 max-w-4xl mx-auto text-sm">
              <Shield className="h-4 w-4" />
              {debugError}
            </div>
          )}

          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Finding rides...</p>
            </div>
          ) : searched && filteredRides.length === 0 ? (
            <Card className="p-6 text-center max-w-sm mx-auto">
              <h3 className="font-semibold text-sm">No rides found</h3>
              <p className="text-muted-foreground text-xs mt-1">Be the first to offer a ride!</p>
              <Link href="/signup">
                <Button size="sm" className="mt-3">Offer a Ride</Button>
              </Link>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredRides.slice(0, 6).map((ride) => (
                <Card key={ride.id} className="text-sm">
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-center">
                      <Badge variant="secondary" className="text-xs">{ride.available_seats} seats</Badge>
                      <span className="text-xs text-muted-foreground">{ride.status}</span>
                    </div>
                    <CardTitle className="text-sm font-bold flex flex-col gap-1 mt-2">
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3 w-3 text-primary" />
                        {ride.source}
                      </div>
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3 w-3 text-destructive" />
                        {ride.destination}
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-xs text-muted-foreground pb-2">
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(ride.departure_time).toLocaleString("en-IN", {
                        day: "numeric",
                        month: "short",
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </div>
                  </CardContent>
                  <CardFooter className="pt-0">
                    <Button 
                      className="w-full text-xs" 
                      size="sm"
                      onClick={() => router.push('/login')}
                    >
                      Login to Book
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Bottom Navigation for Mobile */}
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t md:hidden">
        <div className="flex justify-around items-center h-16">
          <Link href="/" className="flex flex-col items-center gap-1 p-2 text-primary">
            <Home className="h-5 w-5" />
            <span className="text-xs">Home</span>
          </Link>
          <Link href="/rides" className="flex flex-col items-center gap-1 p-2">
            <CarIcon className="h-5 w-5" />
            <span className="text-xs">Rides</span>
          </Link>
          <Link href="/login" className="flex flex-col items-center gap-1 p-2">
            <User className="h-5 w-5" />
            <span className="text-xs">Account</span>
          </Link>
        </div>
      </div>
    </div>
  )
}
