"use client"

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from "@/lib/AuthContext";
import { RoleProvider } from "@/lib/RoleContext";
import { BottomNav } from "@/components/BottomNav";
import { usePathname } from "next/navigation";

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
  const isAuthPage = pathname === "/login";

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <GoogleOAuthProvider clientId="403477193934-b7cahbs2e3kkobclbno63upat04c0at5.apps.googleusercontent.com">
          <AuthProvider>
            <RoleProvider>
              <main className={isAuthPage ? "" : "pb-16"}>{children}</main>
              {!isAuthPage && <BottomNav />}
            </RoleProvider>
          </AuthProvider>
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}