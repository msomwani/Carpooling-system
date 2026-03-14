// "use client"

// import { useEffect, useRef, useState } from "react"
// import { Loader2 } from "lucide-react"

// interface GoogleMapProps {
//   apiKey: string
//   center?: { lat: number; lng: number }
//   zoom?: number
// }

// export function GoogleMap({ apiKey, center = { lat: 22.3072, lng: 73.1812 }, zoom = 12 }: GoogleMapProps) {
//   const mapRef = useRef<HTMLDivElement>(null)
//   const [isLoading, setIsLoading] = useState(true)
//   const [error, setError] = useState<string | null>(null)
//   const [isMounted, setIsMounted] = useState(false)

//   useEffect(() => {
//     setIsMounted(true)
//   }, [])

//   useEffect(() => {
//     if (!isMounted || !apiKey) {
//       if (!apiKey && isMounted) setError("API Key is missing")
//       return
//     }

//     const loadMap = () => {
//       const scriptId = "google-maps-script"
//       let script = document.getElementById(scriptId) as HTMLScriptElement

//       const initMap = () => {
//         if (mapRef.current && window.google) {
//           try {
//             new window.google.maps.Map(mapRef.current, {
//               center,
//               zoom,
//               disableDefaultUI: true,
//               styles: [
//                 {
//                   featureType: "poi",
//                   elementType: "labels",
//                   stylers: [{ visibility: "off" }],
//                 },
//               ],
//             })
//             setIsLoading(false)
//             setError(null)
//           } catch (err) {
//             console.error("Error initializing map:", err)
//             setError("Failed to initialize map")
//             setIsLoading(false)
//           }
//         }
//       }

//       if (!window.google) {
//         if (!script) {
//           script = document.createElement("script")
//           script.id = scriptId
//           script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`
//           script.async = true
//           script.defer = true
//           script.onload = initMap
//           script.onerror = () => {
//             setError("Failed to load Google Maps script")
//             setIsLoading(false)
//           }
//           document.head.appendChild(script)
//         } else {
//           // Script is already there but google not loaded yet, wait for it
//           script.addEventListener('load', initMap)
//         }
//       } else {
//         initMap()
//       }
//     }

//     loadMap()
//   }, [apiKey, center, zoom, isMounted])

//   if (!isMounted) return <div className="w-full h-full min-h-[300px] bg-muted animate-pulse rounded-2xl" />

//   return (
//     <div className="relative w-full h-full min-h-[300px] bg-muted rounded-2xl overflow-hidden shadow-inner">
//       {isLoading && !error && (
//         <div className="absolute inset-0 flex items-center justify-center bg-muted/50 z-10">
//           <Loader2 className="h-8 w-8 animate-spin text-primary" />
//         </div>
//       )}
//       {error && (
//         <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center z-20 bg-muted/90">
//           <p className="text-sm text-destructive font-bold mb-2">Map Error</p>
//           <p className="text-xs text-muted-foreground">{error}</p>
//         </div>
//       )}
//       <div ref={mapRef} className="w-full h-full" />
//     </div>
//   )
// }

// declare global {
//   interface Window {
//     google: any
//   }
// }

"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2 } from "lucide-react"
import L from "leaflet"
import "leaflet/dist/leaflet.css" // Required for the map to render correctly

interface OpenMapProps {
  center?: { lat: number; lng: number }
  zoom?: number
}

// I kept your default coordinates which map to the Vadodara/Godhra region!
export function OpenMap({ center = { lat: 22.3072, lng: 73.1812 }, zoom = 12 }: OpenMapProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Ensure this only runs on the client and the map container exists
    if (typeof window !== "undefined" && mapRef.current && !mapInstanceRef.current) {

      // 1. Initialize the Leaflet map
      const map = L.map(mapRef.current, {
        zoomControl: false, // You can enable this if you want +/- buttons
      }).setView([center.lat, center.lng], zoom)

      // 2. Add the free OpenStreetMap tiles
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map)

      // Store the instance and remove loading state
      mapInstanceRef.current = map
      setIsLoading(false)
    }

    // 3. Cleanup function for Next.js strict mode / unmounting
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [center.lat, center.lng, zoom])

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