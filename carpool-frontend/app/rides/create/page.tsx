"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import Image from "next/image"
import { CORRIDOR_STOPS } from "@/lib/locations"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2, ArrowLeft, MapPin, Calendar, Users, Car } from "lucide-react"
import { useAuth } from "@/lib/AuthContext"
import "leaflet/dist/leaflet.css"
import dynamic from "next/dynamic"

const fetchAddress = async (lat: number, lng: number): Promise<string> => {
  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`, {
      headers: { "Accept-Language": "en" }
    })
    const data = await response.json()
    const address = data.address
    const name = address.road || address.village || address.suburb || address.city || address.county || "Unnamed Location"
    const number = address.house_number ? `${address.house_number}, ` : ""
    return `${number}${name}`
  } catch (error) {
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`
  }
}

function CreateRideContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { getAuthHeaders } = useAuth()
  const LeafletRef = useRef<any>(null)
  const [apiKey, setApiKey] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [mapError, setMapError] = useState<string | null>(null)
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<any>(null)
  const sourceMarkerRef = useRef<any>(null)
  const destMarkerRef = useRef<any>(null)
  const routeLayerRef = useRef<any>(null)

  const [vehicles, setVehicles] = useState<any[]>([])
  const [selectedVehicleId, setSelectedVehicleId] = useState("")
  const [routeGeometry, setRouteGeometry] = useState<any>(null)
  const [selectionMode, setSelectionMode] = useState<"source" | "destination">("source")
  const [showSourceDropdown, setShowSourceDropdown] = useState(false)
  const [showDestDropdown, setShowDestDropdown] = useState(false)
  const sourceContainerRef = useRef<HTMLDivElement>(null)
  const destContainerRef = useRef<HTMLDivElement>(null)
  const selectionRef = useRef(selectionMode)

  useEffect(() => {
    selectionRef.current = selectionMode
  }, [selectionMode])

  const [formData, setFormData] = useState({
    source: "",
    destination: "",
    departure_time: "",
    total_seats: 4,
    price_per_seat: 100,
    source_lat: 0,
    source_lng: 0,
    destination_lat: 0,
    destination_lng: 0,
  })

  useEffect(() => {
    // Fetch vehicles
    const fetchVehicles = async () => {
      try {
        const res = await fetch("/api/vehicles/me", { headers: getAuthHeaders(), credentials: "include" })
        if (res.ok) {
          const data = await res.json()
          setVehicles(data)
          if (data.length > 0) setSelectedVehicleId(data[0].id)
        }
      } catch (err) {
        console.error("Failed to load vehicles")
      }
    }
    fetchVehicles()

    // Check for query params to pre-fill
    const pSource = searchParams.get("source")
    const pDest = searchParams.get("destination")
    const pSLat = searchParams.get("source_lat")
    const pSLng = searchParams.get("source_lng")
    const pDLat = searchParams.get("destination_lat")
    const pDLng = searchParams.get("destination_lng")
    const pSeats = searchParams.get("seats")
    const pPrice = searchParams.get("price")
    const pVehicle = searchParams.get("vehicle_id")

    if (pSource || pDest || pSLat || pDLat) {
      setFormData(prev => ({
        ...prev,
        source: pSource || prev.source,
        destination: pDest || prev.destination,
        source_lat: pSLat ? parseFloat(pSLat) : prev.source_lat,
        source_lng: pSLng ? parseFloat(pSLng) : prev.source_lng,
        destination_lat: pDLat ? parseFloat(pDLat) : prev.destination_lat,
        destination_lng: pDLng ? parseFloat(pDLng) : prev.destination_lng,
        total_seats: pSeats ? parseInt(pSeats) : prev.total_seats,
        price_per_seat: pPrice ? parseInt(pPrice) : prev.price_per_seat,
      }))
      if (pVehicle) setSelectedVehicleId(pVehicle)
    }

    // Init Leaflet Map
    if (typeof window !== "undefined" && mapRef.current && !mapInstanceRef.current) {
      const L = require("leaflet")
      LeafletRef.current = L

      const initialLat = pSLat ? parseFloat(pSLat) : 22.3072
      const initialLng = pSLng ? parseFloat(pSLng) : 73.1812
      
      const map = L.map(mapRef.current, {
        zoomControl: true,
      }).setView([initialLat, initialLng], 11)

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map)

      // Pre-add markers if coordinates exist
      if (pSLat && pSLng) {
        sourceMarkerRef.current = L.marker([parseFloat(pSLat), parseFloat(pSLng)], {
          icon: L.divIcon({
            className: 'custom-div-icon',
            html: "<div style='background-color:#15803d; width:24px; height:24px; border-radius:50%; border:2px solid white; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:10px;'>S</div>",
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          })
        }).addTo(map)
      }

      if (pDLat && pDLng) {
        destMarkerRef.current = L.marker([parseFloat(pDLat), parseFloat(pDLng)], {
          icon: L.divIcon({
            className: 'custom-div-icon',
            html: "<div style='background-color:#dc2626; width:24px; height:24px; border-radius:50%; border:2px solid white; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:10px;'>D</div>",
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          })
        }).addTo(map)
        
        // Fit bounds if both markers exist
        if (pSLat && pSLng) {
           map.fitBounds(L.latLngBounds([parseFloat(pSLat), parseFloat(pSLng)], [parseFloat(pDLat), parseFloat(pDLng)]), { padding: [50, 50] })
        }
      }

      map.on("click", (e: any) => {
        const { lat, lng } = e.latlng
        if (selectionRef.current === "source") {
          handleSetSource(lat, lng)
        } else {
          handleSetDest(lat, lng)
        }
      })

      mapInstanceRef.current = map
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (sourceContainerRef.current && !sourceContainerRef.current.contains(event.target as Node)) {
        setShowSourceDropdown(false)
      }
      if (destContainerRef.current && !destContainerRef.current.contains(event.target as Node)) {
        setShowDestDropdown(false)
      }
    }

    if (typeof window !== "undefined") {
       document.addEventListener("mousedown", handleClickOutside)
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
      if (typeof window !== "undefined") {
        document.removeEventListener("mousedown", handleClickOutside)
      }
    }
  }, []) // Initialize only once

  // Separate effect for route fetching
  useEffect(() => {
    if (formData.source_lat && formData.destination_lat) {
      fetchRoute(formData.source_lat, formData.source_lng, formData.destination_lat, formData.destination_lng)
    }
  }, [formData.source_lat, formData.source_lng, formData.destination_lat, formData.destination_lng])
 
  const fetchRoute = async (sLat: number, sLng: number, dLat: number, dLng: number) => {
    try {
      const response = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${sLng},${sLat};${dLng},${dLat}?overview=full&geometries=geojson`
      )
      const data = await response.json()
      if (data.routes && data.routes.length > 0) {
        const route = data.routes[0].geometry
        setRouteGeometry(route)
        drawRoute(route)
      }
    } catch (err) {
      console.error("Failed to fetch route", err)
    }
  }
 
  const drawRoute = (geometry: any) => {
    const L = LeafletRef.current
    const map = mapInstanceRef.current
    if (!L || !map || !geometry) return
 
    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current)
    }
 
    // OSRM GeoJSON gives [lng, lat], Leaflet needs [lat, lng]
    const latLngs = geometry.coordinates.map((c: any) => [c[1], c[0]])
    
    routeLayerRef.current = L.polyline(latLngs, {
      color: "#15803d", // primary green
      weight: 5,
      opacity: 0.7,
      lineJoin: "round",
      className: "animate-draw-route" // Custom CSS could be added for animation
    }).addTo(map)
  }

  const handleSetSource = async (lat: number, lng: number, name?: string) => {
    let displayName = name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`

    setFormData(prev => ({
      ...prev,
      source: displayName,
      source_lat: lat,
      source_lng: lng
    }))

    const L = LeafletRef.current
    if (!L || !mapInstanceRef.current) return

    if (sourceMarkerRef.current && sourceMarkerRef.current.getElement?.()) {
      sourceMarkerRef.current.setLatLng([lat, lng])
    } else {
      if (sourceMarkerRef.current) {
        try { sourceMarkerRef.current.remove() } catch (e) {}
      }
      sourceMarkerRef.current = L.marker([lat, lng], {
        icon: L.divIcon({
          className: 'custom-div-icon',
          html: "<div style='background-color:#15803d; width:24px; height:24px; border-radius:50%; border:2px solid white; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:10px;'>S</div>",
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        })
      }).addTo(mapInstanceRef.current)
    }

    if (!name) {
      const address = await fetchAddress(lat, lng)
      setFormData(prev => ({ ...prev, source: address }))
    }
  }

  const handleSetDest = async (lat: number, lng: number, name?: string) => {
    let displayName = name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`

    setFormData(prev => ({
      ...prev,
      destination: displayName,
      destination_lat: lat,
      destination_lng: lng
    }))

    const L = LeafletRef.current
    if (!L || !mapInstanceRef.current) return

    if (destMarkerRef.current && destMarkerRef.current.getElement?.()) {
      destMarkerRef.current.setLatLng([lat, lng])
    } else {
      if (destMarkerRef.current) {
        try { destMarkerRef.current.remove() } catch (e) {}
      }
      destMarkerRef.current = L.marker([lat, lng], {
        icon: L.divIcon({
          className: 'custom-div-icon',
          html: "<div style='background-color:#dc2626; width:24px; height:24px; border-radius:50%; border:2px solid white; display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:10px;'>D</div>",
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        })
      }).addTo(mapInstanceRef.current)
    }

    if (!name) {
      const address = await fetchAddress(lat, lng)
      setFormData(prev => ({ ...prev, destination: address }))
    }
  }

  const handleSelectStop = (stopName: string, isSource: boolean) => {
    const stop = CORRIDOR_STOPS.find(s => s.name === stopName)
    if (!stop) return

    if (isSource) {
      handleSetSource(stop.lat, stop.lng, stopName)
      setShowSourceDropdown(false)
    } else {
      handleSetDest(stop.lat, stop.lng, stopName)
      setShowDestDropdown(false)
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
      price_per_seat: Number(formData.price_per_seat),
      vehicle_id: selectedVehicleId,
      route_geometry: routeGeometry ? `LINESTRING(${routeGeometry.coordinates.map((c: any) => `${c[0]} ${c[1]}`).join(", ")})` : null
    }

    try {
      const response = await fetch("/api/rides/", {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
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
              <div className="relative w-12 h-12">
                <Image src="/croc_mascot(y).png" alt="Croc" fill sizes="48px" className="object-contain" />
              </div>
            </Link>
            <Link href="/">
              <span className="font-bold text-xl">Croc Ride</span>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Offer a Ride</CardTitle>
              <CardDescription>Vadodara to Halol Corridor</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="grid gap-4">
                {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

                <div
                  ref={sourceContainerRef}
                  className={`grid gap-2 p-3 rounded-2xl transition-all border-2 ${selectionMode === "source" ? "border-primary bg-primary/5 shadow-md" : "border-transparent hover:bg-muted/50"}`}
                  onClick={() => {
                    setSelectionMode("source")
                    setShowSourceDropdown(true)
                  }}
                >
                  <Label className="flex items-center gap-2 cursor-pointer mb-1">
                    <div className={`w-2.5 h-2.5 rounded-full ${selectionMode === "source" ? "bg-primary animate-pulse shadow-[0_0_8px_rgba(21,128,61,0.5)]" : "bg-muted-foreground/30"}`} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Pickup Point</span>
                  </Label>
                  <div className="relative">
                    <Input
                      className="h-12 rounded-xl border-none bg-background shadow-inner px-4 text-sm font-bold focus-visible:ring-0 placeholder:text-muted-foreground/40 placeholder:font-medium"
                      required
                      placeholder="Tap map or search stop..."
                      value={formData.source}
                      onChange={(e) => {
                        setFormData({ ...formData, source: e.target.value })
                        setShowSourceDropdown(true)
                      }}
                      onFocus={() => {
                        setSelectionMode("source")
                        setShowSourceDropdown(true)
                      }}
                    />
                    {showSourceDropdown && !formData.source.includes(",") && (
                      <div className="absolute left-0 right-0 top-full mt-2 z-50 max-h-48 overflow-y-auto bg-background rounded-2xl border shadow-2xl p-1.5 animate-in slide-in-from-top-2 duration-200">
                        {CORRIDOR_STOPS.filter(s => s.name.toLowerCase().includes(formData.source.toLowerCase()) || formData.source === "").map(stop => (
                          <button
                            key={stop.name}
                            type="button"
                            className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-primary/10 hover:text-primary text-[11px] font-bold transition-colors flex items-center gap-2"
                            onClick={() => handleSelectStop(stop.name, true)}
                          >
                            <MapPin className="h-3 w-3 opacity-40" />
                            {stop.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div
                  ref={destContainerRef}
                  className={`grid gap-2 p-3 rounded-2xl transition-all border-2 ${selectionMode === "destination" ? "border-destructive bg-destructive/5 shadow-md" : "border-transparent hover:bg-muted/50"}`}
                  onClick={() => {
                    setSelectionMode("destination")
                    setShowDestDropdown(true)
                  }}
                >
                  <Label className="flex items-center gap-2 cursor-pointer mb-1">
                    <div className={`w-2.5 h-2.5 rounded-full ${selectionMode === "destination" ? "bg-destructive animate-pulse shadow-[0_0_8px_rgba(220,38,38,0.5)]" : "bg-muted-foreground/30"}`} />
                    <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Drop-off Point</span>
                  </Label>
                  <div className="relative">
                    <Input
                      className="h-12 rounded-xl border-none bg-background shadow-inner px-4 text-sm font-bold focus-visible:ring-0 placeholder:text-muted-foreground/40 placeholder:font-medium"
                      required
                      placeholder="Tap map or search stop..."
                      value={formData.destination}
                      onChange={(e) => {
                        setFormData({ ...formData, destination: e.target.value })
                        setShowDestDropdown(true)
                      }}
                      onFocus={() => {
                        setSelectionMode("destination")
                        setShowDestDropdown(true)
                      }}
                    />
                    {showDestDropdown && !formData.destination.includes(",") && (
                      <div className="absolute left-0 right-0 top-full mt-2 z-50 max-h-48 overflow-y-auto bg-background rounded-2xl border shadow-2xl p-1.5 animate-in slide-in-from-top-2 duration-200">
                        {CORRIDOR_STOPS.filter(s => s.name.toLowerCase().includes(formData.destination.toLowerCase()) || formData.destination === "").map(stop => (
                          <button
                            key={stop.name}
                            type="button"
                            className="w-full text-left px-4 py-2.5 rounded-xl hover:bg-destructive/10 hover:text-destructive text-[11px] font-bold transition-colors flex items-center gap-2"
                            onClick={() => handleSelectStop(stop.name, false)}
                          >
                            <MapPin className="h-3 w-3 opacity-40" />
                            {stop.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label>Departure Time</Label>
                  <Input
                    type="datetime-local"
                    required
                    onChange={(e) => setFormData({ ...formData, departure_time: e.target.value })}
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Seats Available</Label>
                  <Input
                    type="number"
                    min="1"
                    max="7"
                    defaultValue="4"
                    onChange={(e) => setFormData({ ...formData, total_seats: parseInt(e.target.value) })}
                  />
                </div>

                <div className="grid gap-2">
                  <Label>Price per Seat (₹)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.price_per_seat}
                    onChange={(e) => setFormData({ ...formData, price_per_seat: parseInt(e.target.value) })}
                  />
                </div>

                <div className="grid gap-2">
                  <Label className="flex items-center gap-2">
                    <Car className="h-4 w-4" /> Select Vehicle
                  </Label>
                  {vehicles.length === 0 ? (
                    <div className="p-4 rounded-xl border-2 border-dashed border-muted bg-muted/5 flex flex-col items-center gap-2 text-center">
                      <p className="text-xs text-muted-foreground font-medium">No vehicles registered</p>
                      <Link href="/account">
                        <Button type="button" variant="outline" size="sm" className="h-8 rounded-lg text-[10px] font-black uppercase tracking-wider">
                          Register Vehicle
                        </Button>
                      </Link>
                    </div>
                  ) : (
                    <select
                      className="flex h-11 w-full rounded-xl border-2 border-muted bg-background px-4 py-2 text-sm font-bold focus:border-primary transition-colors outline-none appearance-none"
                      required
                      value={selectedVehicleId}
                      onChange={(e) => setSelectedVehicleId(e.target.value)}
                    >
                      <option value="" disabled>Choose your car/bike...</option>
                      {vehicles.map(v => (
                        <option key={v.id} value={v.id}>
                          {v.make} {v.model} ({v.license_plate})
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <Button type="submit" disabled={isLoading || !selectedVehicleId} className="w-full h-12 rounded-xl font-black text-sm uppercase tracking-widest shadow-lg shadow-primary/20 transition-all active:scale-[0.98]">
                  {isLoading ? <Loader2 className="animate-spin mr-2 h-4 w-4" /> : null}
                  Publish Ride
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="rounded-[2.5rem] border shadow-sm overflow-hidden bg-background flex flex-col">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg font-black tracking-tight">
                <MapPin className="h-5 w-5 text-primary" />
                Tap to Set Location
              </CardTitle>
              <CardDescription className="text-xs font-medium">
                {formData.source ? <span className="text-primary font-bold">{formData.source}</span> : "Set pickup"}
                {formData.source && formData.destination && <span className="mx-2 opacity-50">→</span>}
                {formData.destination ? <span className="text-destructive font-bold">{formData.destination}</span> : "Set destination"}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 p-0 relative min-h-[400px]">
              <div ref={mapRef} className="absolute inset-0 z-10" />

              {/* Map Selection Toggle Overlay */}
              <div className="absolute top-4 left-4 right-4 z-20 flex justify-center">
                <div className="bg-background/90 backdrop-blur-md p-1.5 rounded-2xl border shadow-xl flex gap-1">
                  <button
                    type="button"
                    onClick={() => setSelectionMode("source")}
                    className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${selectionMode === "source"
                      ? "bg-primary text-white shadow-lg shadow-primary/20"
                      : "text-muted-foreground hover:bg-muted"
                      }`}
                  >
                    Set Pickup
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectionMode("destination")}
                    className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${selectionMode === "destination"
                      ? "bg-destructive text-white shadow-lg shadow-destructive/20"
                      : "text-muted-foreground hover:bg-muted"
                      }`}
                  >
                    Set Drop-off
                  </button>
                </div>
              </div>

              {mapError && (
                <div className="absolute bottom-4 left-4 right-4 z-20">
                  <Alert variant="destructive" className="rounded-2xl border-none shadow-xl bg-destructive/90 text-white backdrop-blur-md">
                    <AlertDescription className="text-[10px] font-bold uppercase tracking-widest">{mapError}</AlertDescription>
                  </Alert>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default dynamic(() => Promise.resolve(CreateRideContent), { ssr: false })
