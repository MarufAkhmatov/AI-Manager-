"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bell,
  ChevronDown,
  Download,
  LogOut,
  Menu,
  Plus,
  Search,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { logout } from "@/lib/api";

const AGENTS = [
  "AI Manager",
  "AI Architect",
  "AI Metodist",
  "AI Searcher",
  "AI Shadow",
  "AI Regulyator",
  "AI Secure",
];

interface Props {
  isRunning: boolean;
  activeAgents: string[];
  onRun(): void;
}

// Top header — pill buttons, glass pills, emerald accents — ported from the
// Metodistai Figma (Header.tsx) and adapted for AI Manager content
// (agents instead of folders, run-workflow instead of audit committee).
export function TopHeader({ isRunning, activeAgents, onRun }: Props) {
  const router = useRouter();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [search, setSearch] = useState("");

  function signOut() {
    logout();
    router.push("/login");
  }

  return (
    <header className="relative z-40 w-full px-6 pt-4 pb-2">
      {/* Top nav row */}
      <div className="flex items-center justify-between">
        {/* Left: logo + drawer */}
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="grid h-10 w-10 place-items-center rounded-full bg-white font-bold text-black"
            aria-label="AI Manager Platform"
          >
            AI
          </Link>
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-white/70 transition hover:text-white"
          >
            <Menu size={18} />
          </button>
        </div>

        {/* Center: live status pill */}
        <div className="hidden items-center gap-2 rounded-full border border-line bg-surface px-1.5 py-1.5 backdrop-blur md:flex">
          <div className="flex items-center gap-2 border-r border-line px-3">
            <Sparkles size={14} className="text-white/50" />
            <span className="text-sm font-medium text-white/80">
              AI Manager
            </span>
            <span className="rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[10px] uppercase tracking-wider text-white/60">
              Workflow
            </span>
          </div>

          <div
            className={`relative ml-1 flex items-center gap-3 rounded-full border px-4 py-1 transition-colors ${
              isRunning
                ? "border-neon/30 bg-neon-soft shadow-neon-sm"
                : "border-line bg-surface-2"
            }`}
          >
            <span
              className={`text-xs font-medium ${
                isRunning ? "text-neon" : "text-white/50"
              }`}
            >
              {isRunning ? "RUNNING" : "IDLE"}
            </span>
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isRunning ? "bg-neon shadow-neon-sm" : "bg-white/30"
              }`}
            />
            {activeAgents.length > 0 && (
              <span className="text-xs text-white/70">
                {activeAgents.slice(0, 3).join(" · ")}
                {activeAgents.length > 3 && ` +${activeAgents.length - 3}`}
              </span>
            )}
          </div>
        </div>

        {/* Right: settings / notifications / account */}
        <div className="hidden items-center gap-3 md:flex">
          <button
            type="button"
            className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-white/70 transition hover:text-white"
            aria-label="Settings"
          >
            <Settings size={18} />
          </button>
          <button
            type="button"
            className="relative grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-white/70 transition hover:text-white"
            aria-label="Notifications"
          >
            <Bell size={18} />
            <span className="absolute right-0 top-0 grid h-3 w-3 place-items-center rounded-full border-2 border-bg bg-danger text-[8px] font-bold text-white" />
          </button>
          <button
            type="button"
            onClick={signOut}
            className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-sm font-medium text-white/70 transition hover:text-white"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>

      {/* Sub-nav row (desktop only) */}
      <div className="hidden items-center justify-between pt-3 md:flex">
        <div className="flex items-center gap-3">
          <div className="relative">
            <button
              type="button"
              onClick={() => setAgentsOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm text-white/80 transition hover:bg-surface-2"
            >
              <Sparkles size={14} className="text-white/50" />
              <span>Agents ({AGENTS.length})</span>
              <ChevronDown size={14} className="text-white/50" />
            </button>
            {agentsOpen && (
              <div className="absolute left-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-neon/20 bg-[#111] py-2 shadow-2xl">
                {AGENTS.map((name) => {
                  const isOn = activeAgents.includes(name);
                  return (
                    <Link
                      key={name}
                      href={`/agents/${name.replace("AI ", "").toLowerCase()}`}
                      onClick={() => setAgentsOpen(false)}
                      className={`flex items-center justify-between px-4 py-2 text-sm transition-colors ${
                        isOn
                          ? "bg-neon-soft text-neon"
                          : "text-white/70 hover:bg-white/5 hover:text-white"
                      }`}
                    >
                      <span>{name}</span>
                      {isOn && <span className="h-1.5 w-1.5 rounded-full bg-neon" />}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex w-56 items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 transition focus-within:border-white/20 focus-within:bg-surface-2">
            <Search size={14} className="shrink-0 text-white/50" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search KB…"
              className="w-full border-none bg-transparent text-sm text-white placeholder:text-white/40 outline-none"
            />
          </div>

          <Link
            href="/kb"
            className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm text-white/80 transition hover:bg-surface-2"
          >
            <Download size={14} className="text-white/50" />
            <span>Knowledge Base</span>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm text-white/80 transition hover:bg-surface-2"
          >
            <Plus size={14} className="text-white/50" />
            <span>New task</span>
          </button>

          <button
            type="button"
            onClick={onRun}
            className={`flex h-fit items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all duration-300 ${
              isRunning
                ? "border border-danger/30 bg-danger/20 text-danger"
                : "bg-neon text-black shadow-neon-sm hover:bg-neon/90 hover:shadow-neon-md"
            }`}
          >
            {isRunning ? "Stop" : "Run Workflow"}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[100] flex flex-col bg-bg/95 px-6 py-4 backdrop-blur-xl md:hidden">
          <div className="flex items-center justify-between">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-white font-bold text-black">
              AI
            </span>
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-white/70"
            >
              <X size={18} />
            </button>
          </div>
          <nav className="mt-8 flex flex-col gap-2">
            {AGENTS.map((name) => (
              <Link
                key={name}
                href={`/agents/${name.replace("AI ", "").toLowerCase()}`}
                onClick={() => setDrawerOpen(false)}
                className="rounded-xl border border-line bg-surface px-4 py-3 text-sm text-white/80"
              >
                {name}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
