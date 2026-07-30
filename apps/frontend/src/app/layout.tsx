import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobPilot AI",
  description: "Copiloto de carreira inteligente",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen" style={{backgroundColor: 'var(--bg-page)', color: 'var(--text-primary)'}}>{children}</body>
    </html>
  );
}
