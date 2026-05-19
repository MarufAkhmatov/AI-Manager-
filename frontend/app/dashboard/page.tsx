"use client";

import { useEffect, useRef, useState } from "react";
import { TopHeader } from "@/components/TopHeader";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import type { ChatResponse } from "@/components/ChatPanel";
import { api, openActivityWS } from "@/lib/api";

interface ActivityEvent {
  agent: string;
  event: string;
}

const ACTIVE_WINDOW_MS = 4000;
const DEMO_MS = 4500;
const PREVIEW_DEBOUNCE_MS = 700;
const PREVIEW_MIN_CHARS = 3;

const ALL_AGENT_NAMES = [
  "AI Manager",
  "AI Architect",
  "AI Metodist",
  "AI Searcher",
  "AI Shadow",
  "AI Regulyator",
  "AI Secure",
];

export default function DashboardPage() {
  // ── Workflow / agent activity ──
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [recentByAgent, setRecentByAgent] = useState<Record<string, number>>({});
  const [demoUntil, setDemoUntil] = useState<number>(0);

  // ── Chat state (lifted so RecommendationPanel can react to typing) ──
  const [draft, setDraft] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);          // explicit send in flight
  const [previewing, setPreviewing] = useState(false); // auto-suggest in flight

  const previewAbortRef = useRef<AbortController | null>(null);

  // Live activity stream — keeps the chart pulsing for background work
  // (Architect ingesting, Regulyator crawling, …).
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

  // Derive activeAgents from the recency map + demo override.
  useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      const recent = Object.entries(recentByAgent)
        .filter(([, ts]) => now - ts < ACTIVE_WINDOW_MS)
        .map(([name]) => name);
      const demo = now < demoUntil ? ALL_AGENT_NAMES : [];
      setActiveAgents((prev) =>
        Array.from(new Set([...prev, ...recent, ...demo])),
      );
    }, 800);
    return () => clearInterval(t);
  }, [recentByAgent, demoUntil]);

  // Auto-suggest: debounce the draft, fire a /api/chat call, and stash the
  // response so RecommendationPanel renders a live preview.
  useEffect(() => {
    if (busy) return;
    const text = draft.trim();
    if (text.length < PREVIEW_MIN_CHARS) return;
    const t = setTimeout(() => {
      previewAbortRef.current?.abort();
      const ac = new AbortController();
      previewAbortRef.current = ac;
      setPreviewing(true);
      api<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
        signal: ac.signal,
      })
        .then((res) => {
          if (ac.signal.aborted) return;
          setResponse(res);
          setActiveAgents((prev) =>
            Array.from(new Set([...prev, ...res.agents_used])),
          );
        })
        .catch(() => {
          /* preview errors are silent — the explicit send will surface them */
        })
        .finally(() => {
          if (!ac.signal.aborted) setPreviewing(false);
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [draft, busy]);

  async function handleSend() {
    const text = draft.trim();
    if (!text || busy) return;
    previewAbortRef.current?.abort();
    setBusy(true);
    setHistory((prev) => [...prev, text]);
    setDraft("");
    try {
      const res = await api<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      setResponse(res);
      setActiveAgents((prev) =>
        Array.from(new Set([...prev, ...res.agents_used])),
      );
    } catch (e) {
      setResponse({
        task_id: "error",
        agents_used: [],
        response: { agents: { error: { message: (e as Error).message } } },
        citations: [],
        ms_total: 0,
      });
    } finally {
      setBusy(false);
    }
  }

  const isRunning =
    busy || previewing || activeAgents.length > 0 || Date.now() < demoUntil;

  function handleRun() {
    if (Date.now() < demoUntil) {
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
          draft={draft}
          onDraftChange={setDraft}
          history={history}
          onSend={handleSend}
          busy={busy}
          previewing={previewing}
          response={response}
        />
      </div>
    </main>
  );
}
