import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { ThemeProvider } from "@/lib/theme";

export const metadata: Metadata = {
  title: "AI Manager Platform",
  description: "Local multi-agent compliance platform",
};

// `dark` is the default — the ThemeProvider may switch it client-side
// after mount based on the user's last choice in localStorage.
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="min-h-screen">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
