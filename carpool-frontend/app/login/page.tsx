"use client"

import { useRef, useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { GoogleLogin, CredentialResponse } from "@react-oauth/google"
import { useAuth } from "@/lib/AuthContext"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Loader2, LogOut, User as UserIcon, Mail } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function LoginPage() {
  const router = useRouter()
  const { user, logout, isLoading: authLoading, login } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  // Hidden ref to trigger Google's own button programmatically
  const googleBtnRef = useRef<HTMLDivElement>(null)

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    setIsLoading(true)
    setError("")
    try {
      const idToken = credentialResponse.credential
      if (!idToken) throw new Error("No credential received from Google")

      // Temporary debug hook so we can copy the Google ID token for Swagger screenshots.
      if (typeof window !== "undefined") {
        sessionStorage.setItem("debug_google_id_token", idToken)
        ;(window as Window & { __debugGoogleIdToken?: string }).__debugGoogleIdToken = idToken
        console.log("Google ID token:", idToken)
      }

      // Sync with our FastAPI backend — sends the Google id_token for verification
      const syncRes = await fetch(`${API_URL}/auth/sync-google-user`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // required so browser stores the HTTP-only cookie
        body: JSON.stringify({ id_token: idToken, role: "passenger" }),
      })
      if (!syncRes.ok) {
        const errBody = await syncRes.json().catch(() => ({}))
        throw new Error(errBody?.detail || "Backend sync failed")
      }
      const backendUser = await syncRes.json()

      login({
        id: backendUser.id,
        name: backendUser.name,
        email: backendUser.email,
        role: backendUser.role ?? "passenger",
      })

      router.push("/")
    } catch (e: unknown) {
      console.error("Google login failed:", e)
      setError(e instanceof Error ? e.message : "Google login failed. Please try again.")
      setIsLoading(false)
    }
  }

  const handleGoogleError = () => {
    setError("Google sign-in was cancelled or failed.")
    setIsLoading(false)
  }

  // Trigger hidden GoogleLogin button via our custom styled button
  const triggerGoogleLogin = () => {
    setIsLoading(true)
    const btn = googleBtnRef.current?.querySelector("div[role='button']") as HTMLElement | null
    btn?.click()
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (user) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4 bg-slate-50">
        <Card className="w-full max-w-sm shadow-2xl border-none rounded-3xl overflow-hidden">
          <CardHeader className="text-center bg-primary text-primary-foreground pb-8 pt-10">
            <div className="flex justify-center mb-4">
              <div className="w-20 h-20 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center border-4 border-white/30">
                <UserIcon className="h-10 w-10 text-white" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">{user.name}</CardTitle>
            <CardDescription className="text-primary-foreground/80 flex items-center justify-center gap-1 mt-1">
              <Mail className="h-3 w-3" /> {user.email}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6 pt-8 text-center">
            <p className="text-muted-foreground">You are currently logged in.</p>
            <Button variant="outline" className="w-full rounded-2xl h-12 font-bold" onClick={() => router.push("/")}>
              Go to Home
            </Button>
          </CardContent>

          <CardFooter className="pb-8 px-6">
            <Button variant="destructive" className="w-full rounded-2xl h-12 font-bold gap-2 shadow-lg shadow-destructive/20" onClick={logout}>
              <LogOut className="h-4 w-4" /> Sign Out
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-slate-50">
      <Card className="w-full max-w-sm shadow-2xl border-t-4 border-t-black rounded-2xl overflow-hidden bg-white">
        <CardHeader className="text-center pb-2">
          <div className="flex justify-center mb-2">
            <div className="relative w-12 h-12">
              <Image src="/croc_mascot(y).png" alt="Croc Ride Mascot" fill sizes="48px" className="object-contain" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Croc Ride</CardTitle>
          <CardDescription className="text-sm">
            Vadodara <span className="text-primary mx-1">⇄</span> Halol Commute
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4 px-6 space-y-6">
          <p className="text-sm text-muted-foreground text-center">
            To keep our community safe and verified, we currently only support signing in with Google.
          </p>

          {/* Hidden Google button — triggered programmatically */}
          <div ref={googleBtnRef} className="hidden">
            <GoogleLogin onSuccess={handleGoogleSuccess} onError={handleGoogleError} />
          </div>

          {/* Our custom styled button */}
          <Button
            onClick={triggerGoogleLogin}
            variant="outline"
            className="w-full rounded-full h-12 font-bold gap-2 border-2 hover:bg-slate-50 transition-all"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                Sign in with Google
              </>
            )}
          </Button>

          {error && (
            <Alert variant="destructive" className="rounded-xl">
              <AlertDescription className="text-xs">{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>

        <CardFooter className="flex flex-col gap-2 border-t pt-4 pb-6 bg-slate-50/50">
          <p className="text-[9px] text-center text-muted-foreground uppercase tracking-widest px-6">
            Secured by Google Auth &middot; Verified Community
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
