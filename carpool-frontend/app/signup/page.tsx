"use client"

import { useState } from "react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import * as EmailPassword from "supertokens-auth-react/recipe/emailpassword"
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
import { Loader2, Mail, Lock, UserPlus, User, Eye, EyeOff } from "lucide-react"

export default function SignupPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Form states
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()

    if (password !== confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const response = await EmailPassword.signUp({
        formFields: [
          { id: "email", value: email },
          { id: "password", value: password }
        ]
      })

      if (response.status === "OK") {
        // Redirection handled by SuperTokens config or manual redirect
        router.push("/auth/verify")
      } else if (response.status === "FIELD_ERROR") {
        setError(response.formFields[0].error)
      } else {
        setError("Sign up failed. Please try again.")
      }
    } catch (e: any) {
      setError(e.message || "Something went wrong during sign up")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-slate-50">
      <Card className="w-full max-w-sm shadow-2xl border-t-4 border-t-[#15803d] rounded-2xl overflow-hidden bg-white">
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
          <CardTitle className="text-2xl font-bold tracking-tight">Join Croc Ride</CardTitle>
          <CardDescription className="text-sm">
            Create an account for your <span className="text-primary font-semibold">Commute</span>
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-4 px-6 space-y-4">
          <form onSubmit={handleSignup} className="space-y-4">
            {/* Name Field */}
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  className="rounded-xl text-center"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Email Field */}
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

            {/* Password Field */}
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

            {/* Confirm Password Field */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <ShieldCheck className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  className="rounded-xl text-center"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-primary transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full rounded-xl h-12 font-bold gap-2 mt-2"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <><UserPlus className="h-4 w-4" /> Create Account</>
              )}
            </Button>
          </form>

          {error && (
            <Alert variant="destructive" className="rounded-xl mt-2">
              <AlertDescription className="text-xs">
                {error}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>

        <CardFooter className="flex flex-col gap-2 border-t pt-4 pb-6 bg-slate-50/50">
          <p className="text-xs text-center text-muted-foreground">
            Already have an account?{" "}
            <Button variant="link" className="p-0 h-auto font-bold text-primary" onClick={() => router.push("/login")}>
              Sign In
            </Button>
          </p>
          <p className="text-[9px] text-center text-muted-foreground uppercase tracking-widest px-6 mt-2">
            Secured by SuperTokens &middot; Email Verification Required
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

function ShieldCheck(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}
