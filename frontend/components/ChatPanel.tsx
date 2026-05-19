"use client";

import { Maximize2, Minimize2, Plus, Send } from "lucide-react";
import { AgentAvatar } from "@/components/AgentAvatar";

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

interface Props {
  // Controlled state — the dashboard owns the draft + history so the
  // recommendation panel can react to keystrokes in real time.
  draft: string;
  onDraftChange(v: string): void;
  history: string[];        // user's past sent messages
  onSend(): void;
  busy: boolean;            // true during an explicit send
  expanded: boolean;
  onToggleExpand(): void;
}

// Left-hand chat panel — user types their question and reviews their own
// past messages. The AI response goes into RecommendationPanel.
export function ChatPanel({
  draft,
  onDraftChange,
  history,
  onSend,
  busy,
  expanded,
  onToggleExpand,
}: Props) {
  const ExpandIcon = expanded ? Minimize2 : Maximize2;

  return (
    <section className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-black/40 shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      {/* Header — drag handle */}
      <header
        data-drag-handle="true"
        className="flex cursor-grab items-center justify-between border-b border-line bg-white/[0.02] px-4 py-2.5 active:cursor-grabbing select-none"
      >
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-full border border-neon/30 bg-neon-soft">
            <AgentAvatar slug="manager" size={28} className="h-full w-full object-cover" />
          </div>
          <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/60">
            AI Manager Chat
          </span>
        </div>
        <button
          type="button"
          aria-label={expanded ? "Collapse" : "Expand"}
          onClick={onToggleExpand}
          className="flex h-6 w-6 items-center justify-center rounded-md text-white/50 transition hover:bg-white/5 hover:text-white"
        >
          <ExpandIcon size={13} />
        </button>
      </header>

      {/* History — user bubbles only */}
      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3 scrollbar-thin">
        {history.length === 0 && draft.trim().length === 0 && (
          <div className="grid h-full place-items-center text-center text-xs text-white/35">
            Yangi savol bilan boshlang —<br />javob o&apos;ngdagi panelda chiqadi.
          </div>
        )}
        {history.map((msg, i) => (
          <div key={i} className="self-end max-w-[85%]">
            <div className="rounded-2xl rounded-tr-sm border border-neon/20 bg-neon-soft px-4 py-2.5 text-sm leading-relaxed text-white shadow-[0_0_15px_rgba(34,255,136,0.05)]">
              {msg}
            </div>
          </div>
        ))}
        {/* Live draft echo so the user sees what's pending */}
        {draft.trim().length > 0 && (
          <div className="self-end max-w-[85%]">
            <div className="rounded-2xl rounded-tr-sm border border-line bg-white/[0.03] px-4 py-2.5 text-sm leading-relaxed text-white/70">
              {draft}
            </div>
          </div>
        )}
      </div>

      {/* Input footer */}
      <div className="flex items-center gap-3 border-t border-line bg-white/[0.02] px-3 py-2.5">
        <button
          type="button"
          aria-label="Attach"
          className="flex h-8 w-8 items-center justify-center rounded-full border border-line text-white/50 transition hover:border-white/25 hover:text-white"
        >
          <Plus size={14} />
        </button>
        <input
          type="text"
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          disabled={busy}
          placeholder="Savol yozing — AI Manager javobni avtomatik tayyorlaydi…"
          className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none disabled:opacity-50"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={busy || !draft.trim()}
          aria-label="Send"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-neon text-black shadow-neon-sm transition hover:bg-neon/90 hover:shadow-neon-md disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-neon"
        >
          <Send size={14} />
        </button>
      </div>
    </section>
  );
}
