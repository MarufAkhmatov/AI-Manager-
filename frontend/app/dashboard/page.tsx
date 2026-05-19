"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TopHeader } from "@/components/TopHeader";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import type { ChatResponse } from "@/components/ChatPanel";
import { ApiError, api, hasToken, openActivityWS } from "@/lib/api";

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
  const router = useRouter();

  // Hard auth gate — bounce to /login if there's no token. The api helper
  // also clears the token on 401 from the server, so a subsequent reload
  // will land here.
  useEffect(() => {
    if (!hasToken()) {
      router.replace("/login");
    }
  }, [router]);

  // ── Workflow / agent activity ──
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [recentByAgent, setRecentByAgent] = useState<Record<string, number>>({});
  const [demoUntil, setDemoUntil] = useState<number>(0);

  // ── Chat state (lifted so RecommendationPanel can react to typing) ──
  const [draft, setDraft] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  const previewAbortRef = useRef<AbortController | null>(null);

  // Live activity stream — keeps the chart pulsing for background work.
  useEffect(() => {
    if (!hasToken()) return;
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

  // Auto-suggest: debounce the draft and hit /api/chat/suggest — a lighter
  // Manager pass that skips Metodist's Claude call, so we don't burn
  // tokens (or wait 15 s) on every keystroke.
  useEffect(() => {
    if (busy) return;
    const text = draft.trim();
    if (text.length < PREVIEW_MIN_CHARS) return;
    const t = setTimeout(() => {
      previewAbortRef.current?.abort();
      const ac = new AbortController();
      previewAbortRef.current = ac;
      setPreviewing(true);
      api<ChatResponse>("/api/chat/suggest", {
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
        .catch((e) => {
          if ((e as Error).name === "AbortError") return;
          if (e instanceof ApiError && e.kind === "auth") {
            router.replace("/login");
          }
          /* Other errors are silent on preview — the explicit send surfaces them. */
        })
        .finally(() => {
          if (!ac.signal.aborted) setPreviewing(false);
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [draft, busy, router]);

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
      if (e instanceof ApiError && e.kind === "auth") {
        router.replace("/login");
        return;
      }
      const msg =
        e instanceof ApiError
          ? e.kind === "network"
            ? "Backend bilan aloqa yo'q — server ishlayotganini tekshiring."
            : e.kind === "server"
              ? `Server xatosi (${e.status}). Iltimos qaytadan urinib ko'ring.`
              : `${e.status}: ${e.message}`
          : (e as Error).message;
      setResponse({
        task_id: "error",
        agents_used: [],
        response: { agents: { error: { message: msg } } },
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
