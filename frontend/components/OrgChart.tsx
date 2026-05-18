"use client";

import { useMemo } from "react";
import { AgentCard } from "@/components/AgentCard";
import type { AgentSlug } from "@/components/avatars";

interface AgentSpec {
  slug: AgentSlug;
  name: string;
}

// Manager + 6 sub-agents. All 7 agents from docs/DESIGN.md are kept; the row
// reads left-to-right roughly along the pipeline (intake → analysis → egress).
const MANAGER: AgentSpec = { slug: "manager", name: "AI MANAGER" };

const SUBS: AgentSpec[] = [
  { slug: "architect",  name: "AI ARCHITECT" },
  { slug: "metodist",   name: "AI METODIST" },
  { slug: "searcher",   name: "AI SEARCHER" },
  { slug: "shadow",     name: "AI SHADOW" },
  { slug: "regulyator", name: "AI REGULYATOR" },
  { slug: "secure",     name: "AI SECURE" },
];

interface Props {
  activeAgents?: string[];
}

export function OrgChart({ activeAgents = [] }: Props) {
  const active = useMemo(() => {
    // Activity events use display-name strings ("AI Searcher"); normalise so
    // matching is case-insensitive across the two spellings.
    const norm = new Set(activeAgents.map((s) => s.toUpperCase()));
    return norm;
  }, [activeAgents]);

  const managerActive = active.has(MANAGER.name);

  return (
    <div className="mx-auto w-full max-w-5xl">
      {/* Row 1 — Manager */}
      <div className="flex justify-center">
        <AgentCard
          slug={MANAGER.slug}
          name={MANAGER.name}
          role="Team Lead"
          status="online"
          active={managerActive}
          size="lg"
        />
      </div>

      {/* Row 2 — connector zone: stem down from manager, horizontal bus,
          and one vertical stem per sub-agent column. */}
      <div className="relative h-10">
        {/* manager-down stem */}
        <div className="absolute left-1/2 top-0 h-5 w-px -translate-x-1/2 bg-white/15" />
        {/* horizontal bus, spanning the centres of the first and last
            sub-agent columns in a 6-column even grid. */}
        <div
          className="absolute top-5 border-t border-white/15"
          style={{ left: `${100 / 12}%`, right: `${100 / 12}%` }}
        />
        {/* per-column drops */}
        {SUBS.map((_, i) => (
          <div
            key={i}
            className="absolute top-5 h-5 w-px bg-white/15"
            style={{ left: `${((i + 0.5) * 100) / 6}%` }}
          />
        ))}
      </div>

      {/* Row 3 — sub-agents */}
      <div className="grid grid-cols-6 gap-3">
        {SUBS.map((s) => {
          const on = active.has(s.name);
          return (
            <div key={s.slug} className="flex justify-center">
              <AgentCard
                slug={s.slug}
                name={s.name}
                role="Sub Agent"
                status={on ? "active" : "idle"}
                active={on}
                size="md"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Re-export the canonical list so the avatar stack on the recommendation
// header can render the same set without redefining it.
export const ALL_SUBS = SUBS;
