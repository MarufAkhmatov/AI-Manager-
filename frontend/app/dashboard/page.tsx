"use client";

import { useEffect, useState } from "react";
import { OrgChart, ALL_SUBS } from "@/components/OrgChart";
import { Panel } from "@/components/Panel";
import { ChatPanel, type ChatResponse } from "@/components/ChatPanel";
import { RecommendationPanel } from "@/components/RecommendationPanel";
import { AvatarStack } from "@/components/AvatarStack";
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
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);

  // Background pulse from /ws/activity so the chart highlights agents even
  // when the operator isn't chatting (Architect ingesting, Regulyator crawling).
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

  // Derive the active set every second from the recency map and union it with
  // the explicit chat-triggered list.
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      const active = Object.entries(recentByAgent)
        .filter(([, ts]) => now - ts < ACTIVE_WINDOW_MS)
        .map(([name]) => name);
      setActiveAgents((prev) => Array.from(new Set([...prev, ...active])));
    }, 800);
    return () => clearInterval(t);
  }, [recentByAgent]);

  return (
    <main className="flex min-h-screen flex-col gap-6 bg-black pb-6 pt-3">
      <TopMenuBar />

      <section className="mx-3 mt-2">
        <OrgChart activeAgents={activeAgents} />
      </section>

      <section className="mx-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Panel title="AI MANAGER  CHAT">
          <ChatPanel
            onAgentsActive={setActiveAgents}
            onResponse={setLastResponse}
          />
        </Panel>

        <Panel
          title="AI MANAGER RECOMMENDATION"
          rightSlot={
            <AvatarStack
              slugs={ALL_SUBS.map((s) => s.slug)}
              size={22}
              className="mr-1"
            />
          }
        >
          <RecommendationPanel response={lastResponse} />
        </Panel>
      </section>
    </main>
  );
}
