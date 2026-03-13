"use client"

import { useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Loader2 } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    setIsLoading(true)
    setError("")

    if (!credentialResponse.credential) {
      setError("Google did not return a usable credential.")
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          id_token: credentialResponse.credential,
          role: "passenger" 
        }),
      })

      const data = await response.json()

      if (response.ok) {
        router.push("/dashboard") 
      } else {
        if (Array.isArray(data.detail)) {
          const firstError = data.detail[0]
          setError(`Backend Error: ${firstError.loc.join(" -> ")} - ${firstError.msg}`)
        } else {
          setError(data.detail || "Authentication failed")
        }
      }
    } catch {
      setError("Cannot reach the server. Make sure Docker is running.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-slate-50">
      <Card className="w-full max-w-sm shadow-2xl border-t-4 border-t-black">
        <CardHeader className="text-center pb-2">
            <div className="flex justify-center mb-2">
            <div className="relative w-12 h-12">
              <Image 
                src="/croc_mascot.png" 
                alt="Croc Ride Mascot" 
                fill
                className="object-contain"
              />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Croc Ride</CardTitle>
          <CardDescription className="text-sm">
            Vadodara <span className="text-primary mx-1">⇄</span> Halol Daily Commute
          </CardDescription>
        </CardHeader>
        
        <CardContent className="grid gap-6 pt-4">
          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              Sign in with your Google account to bypass email verification.
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription className="text-xs font-medium leading-relaxed">
                {error}
              </AlertDescription>
            </Alert>
          )}

          <div className="flex justify-center flex-col items-center gap-4 min-h-[50px]">
            {isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                <Loader2 className="h-4 w-4 animate-spin" />
                Signing you in...
              </div>
            ) : (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError("Google Login Failed. Please try again.")}
                useOneTap
                theme="filled_black"
                shape="pill"
                width="320px"
              />
            )}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-4 border-t pt-6 bg-slate-50/50">
          <p className="text-[10px] text-center text-muted-foreground uppercase tracking-widest px-6">
            Secured by Google Identity
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
