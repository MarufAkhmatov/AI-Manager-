"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";

interface ChatResponse {
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
}

export function ChatPanel({ onAgentsActive }: Props) {
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
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: renderResponse(res),
          meta: res,
        },
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
      <div className="flex-1 overflow-y-auto space-y-3 p-1 scrollbar-thin">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center text-xs text-text-dim">
            Yangi savol bilan boshlang — AI Manager kerakli agentlarni o'zi tanlaydi.
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "neo px-4 py-3" : "neo-in px-4 py-3"}
          >
            <div className="mb-1 text-[10px] uppercase tracking-wide text-text-dim">
              {m.role}
            </div>
            <div className="whitespace-pre-wrap text-sm text-text">{m.text}</div>
            {m.meta && (
              <div className="mt-2 text-[10px] text-text-dim">
                {m.meta.agents_used.join(" · ")} · {m.meta.ms_total}ms
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <Input
          placeholder="Ask the AI Manager…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          disabled={busy}
        />
        <Button onClick={send} disabled={busy || !draft.trim()}>
          Send
        </Button>
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
