"use client";

import Link from "next/link";
import { AgentNode } from "@/components/AgentNode";

const AGENTS: { name: string; slug: string }[] = [
  { name: "AI Manager", slug: "manager" },
  { name: "AI Searcher", slug: "searcher" },
  { name: "AI Metodist", slug: "metodist" },
  { name: "AI Shadow", slug: "shadow" },
  { name: "AI Secure", slug: "secure" },
  { name: "AI Regulyator", slug: "regulyator" },
  { name: "AI Architect", slug: "architect" },
];

// Hex layout: AI Manager at center, six others around it.
const POSITIONS = [
  { x: 0, y: 0 },
  { x: 220, y: -10 },
  { x: 130, y: 200 },
  { x: -130, y: 200 },
  { x: -220, y: -10 },
  { x: -130, y: -220 },
  { x: 130, y: -220 },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen px-8 py-10">
      <header className="mb-10 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-wide">AI Manager Platform</h1>
        <nav className="flex gap-4 text-sm text-bone-200">
          <Link href="/manager" className="hover:text-accent">
            Chat
          </Link>
          <Link href="/kb" className="hover:text-accent">
            Knowledge base
          </Link>
        </nav>
      </header>

      <div className="relative mx-auto h-[640px] w-[640px]">
        {AGENTS.map((a, i) => {
          const p = POSITIONS[i];
          return (
            <div
              key={a.slug}
              className="absolute"
              style={{
                left: `calc(50% + ${p.x}px - 60px)`,
                top: `calc(50% + ${p.y}px - 60px)`,
              }}
            >
              <AgentNode
                name={a.name}
                slug={a.slug}
                size={a.slug === "manager" ? 160 : 120}
              />
            </div>
          );
        })}
      </div>
    </main>
  );
}
