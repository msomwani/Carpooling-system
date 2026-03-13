"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { RefreshCcw, Activity, Database, ShieldCheck } from "lucide-react"

type ServiceStatus = "unknown" | "healthy" | "error" | "offline"

function StatusBadge({ status }: { status: ServiceStatus }) {
  if (status === "healthy") return <Badge className="bg-green-500">Online</Badge>
  if (status === "error") return <Badge variant="destructive">Component Failed</Badge>
  if (status === "offline") {
    return <Badge variant="outline" className="border-red-500 text-red-500">Backend Unreachable</Badge>
  }
  return <Badge variant="secondary">Checking...</Badge>
}

export default function HealthPage() {
  const [checks, setChecks] = useState<{
    api: ServiceStatus,
    db: ServiceStatus,
    redis: ServiceStatus,
    kafka: ServiceStatus,
    loading: boolean
  }>({
    api: "unknown",
    db: "unknown",
    redis: "unknown",
    kafka: "unknown",
    loading: true
  })

  const runChecks = async () => {
    setChecks(prev => ({ ...prev, loading: true }))
    
    try {
      // 1. Check basic API Health
      const healthRes = await fetch("/api/healthz")
      const healthData = await healthRes.json()
      
      // 2. Check Readiness (DB, Redis, Kafka)
      const readyRes = await fetch("/api/readyz")
      const readyData = await readyRes.json()

      setChecks({
        api: healthData.status === "ok" ? "healthy" : "error",
        db: readyData.status === "ready" ? "healthy" : (readyData.component === "database" ? "error" : "healthy"),
        redis: readyData.status === "ready" ? "healthy" : (readyData.component === "redis" ? "error" : "healthy"),
        kafka: readyData.status === "ready" ? "healthy" : (readyData.component === "kafka" ? "error" : "healthy"),
        loading: false
      })
    } catch {
      setChecks({ api: "offline", db: "offline", redis: "offline", kafka: "offline", loading: false })
    }
  }

  useEffect(() => {
    async function loadChecks() {
      await runChecks()
    }

    void loadChecks()
  }, [])

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">System Status</h1>
        <Button onClick={runChecks} variant="outline" size="sm" disabled={checks.loading}>
          <RefreshCcw className={`mr-2 h-4 w-4 ${checks.loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">API Gateway</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={checks.api} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">PostgreSQL</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={checks.db} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Redis Cache</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={checks.redis} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">Kafka Stream</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <StatusBadge status={checks.kafka} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
