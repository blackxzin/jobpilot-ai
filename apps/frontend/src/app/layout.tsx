import type { Metadata, Viewport } from "next";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";
import { Inter, Sora } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const sora = Sora({ subsets: ["latin"], variable: "--font-display", display: "swap" });

export const metadata: Metadata = {
  title: "JobPilot AI — Copiloto de carreira",
  description:
    "Encontre vagas compatíveis, avalie seu currículo contra filtros de ATS e prepare cada candidatura com IA.",
  manifest: "/manifest.json",
  applicationName: "JobPilot AI",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "JobPilot AI",
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  // Matches --bg-page in each theme so the mobile browser chrome does not
  // clash with the page while scrolling.
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#08090c" },
    { media: "(prefers-color-scheme: light)", color: "#f7f8fa" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${sora.variable}`} suppressHydrationWarning>
      <head>
        {/*
          Applies the stored theme before first paint. Without it the page
          renders in the default dark palette and then snaps to light, which
          is a visible flash on every load for light-theme users.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("jobpilot-theme");if(!t){t=window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";}document.documentElement.setAttribute("data-theme",t);}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-screen font-sans antialiased">
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
