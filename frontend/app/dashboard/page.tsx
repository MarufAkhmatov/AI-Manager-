"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TopHeader } from "@/components/TopHeader";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import type { ChatResponse, PendingAttachment } from "@/components/ChatPanel";
import {
  ApiError,
  api,
  hasToken,
  openActivityWS,
  uploadAttachment,
} from "@/lib/api";

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

interface ChatPayload {
  message: string;
  attachment_id?: string;
}

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!hasToken()) {
      router.replace("/login");
    }
  }, [router]);

  // Workflow / agent activity
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [recentByAgent, setRecentByAgent] = useState<Record<string, number>>({});
  const [demoUntil, setDemoUntil] = useState<number>(0);

  // Chat state (lifted)
  const [draft, setDraft] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewing, setPreviewing] = useState(false);

  // Attachment state
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);
  const [attachmentBusy, setAttachmentBusy] = useState(false);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);

  const previewAbortRef = useRef<AbortController | null>(null);

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

  // Auto-suggest debounced. Uploads also trigger the preview — even an
  // empty draft is interesting when the attachment carries the question.
  useEffect(() => {
    if (busy) return;
    const text = draft.trim();
    if (!attachment && text.length < PREVIEW_MIN_CHARS) return;

    const t = setTimeout(() => {
      previewAbortRef.current?.abort();
      const ac = new AbortController();
      previewAbortRef.current = ac;
      setPreviewing(true);
      const payload: ChatPayload = {
        message: text || "tahlil qiling",
        attachment_id: attachment?.attachment_id,
      };
      api<ChatResponse>("/api/chat/suggest", {
        method: "POST",
        body: JSON.stringify(payload),
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
        })
        .finally(() => {
          if (!ac.signal.aborted) setPreviewing(false);
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [draft, attachment, busy, router]);

  async function handleAttach(file: File) {
    setAttachmentError(null);
    setAttachmentBusy(true);
    try {
      const up = await uploadAttachment(file);
      setAttachment({
        attachment_id: up.attachment_id,
        filename: up.filename,
        bytes_size: up.bytes_size,
        char_count: up.char_count,
      });
    } catch (e) {
      if (e instanceof ApiError && e.kind === "auth") {
        router.replace("/login");
        return;
      }
      const msg =
        e instanceof ApiError
          ? e.kind === "network"
            ? "Backend bilan aloqa yo'q — server ishlayotganini tekshiring."
            : `Yuklash xatosi (${e.status}): ${e.message.slice(0, 120)}`
          : (e as Error).message;
      setAttachmentError(msg);
      setAttachment(null);
    } finally {
      setAttachmentBusy(false);
    }
  }

  function handleClearAttachment() {
    setAttachment(null);
    setAttachmentError(null);
  }

  async function handleSend() {
    const text = draft.trim();
    if (!text && !attachment) return;
    if (busy) return;
    previewAbortRef.current?.abort();
    setBusy(true);
    const userBubble = text || `📎 ${attachment?.filename}`;
    setHistory((prev) => [...prev, userBubble]);
    setDraft("");
    const sentAttachment = attachment;
    try {
      const payload: ChatPayload = {
        message: text || "tahlil qiling",
        attachment_id: sentAttachment?.attachment_id,
      };
      const res = await api<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setResponse(res);
      setActiveAgents((prev) =>
        Array.from(new Set([...prev, ...res.agents_used])),
      );
      // Successful send — clear the attachment so the next message starts fresh.
      setAttachment(null);
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
          attachment={attachment}
          attachmentBusy={attachmentBusy}
          attachmentError={attachmentError}
          onAttach={handleAttach}
          onClearAttachment={handleClearAttachment}
        />
      </div>
    </main>
  );
}
