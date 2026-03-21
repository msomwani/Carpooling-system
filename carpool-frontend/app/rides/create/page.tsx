"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import Image from "next/image"
import { CORRIDOR_STOPS } from "@/lib/locations"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, ArrowLeft, MapPin, Calendar, Users } from "lucide-react"
import { useAuth } from "@/lib/AuthContext"

type GoogleMap = any
type GoogleMarker = any
let google: any

export default function CreateRidePage() {
  const router = useRouter()
  const { getAuthHeaders } = useAuth()
  const [apiKey, setApiKey] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [mapError, setMapError] = useState<string | null>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<GoogleMap | null>(null)
  const sourceMarkerRef = useRef<GoogleMarker | null>(null)
  const destMarkerRef = useRef<GoogleMarker | null>(null)
  
  const [formData, setFormData] = useState({
    source: "",
    destination: "",
    departure_time: "",
    total_seats: 4,
    source_lat: 0,
    source_lng: 0,
    destination_lat: 0,
    destination_lng: 0,
  })

  useEffect(() => {
    if (typeof window === 'undefined' || (window as any).google) return
    
    const loadMap = async () => {
      try {
        const res = await fetch("/api/maps/api-key")
        const data = await res.json()
        if (data.api_key) {
          setApiKey(data.api_key)
          initGoogleMaps(data.api_key)
        }
      } catch (e) {
        setMapError("Failed to load Google Maps API key")
      }
    }
    loadMap()
  }, [])

  const initGoogleMaps = (key: string) => {
    if (!mapRef.current) return
    if ((window as any).google) return
    
    const script = document.createElement("script")
    script.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places`
    script.async = true
    script.defer = true
    script.onload = () => {
      if (!mapRef.current) return
      
      google = (window as any).google
      
      const map = new google.maps.Map(mapRef.current, {
        center: { lat: 22.38, lng: 73.32 },
        zoom: 11,
      })
      mapInstanceRef.current = map

      map.addListener("click", (e: any) => {
        if (!e.latLng) return
        const lat = e.latLng.lat()
        const lng = e.latLng.lng()
        
        if (!formData.source || (formData.source && formData.destination)) {
          handleSetSource(lat, lng)
        } else {
          handleSetDest(lat, lng)
        }
      })
    }
    document.head.appendChild(script)
  }

  const handleSetSource = (lat: number, lng: number) => {
    setFormData(prev => ({
      ...prev,
      source: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
      source_lat: lat,
      source_lng: lng
    }))
    
    if (sourceMarkerRef.current) {
      sourceMarkerRef.current.setPosition({ lat, lng })
    } else if (mapInstanceRef.current) {
      sourceMarkerRef.current = new google.maps.Marker({
        position: { lat, lng },
        map: mapInstanceRef.current,
        label: "S",
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 12,
          fillColor: "#15803d",
          fillOpacity: 1,
          strokeColor: "#fff",
          strokeWeight: 2,
        }
      })
    }
  }

  const handleSetDest = (lat: number, lng: number) => {
    setFormData(prev => ({
      ...prev,
      destination: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
      destination_lat: lat,
      destination_lng: lng
    }))
    
    if (destMarkerRef.current) {
      destMarkerRef.current.setPosition({ lat, lng })
    } else if (mapInstanceRef.current) {
      destMarkerRef.current = new google.maps.Marker({
        position: { lat, lng },
        map: mapInstanceRef.current,
        label: "D",
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 12,
          fillColor: "#dc2626",
          fillOpacity: 1,
          strokeColor: "#fff",
          strokeWeight: 2,
        }
      })
    }
  }

  const handleSelectStop = (stopName: string, isSource: boolean) => {
    const stop = CORRIDOR_STOPS.find(s => s.name === stopName)
    if (!stop) return
    
    if (isSource) {
      handleSetSource(stop.lat, stop.lng)
      setFormData(prev => ({ ...prev, source: stopName }))
    } else {
      handleSetDest(stop.lat, stop.lng)
      setFormData(prev => ({ ...prev, destination: stopName }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    const payload = {
      source: formData.source,
      source_lat: formData.source_lat,
      source_lng: formData.source_lng,
      destination: formData.destination,
      destination_lat: formData.destination_lat,
      destination_lng: formData.destination_lng,
      departure_time: new Date(formData.departure_time).toISOString(),
      total_seats: Number(formData.total_seats),
    }

    try {
      const response = await fetch("/api/rides/", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      })

      if (response.ok) {
        router.push("/bookings")
      } else {
        const data = await response.json()
        setError(data.detail || "Failed to create ride.")
      }
    } catch {
      setError("Backend connection failed.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b sticky top-0 bg-background">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="relative w-10 h-10">
                <Image src="/croc_mascot.png" alt="Croc" fill className="object-contain" />
              </div>
            </Link>
            <Link href="/">
              <span className="font-bold text-xl">Croc Ride</span>
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/rides">
              <Button variant="ghost" size="sm">Rides</Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        <div className="mb-6">
          <Link href="/rides" className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1">
            <ArrowLeft className="h-4 w-4" /> Back to Rides
          </Link>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Offer a Ride</CardTitle>
              <CardDescription>Vadodara to Halol Corridor</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="grid gap-4">
                {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

                <div className="grid gap-2">
                  <Label>Pickup Point</Label>
                  <select 
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                    value={formData.source}
                    onChange={(e) => handleSelectStop(e.target.value, true)}
                  >
                    <option value="">Select location...</option>
                    {CORRIDOR_STOPS.map(stop => (
                      <option key={stop.name} value={stop.name}>{stop.name}</option>
                    ))}
                  </select>
                </div>

                <div className="grid gap-2">
                  <Label>Drop-off Point</Label>
                  <select 
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                    value={formData.destination}
                    onChange={(e) => handleSelectStop(e.target.value, false)}
                  >
                    <option value="">Select location...</option>
                    {CORRIDOR_STOPS.map(stop => (
                      <option key={stop.name} value={stop.name}>{stop.name}</option>
                    ))}
                  </select>
                </div>

                <div className="grid gap-2">
                  <Label>Departure Time</Label>
                  <Input 
                    type="datetime-local" 
                    required 
                    onChange={(e) => setFormData({...formData, departure_time: e.target.value})} 
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Seats Available</Label>
                  <Input 
                    type="number" 
                    min="1" 
                    max="8" 
                    defaultValue="4" 
                    onChange={(e) => setFormData({...formData, total_seats: parseInt(e.target.value)})} 
                  />
                </div>

                <Button type="submit" disabled={isLoading} className="w-full">
                  {isLoading ? <Loader2 className="animate-spin mr-2" /> : null}
                  Publish Ride
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" /> 
                Click on Map to Set Location
              </CardTitle>
              <CardDescription>
                {formData.source ? `Source: ${formData.source}` : "Click to set pickup"} 
                {formData.source && formData.destination && " → "}
                {formData.destination ? `Destination: ${formData.destination}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!apiKey ? (
                <div className="h-[400px] bg-muted flex items-center justify-center rounded-lg">
                  <p className="text-muted-foreground">Loading map...</p>
                </div>
              ) : (
                <div ref={mapRef} className="h-[400px] w-full rounded-lg" />
              )}
              {mapError && (
                <Alert className="mt-4">
                  <AlertDescription>{mapError}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
