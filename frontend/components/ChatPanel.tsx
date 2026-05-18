"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { AgentAvatar } from "@/components/AgentAvatar";
import { api } from "@/lib/api";

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

// Floating chat panel — styling ported from the AI-Workflow ChatPanel
// (340×400 glass card, neon-green bot avatar header, send-icon footer).
// Still talks to /api/chat and hands the response back up so the canvas
// can light up the agents that ran.
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
    <div className="group relative flex h-[400px] w-full flex-col overflow-hidden rounded-2xl border border-line bg-black/40 shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      {/* ambient glow */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-neon-soft to-transparent opacity-60 transition-opacity duration-500 group-hover:opacity-100" />

      {/* Header — manager avatar acts as the bot face */}
      <div className="relative z-10 flex items-center gap-3 border-b border-line bg-white/[0.02] px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-neon/30 bg-neon-soft">
          <AgentAvatar slug="manager" size={32} className="h-full w-full object-cover" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-white">AI Manager</h3>
          <p className="text-[11px] text-neon/80">
            {busy ? "Thinking…" : "Online"}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="relative z-10 flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3 scrollbar-thin">
        {messages.length === 0 && (
          <div className="self-start max-w-[85%]">
            <div className="rounded-2xl rounded-tl-sm border border-line bg-white/5 px-4 py-2.5 text-sm leading-relaxed text-white/85 shadow-sm">
              Yangi savol bilan boshlang — AI Manager kerakli agentlarni o&apos;zi tanlaydi va parallel ishga tushiradi.
            </div>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="self-end max-w-[85%]">
              <div className="rounded-2xl rounded-tr-sm border border-neon/20 bg-neon-soft px-4 py-2.5 text-sm leading-relaxed text-white shadow-[0_0_15px_rgba(34,255,136,0.05)]">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="self-start max-w-[90%]">
              <div className="whitespace-pre-wrap rounded-2xl rounded-tl-sm border border-line bg-white/5 px-4 py-2.5 text-sm leading-relaxed text-white/90">
                {m.text}
              </div>
              {m.meta && (
                <span className="ml-2 mt-1.5 block text-[10px] text-white/40">
                  {m.meta.agents_used.join(" · ")} · {m.meta.ms_total}ms
                </span>
              )}
            </div>
          ),
        )}
      </div>

      {/* Input */}
      <div className="relative z-10 border-t border-line bg-white/[0.02] p-3">
        <div className="relative flex items-center">
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
            placeholder="Type a message…"
            className="w-full rounded-xl border border-line bg-black/50 py-2.5 pl-4 pr-10 text-sm text-white placeholder:text-white/30 outline-none transition focus:border-neon/50 focus:ring-1 focus:ring-neon/50 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={send}
            disabled={busy || !draft.trim()}
            aria-label="Send"
            className="absolute right-2 rounded-lg p-1.5 text-white/50 transition-colors hover:bg-neon-soft hover:text-neon disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent"
          >
            <Send size={16} />
          </button>
        </div>
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
