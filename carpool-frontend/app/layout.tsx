"use client"

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from "@/lib/AuthContext";
import { RoleProvider } from "@/lib/RoleContext";
import { BottomNav } from "@/components/BottomNav";
import SuperTokensReact, { SuperTokensWrapper } from 'supertokens-auth-react'
import { frontendConfig } from '@/lib/supertokens/config'
import { usePathname } from "next/navigation";

if (typeof window !== 'undefined') {
  SuperTokensReact.init(frontendConfig())
}

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <SuperTokensWrapper>
          <AuthProvider>
            <RoleProvider>
              <main className={isAuthPage ? "" : "pb-16"}>{children}</main>
              {!isAuthPage && <BottomNav />}
            </RoleProvider>
          </AuthProvider>
        </SuperTokensWrapper>
      </body>
    </html>
  );
}