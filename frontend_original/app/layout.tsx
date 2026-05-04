import { GoogleAnalytics } from "@next/third-parties/google";
import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import NavigationSafety from "./components/common/NavigationSafety";
import "./globals.css";

const soriaFont = localFont({
  src: "../public/soria-font.ttf",
  variable: "--font-soria",
});

const vercettiFont = localFont({
  src: "../public/Vercetti-Regular.woff",
  variable: "--font-vercetti",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://github.com/Jethin10"),
  title: "Placement Trust Passport",
  description: "Evidence-backed placement readiness, assessment integrity, trust scoring, and recruiter-facing proof.",
  keywords: "placement trust, readiness assessment, GitHub evidence, coding harness, trust stamp, student placement",
  authors: [{ name: "Placement Trust" }],
  creator: "Placement Trust",
  publisher: "Placement Trust",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    title: "Placement Trust Passport",
    description: "Evidence-backed student readiness and recruiter-facing proof.",
    url: "https://github.com/Jethin10",
    siteName: "Placement Trust Passport",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Placement Trust Passport",
    description: "Evidence-backed student readiness and recruiter-facing proof.",
  },
  verification: {
    google: "GsRYY-ivL0F_VKkfs5KAeToliqz0gCrRAJKKmFkAxBA",
  },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  initialScale: 1,
  minimumScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="overscroll-y-none" suppressHydrationWarning>
      <body className={`${soriaFont.variable} ${vercettiFont.variable} font-sans antialiased`} suppressHydrationWarning>
        <NavigationSafety />
        {children}
      </body>
      <GoogleAnalytics gaId="G-7WD4HM3XRE" />
    </html>
  );
}
