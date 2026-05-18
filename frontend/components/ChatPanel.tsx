"use client";

import { useState } from "react";
import { ArrowUp, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

export interface ChatResponse {
  task_id: string;
  agents_used: string[];
  response: Record<string, unknown>;
  citations: Array<{
    document_id: string | null;
    title: string | null;
    snippet: string;
    score: number;
  }>;
  ms_total: number;
}

interface Message {
  role: "user" | "assistant";
  text: string;
  meta?: ChatResponse;
}

interface Props {
  onAgentsActive(agents: string[]): void;
  onResponse?(response: ChatResponse): void;
}

export function ChatPanel({ onAgentsActive, onResponse }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const q = draft.trim();
    if (!q || busy) return;
    setBusy(true);
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setDraft("");
    try {
      const res = await api<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: q }),
      });
      onAgentsActive(res.agents_used);
      onResponse?.(res);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: renderResponse(res), meta: res },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `error: ${(e as Error).message}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto space-y-3 px-4 pt-3 scrollbar-thin">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center text-xs text-white/35">
            Yangi savol bilan boshlang — AI Manager kerakli agentlarni o&apos;zi tanlaydi.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              "rounded-xl border px-4 py-3",
              m.role === "user"
                ? "border-white/10 bg-white/[0.03]"
                : "border-white/5 bg-black/40",
            )}
          >
            <div className="mb-1 text-[10px] uppercase tracking-wider text-white/35">
              {m.role}
            </div>
            <div className="whitespace-pre-wrap text-sm text-white/90">{m.text}</div>
            {m.meta && (
              <div className="mt-2 text-[10px] text-white/30">
                {m.meta.agents_used.join(" · ")} · {m.meta.ms_total}ms
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer: + on the far left, free text in the middle, ↑ on the far right. */}
      <div className="flex items-center gap-3 border-t border-white/5 px-3 py-2.5">
        <button
          type="button"
          aria-label="Attach"
          className="flex h-8 w-8 items-center justify-center rounded-full border border-white/10 text-white/55 transition hover:border-white/25 hover:text-white"
        >
          <Plus size={14} />
        </button>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          disabled={busy}
          placeholder="Ask the AI Manager…"
          className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none disabled:opacity-50"
        />
        <button
          type="button"
          onClick={send}
          disabled={busy || !draft.trim()}
          aria-label="Send"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-black transition hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ArrowUp size={14} strokeWidth={2.4} />
        </button>
      </div>
    </div>
  );
}

function renderResponse(r: ChatResponse): string {
  const parts: string[] = [];
  const agents = (r.response as { agents?: Record<string, unknown> }).agents;
  if (agents) {
    for (const [name, payload] of Object.entries(agents)) {
      parts.push(`— ${name} —\n${JSON.stringify(payload, null, 2)}`);
    }
  }
  if (r.citations.length > 0) {
    parts.push(
      "Citations:\n" +
        r.citations
          .map(
            (c, i) =>
              `[${i + 1}] ${c.title ?? "(redacted)"} — score ${c.score.toFixed(2)}\n${c.snippet}`,
          )
          .join("\n\n"),
    );
  }
  return parts.join("\n\n") || "(empty)";
}
