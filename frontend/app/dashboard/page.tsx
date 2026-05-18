"use client";

import { useEffect, useState } from "react";
import { AgentOrgChart } from "@/components/AgentOrgChart";
import { ResizableChatPanel } from "@/components/ResizableChatPanel";
import { TopMenuBar } from "@/components/TopMenuBar";
import { openActivityWS } from "@/lib/api";

interface ActivityEvent {
  agent: string;
  event: string;
}

// Agents that emitted an event in the last ACTIVE_WINDOW_MS pulse on the chart.
const ACTIVE_WINDOW_MS = 4000;

export default function DashboardPage() {
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [recentByAgent, setRecentByAgent] = useState<Record<string, number>>({});

  // Subscribe to /ws/activity so the chart pulses in real time even when
  // the operator isn't actively chatting (e.g. AI Architect ingesting,
  // AI Regulyator crawling).
  useEffect(() => {
    const ws = openActivityWS();
    ws.onmessage = (msg) => {
      try {
        const ev: ActivityEvent = JSON.parse(msg.data);
        setRecentByAgent((prev) => ({ ...prev, [ev.agent]: Date.now() }));
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, []);

  // Every second, derive the active agent set from the recency map.
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      const active = Object.entries(recentByAgent)
        .filter(([, ts]) => now - ts < ACTIVE_WINDOW_MS)
        .map(([name]) => name);
      // Merge with the explicit chat-triggered list so a recent response
      // is still highlighted while events fade.
      setActiveAgents((prev) => Array.from(new Set([...prev, ...active])));
    }, 800);
    return () => clearInterval(t);
  }, [recentByAgent]);

  return (
    <main className="flex min-h-screen flex-col gap-4 pb-4 pt-3">
      <TopMenuBar />

      <section className="mx-3 flex-1 min-h-[460px]">
        <AgentOrgChart activeAgents={activeAgents} />
      </section>

      <section className="mx-3">
        <ResizableChatPanel onAgentsActive={setActiveAgents} />
      </section>
    </main>
  );
}
