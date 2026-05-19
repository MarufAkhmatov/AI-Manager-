"use client";

import { useRef } from "react";
import { Loader2, Maximize2, Minimize2, Paperclip, Plus, Send, X } from "lucide-react";
import { AgentAvatar } from "@/components/AgentAvatar";
import { cn } from "@/lib/cn";

export interface CaseAnalysis {
  summary: string;
  affected_internal: Array<{
    document_id: string | null;
    title: string | null;
    snippet: string;
    score: number;
    section: string | null;
    department: string | null;
  }>;
  external_basis: Array<{
    authority: string | null;
    source_url: string | null;
    title: string | null;
    snippet: string;
  }>;
  conflicts: Array<{
    internal_ref: string;
    external_ref: string;
    why: string;
  }>;
  recommendations: Array<{
    action: string;
    target_doc: string | null;
    target_clause: string | null;
    suggested_text: string;
  }>;
  affected_departments: string[];
}

export interface AttachmentMeta {
  id: string;
  filename: string;
  bytes_size: number;
  char_count: number;
}

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
  case_analysis?: CaseAnalysis;
  attachment?: AttachmentMeta | { missing: true; id: string } | null;
  ms_total: number;
}

export interface PendingAttachment {
  attachment_id: string;
  filename: string;
  bytes_size: number;
  char_count: number;
}

interface Props {
  draft: string;
  onDraftChange(v: string): void;
  history: string[];
  onSend(): void;
  busy: boolean;
  expanded: boolean;
  onToggleExpand(): void;

  attachment: PendingAttachment | null;
  attachmentBusy: boolean;
  attachmentError: string | null;
  onAttach(file: File): void;
  onClearAttachment(): void;
}

const ACCEPT = ".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.tiff";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function ChatPanel({
  draft,
  onDraftChange,
  history,
  onSend,
  busy,
  expanded,
  onToggleExpand,
  attachment,
  attachmentBusy,
  attachmentError,
  onAttach,
  onClearAttachment,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ExpandIcon = expanded ? Minimize2 : Maximize2;

  function pickFile() {
    fileInputRef.current?.click();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) onAttach(f);
    // Reset so picking the same file twice re-fires onChange.
    e.target.value = "";
  }

  const sendDisabled = busy || (!draft.trim() && !attachment);

  return (
    <section className="relative flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-black/40 shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleFileChange}
        className="hidden"
      />

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
        {history.length === 0 &&
          draft.trim().length === 0 &&
          !attachment && (
            <div className="grid h-full place-items-center text-center text-xs text-white/35">
              Yangi savol bilan boshlang —<br />
              <span className="mt-1">📎 Xat / sirkulyar yuklash uchun chap-pastdagi <b>+</b> tugmasini bosing.</span><br />
              javob o&apos;ngdagi panelda chiqadi.
            </div>
          )}
        {history.map((msg, i) => (
          <div key={i} className="self-end max-w-[85%]">
            <div className="rounded-2xl rounded-tr-sm border border-neon/20 bg-neon-soft px-4 py-2.5 text-sm leading-relaxed text-white shadow-[0_0_15px_rgba(34,255,136,0.05)]">
              {msg}
            </div>
          </div>
        ))}
        {draft.trim().length > 0 && (
          <div className="self-end max-w-[85%]">
            <div className="rounded-2xl rounded-tr-sm border border-line bg-white/[0.03] px-4 py-2.5 text-sm leading-relaxed text-white/70">
              {draft}
            </div>
          </div>
        )}
      </div>

      {/* Attachment chip + input footer */}
      <div className="border-t border-line bg-white/[0.02]">
        {(attachment || attachmentBusy || attachmentError) && (
          <div className="flex items-center gap-2 border-b border-line px-3 py-1.5">
            {attachmentBusy ? (
              <span className="flex items-center gap-2 text-[11px] text-white/55">
                <Loader2 size={12} className="animate-spin text-neon" />
                Faylni o&apos;qiyapman…
              </span>
            ) : attachment ? (
              <div className="flex items-center gap-2 rounded-full border border-neon/30 bg-neon-soft px-3 py-1 text-[11px] text-white">
                <Paperclip size={11} className="text-neon" />
                <span className="max-w-[180px] truncate font-medium">
                  {attachment.filename}
                </span>
                <span className="text-white/45">
                  · {formatBytes(attachment.bytes_size)} · {attachment.char_count.toLocaleString()} chars
                </span>
                <button
                  type="button"
                  onClick={onClearAttachment}
                  aria-label="Remove attachment"
                  className="ml-1 rounded-full text-white/50 transition hover:text-white"
                >
                  <X size={12} />
                </button>
              </div>
            ) : attachmentError ? (
              <span
                className={cn(
                  "flex items-center gap-1.5 text-[11px] text-amber",
                )}
              >
                <X size={11} /> {attachmentError}
              </span>
            ) : null}
          </div>
        )}

        <div className="flex items-center gap-3 px-3 py-2.5">
          <button
            type="button"
            onClick={pickFile}
            aria-label="Attach file"
            title="Xat / sirkulyar / PDF yuklash"
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-full border transition",
              attachment
                ? "border-neon/40 bg-neon-soft text-neon"
                : "border-line text-white/50 hover:border-white/25 hover:text-white",
            )}
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
            placeholder={
              attachment
                ? "Faylga oid savol yozing (yoki bo'sh qoldirib Send bosing)…"
                : "Savol yozing — AI Manager javobni avtomatik tayyorlaydi…"
            }
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none disabled:opacity-50"
          />
          <button
            type="button"
            onClick={onSend}
            disabled={sendDisabled}
            aria-label="Send"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-neon text-black shadow-neon-sm transition hover:bg-neon/90 hover:shadow-neon-md disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-neon"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </section>
  );
}
