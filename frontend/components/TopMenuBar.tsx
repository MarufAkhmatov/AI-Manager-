"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, LayoutDashboard, LogOut, MessagesSquare } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { cn } from "@/lib/cn";
import { logout } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/manager", label: "Full Chat", icon: MessagesSquare },
  { href: "/kb", label: "Knowledge Base", icon: Database },
];

export function TopMenuBar() {
  const path = usePathname();

  function signOut() {
    logout();
    window.location.href = "/login";
  }

  return (
    <header className="glass sticky top-3 z-40 mx-3 flex items-center justify-between px-4 py-2">
      <Link href="/dashboard" className="flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-accent shadow-glow" />
        <span className="text-sm font-semibold tracking-wide text-text">
          AI Manager Platform
        </span>
      </Link>

      <nav className="flex items-center gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-2xl px-3 py-1.5 text-sm transition",
                active
                  ? "bg-accent-soft text-accent"
                  : "text-text-dim hover:text-text hover:bg-surface",
              )}
            >
              <Icon size={15} />
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <button
          type="button"
          onClick={signOut}
          aria-label="Sign out"
          className="neo flex h-9 w-9 items-center justify-center rounded-full transition hover:accent-pulse"
        >
          <LogOut size={15} className="text-text" />
        </button>
      </div>
    </header>
  );
}
