"use client"

import { useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import * as ThirdParty from "supertokens-auth-react/recipe/thirdparty"
import * as EmailPassword from "supertokens-auth-react/recipe/emailpassword"
import { useAuth } from "@/lib/AuthContext"
import { useGoogleLogin } from '@react-oauth/google'
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, LogOut, User as UserIcon, Mail, ShieldCheck, Lock, UserPlus, LogIn, Eye, EyeOff } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const { user, logout, login, isLoading: authLoading } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // Form states
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isSignUp, setIsSignUp] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setIsLoading(true)
      try {
        const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        })
        const googleUser = await res.json()
        
        login({
          id: googleUser.sub,
          name: googleUser.name,
          email: googleUser.email,
          role: "passenger"
        })
        
        router.push("/")
      } catch (e: any) {
        setError("Failed to fetch Google profile")
      } finally {
        setIsLoading(false)
      }
    },
    onError: () => setError("Google login failed"),
  })

  const handleEmailPasswordAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      if (isSignUp) {
        const response = await EmailPassword.signUp({
          formFields: [
            { id: "email", value: email },
            { id: "password", value: password }
          ]
        })
        if (response.status === "OK") {
          // Check if email verification is required
          router.push("/auth/verify-email")
        } else if (response.status === "FIELD_ERROR") {
          setError(response.formFields[0].error)
        }
      } else {
        const response = await EmailPassword.signIn({
          formFields: [
            { id: "email", value: email },
            { id: "password", value: password }
          ]
        })
        if (response.status === "OK") {
          router.push("/")
        } else if (response.status === "WRONG_CREDENTIALS_ERROR") {
          setError("Invalid email or password")
        } else {
          setError("Login failed")
        }
      }
    } catch (e: any) {
      setError(e.message || "Authentication failed")
    } finally {
      setIsLoading(false)
    }
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
            <div className="grid grid-cols-1 gap-3">
              <Button variant="outline" className="rounded-2xl h-12 font-bold" onClick={() => router.push('/')}>
                Go to Home
              </Button>
            </div>
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
            Vadodara <span className="text-primary mx-1">⇄</span> Halol Commute
          </CardDescription>
        </CardHeader>
        
        <CardContent className="pt-4 px-6 space-y-6">
          <form onSubmit={handleEmailPasswordAuth} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="email" 
                  type="email" 
                  placeholder="name@example.com" 
                  className="rounded-xl text-center"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="password" 
                  type={showPassword ? "text" : "password"} 
                  className="rounded-xl text-center"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button 
              type="submit" 
              className="w-full rounded-xl h-12 font-bold gap-2"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                isSignUp ? <><UserPlus className="h-4 w-4" /> Create Account</> : <><LogIn className="h-4 w-4" /> Sign In</>
              )}
            </Button>

            <div className="text-center">
              <button 
                type="button"
                onClick={() => router.push("/signup")}
                className="text-xs text-primary font-semibold hover:underline"
              >
                New here? Create an account
              </button>
            </div>
          </form>

          <div className="relative py-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-muted-foreground">Or continue with</span>
            </div>
          </div>

          <Button 
            onClick={() => handleGoogleLogin()} 
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
                    Google Account
                </>
            )}
          </Button>

          {error && (
            <Alert variant="destructive" className="rounded-xl">
              <AlertDescription className="text-xs">
                {error}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>

        <CardFooter className="flex flex-col gap-2 border-t pt-4 pb-6 bg-slate-50/50">
          <p className="text-[9px] text-center text-muted-foreground uppercase tracking-widest px-6">
            Secured by SuperTokens &middot; Email Verification Required
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
