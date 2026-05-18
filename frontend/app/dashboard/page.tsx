"use client";

import { useEffect, useState } from "react";
import { TopHeader } from "@/components/TopHeader";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import { openActivityWS } from "@/lib/api";

interface ActivityEvent {
  agent: string;
  event: string;
}

// Agents that emitted an event in the last ACTIVE_WINDOW_MS pulse on the chart.
const ACTIVE_WINDOW_MS = 4000;

// Demo-mode lights every edge for a few seconds so the operator can see the
// running visualisation without typing into the chat.
const DEMO_MS = 4500;

const ALL_AGENTS = [
  "AI Manager",
  "AI Architect",
  "AI Metodist",
  "AI Searcher",
  "AI Shadow",
  "AI Regulyator",
  "AI Secure",
];

export default function DashboardPage() {
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [recentByAgent, setRecentByAgent] = useState<Record<string, number>>({});
  const [demoUntil, setDemoUntil] = useState<number>(0);

  // Real-time activity stream — keeps the canvas in sync with background
  // work (Architect ingesting, Regulyator crawling, etc.).
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

  // Derive the active set every 800ms by combining the recency map, chat-
  // triggered agents, and demo-mode override.
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      const recent = Object.entries(recentByAgent)
        .filter(([, ts]) => now - ts < ACTIVE_WINDOW_MS)
        .map(([name]) => name);
      const demo = now < demoUntil ? ALL_AGENTS : [];
      setActiveAgents((prev) =>
        Array.from(new Set([...prev, ...recent, ...demo])),
      );
    }, 800);
    return () => clearInterval(t);
  }, [recentByAgent, demoUntil]);

  const isRunning = activeAgents.length > 0 || Date.now() < demoUntil;

  function handleRun() {
    if (isRunning) {
      // stop demo immediately and clear chat-active set; live WS events keep
      // their own recency, so they'll drop out naturally inside 4s.
      setDemoUntil(0);
      setActiveAgents([]);
    } else {
      setDemoUntil(Date.now() + DEMO_MS);
    }
  }

  return (
    <main className="relative flex h-screen w-screen flex-col overflow-hidden bg-bg text-white">
      <TopHeader
        isRunning={isRunning}
        activeAgents={activeAgents}
        onRun={handleRun}
      />
      <div className="relative flex-1">
        <WorkflowCanvas
          isRunning={isRunning}
          activeAgents={activeAgents}
          onAgentsActive={setActiveAgents}
        />
      </div>
    </main>
  );
}
