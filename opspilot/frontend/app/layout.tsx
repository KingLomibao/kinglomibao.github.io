import type { Metadata } from "next";
import "./globals.css";
import { NavBar } from "@/components/NavBar";

export const metadata: Metadata = {
  title: "OpsPilot | Ironbridge Field Operations",
  description: "Deterministic workforce operations dashboard for Ironbridge Field Operations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <NavBar />
        <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
