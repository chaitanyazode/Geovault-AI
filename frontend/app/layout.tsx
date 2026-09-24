import "./globals.css";
import type { Metadata } from "next";
import AppShell from "../components/AppShell";

export const metadata: Metadata = {
  title: "GeoVault AI — Geological, Mining & Operational Reporting Intelligence",
  description: "AI-Powered Geological, Mining and Operational Reporting Solution for CMPDI and Coal India Limited Subsidiaries",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-50 text-slate-900 min-h-screen">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
