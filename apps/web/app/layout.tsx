import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { brand } from "../lib/brand";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Absolute URLs for social images need a base; WEB_APP_URL is the public origin.
const siteUrl = process.env.WEB_APP_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: brand.name,
  description: brand.shortDescription,
  openGraph: { siteName: brand.name, type: "website" },
};

// The Clerk application can be shared with other products (its own name
// would otherwise appear as "Sign in to <that app>"), so every string that
// interpolates {{applicationName}} is overridden with this brand's name.
const continueTo = `to continue to ${brand.name}`;
const clerkLocalization = {
  signIn: {
    start: {
      title: `Sign in to ${brand.name}`,
      titleCombined: `Continue to ${brand.name}`,
      alternativePhoneCodeProvider: { title: `Sign in to ${brand.name} with {{provider}}` },
    },
    alternativePhoneCodeProvider: { subtitle: continueTo },
    emailCode: { subtitle: continueTo },
    emailCodeMfa: { subtitle: continueTo },
    emailLink: { subtitle: continueTo },
    emailLinkMfa: { subtitle: continueTo },
    phoneCode: { subtitle: continueTo },
    ssoBypass: { code: { subtitle: continueTo } },
  },
  signUp: {
    start: {
      alternativePhoneCodeProvider: { title: `Sign up to ${brand.name} with {{provider}}` },
    },
    emailLink: { subtitle: continueTo },
  },
  organizationList: { subtitle: continueTo },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // `dynamic`: every page is rendered per request so Clerk's scripts get the CSP nonce from proxy.ts.
    <ClerkProvider dynamic localization={clerkLocalization}>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col bg-background text-foreground">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
