
"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2 } from "lucide-react"
import L from "leaflet"
import "leaflet/dist/leaflet.css" // Required for the map to render correctly

interface OpenMapProps {
  center?: { lat: number; lng: number }
  zoom?: number
  pickup?: { lat: number; lng: number }
  dropoff?: { lat: number; lng: number }
  route?: string // WKT string: "LINESTRING(lng lat, lng lat, ...)"
}

const parseWKT = (wkt: string): [number, number][] => {
  if (!wkt) return []
  const cleanWkt = wkt.trim().toUpperCase()
  if (!cleanWkt.includes("LINESTRING")) return []
  
  try {
    const coordsStr = wkt.substring(wkt.indexOf("(") + 1, wkt.lastIndexOf(")"))
    return coordsStr.split(",").map(pair => {
      const parts = pair.trim().split(/\s+/)
      if (parts.length < 2) return null
      const [lng, lat] = parts.map(Number)
      if (isNaN(lat) || isNaN(lng)) return null
      return [lat, lng] as [number, number]
    }).filter((p): p is [number, number] => p !== null)
  } catch (e) {
    console.error("Error parsing WKT:", e)
    return []
  }
}

export function OpenMap({ 
  center = { lat: 22.3072, lng: 73.1812 }, 
  zoom = 12,
  pickup,
  dropoff,
  route
}: OpenMapProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Initialize map only once
    if (typeof window !== "undefined" && mapRef.current && !mapInstanceRef.current) {
      console.log("DEBUG: Initializing Leaflet map");
      const map = L.map(mapRef.current, {
        zoomControl: false,
      }).setView([center.lat, center.lng], zoom)

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map)

      mapInstanceRef.current = map
      setIsLoading(false)
    }

    return () => {
      if (mapInstanceRef.current) {
        console.log("DEBUG: Removing Leaflet map");
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, []) // Empty dependency array: init once

  useEffect(() => {
    // Update markers and bounds when props change
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear existing markers and polylines
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.FeatureGroup) {
        if (!(layer instanceof L.TileLayer)) {
          map.removeLayer(layer);
        }
      }
    });

    const markers: L.Marker[] = []
    
    if (pickup) {
      const pickupIcon = L.divIcon({
        className: 'custom-div-icon',
        html: '<div style="background-color: #15803d; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
      });
      const pickupMarker = L.marker([pickup.lat, pickup.lng], { icon: pickupIcon }).addTo(map)
      markers.push(pickupMarker)
    }

    if (dropoff) {
      const dropoffIcon = L.divIcon({
        className: 'custom-div-icon',
        html: '<div style="background-color: #ef4444; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.3);"></div>',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
      });
      const dropoffMarker = L.marker([dropoff.lat, dropoff.lng], { icon: dropoffIcon }).addTo(map)
      markers.push(dropoffMarker)
    }

    let routeLayer: L.Polyline | null = null
    if (route) {
      const latLngs = parseWKT(route)
      if (latLngs.length > 0) {
        routeLayer = L.polyline(latLngs, {
          color: "#2563eb", // Brighter blue for better visibility
          weight: 5,
          opacity: 0.8,
          lineJoin: "round"
        }).addTo(map)
      }
    }

    if (markers.length > 0 || routeLayer) {
      const items: (L.Layer)[] = [...markers]
      if (routeLayer) items.push(routeLayer)
      const group = L.featureGroup(items)
      map.fitBounds(group.getBounds().pad(0.3), { animate: false })
    } else if (center) {
      map.setView([center.lat, center.lng], zoom, { animate: false })
    }
  }, [center.lat, center.lng, zoom, pickup, dropoff, route])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize()
      }
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="relative w-full h-full min-h-[300px] bg-muted rounded-2xl overflow-hidden shadow-inner">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted/50 z-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
      {/* z-10 ensures the map stays behind your loading overlay */}
      <div ref={mapRef} className="w-full h-full z-10" />
    </div>
  )
}