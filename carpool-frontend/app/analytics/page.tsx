"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, TrendingUp, Users, Car, Calendar, DollarSign, Activity, Route, XCircle, CheckCircle } from "lucide-react"

type AnalyticsOverview = {
  window_days: number
  total_bookings: number
  cancellation_rate: number
  seat_utilization: number
  popular_routes: {
    source: string
    destination: string
    bookings: number
  }[]
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const fetchAnalytics = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/analytics/overview?days=${days}`)

      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      } else {
        const errorData = await response.json().catch(() => null)
        setError(`Error: ${JSON.stringify(errorData)}`)
      }
    } catch (error) {
      setError("Cannot connect to server.")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [days])

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b sticky top-0 bg-background">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="relative w-10 h-10">
                <Image
                  src="/croc_mascot(y).png"
                  alt="Croc Ride Mascot"
                  fill
                  sizes="40px"
                  className="object-contain"
                />
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
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">Analytics</h1>
            <p className="text-muted-foreground">Platform performance overview</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <Button variant="outline" onClick={fetchAnalytics}>
              Refresh
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive rounded-lg text-destructive">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading analytics...</p>
          </div>
        ) : analytics ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Bookings</CardTitle>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{analytics.total_bookings}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Last {analytics.window_days} days
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Cancellation Rate</CardTitle>
                  <XCircle className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{(analytics.cancellation_rate * 100).toFixed(1)}%</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Of all bookings
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Seat Utilization</CardTitle>
                  <Users className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{(analytics.seat_utilization * 100).toFixed(1)}%</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Of available seats
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Popular Routes</CardTitle>
                  <Route className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{analytics.popular_routes.length}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Top routes
                  </p>
                </CardContent>
              </Card>
            </div>

            {analytics.popular_routes.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Popular Routes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {analytics.popular_routes.map((route, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center text-sm font-bold text-primary">
                            {idx + 1}
                          </div>
                          <div>
                            <p className="font-medium">{route.source} → {route.destination}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-primary" />
                          <span className="font-semibold">{route.bookings} bookings</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {analytics.total_bookings === 0 && (
              <Card className="p-12 text-center">
                <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                  <Activity className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold">No data yet</h3>
                <p className="text-muted-foreground text-sm mt-1">
                  Analytics will appear here once there are bookings on the platform.
                </p>
              </Card>
            )}
          </div>
        ) : (
          <Card className="p-12 text-center">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <Activity className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No data available</h3>
          </Card>
        )}
      </div>
    </div>
  )
}
