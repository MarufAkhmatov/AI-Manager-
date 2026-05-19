"use client";

import { useState } from "react";
import { Check, Copy, FileText, Loader2, Maximize2, Minimize2 } from "lucide-react";
import { AvatarStack } from "@/components/AvatarStack";
import type { ChatResponse } from "@/components/ChatPanel";
import type { AgentSlug } from "@/components/avatars";

const ALL_AGENTS: Array<{ slug: AgentSlug; name: string }> = [
  { slug: "manager",    name: "AI Manager" },
  { slug: "architect",  name: "AI Architect" },
  { slug: "metodist",   name: "AI Metodist" },
  { slug: "searcher",   name: "AI Searcher" },
  { slug: "shadow",     name: "AI Shadow" },
  { slug: "regulyator", name: "AI Regulyator" },
  { slug: "secure",     name: "AI Secure" },
];

interface Props {
  response: ChatResponse | null;
  previewing: boolean;
  busy: boolean;
  expanded: boolean;
  onToggleExpand(): void;
}

// Read-only output panel — copy + Word + maximise controls. The avatar
// strip sits ABOVE the panel section so that the section itself stays the
// exact same height as the chat panel's section (perfect top/bottom
// symmetry across the two panels).
export function RecommendationPanel({
  response,
  previewing,
  busy,
  expanded,
  onToggleExpand,
}: Props) {
  const [copied, setCopied] = useState(false);
  const text = response ? renderText(response) : "";
  const usedAgents = new Set(response?.agents_used ?? []);
  const items = ALL_AGENTS.map((a) => ({ ...a, active: usedAgents.has(a.name) }));

  async function handleCopy() {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard denied — silently ignore */
    }
  }

  function handleDownloadDoc() {
    if (!text) return;
    const html = `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">
<head><meta charset="utf-8"><title>AI Manager Recommendation</title></head>
<body style="font-family: Calibri, sans-serif; font-size: 11pt; color: #111;">
<h2 style="color: #16502b;">AI Manager Recommendation</h2>
<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(text)}</pre>
${response ? `<hr><p style="font-size: 9pt; color: #555;">Agents: ${response.agents_used.join(", ")} · ${response.ms_total}ms</p>` : ""}
</body></html>`;
    const blob = new Blob([html], { type: "application/msword" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
    a.href = url;
    a.download = `ai-manager-recommendation-${stamp}.doc`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const ExpandIcon = expanded ? Minimize2 : Maximize2;

  return (
    <div className="flex h-full flex-col">
      {/* Avatar strip — drag handle. Fixed height (~32px) so the panel
          section below it remains symmetric with the chat panel section. */}
      <div
        data-drag-handle="true"
        className="flex h-8 cursor-grab items-center gap-2 px-3 active:cursor-grabbing select-none"
      >
        <AvatarStack items={items} size={22} />
        <span className="text-[10px] uppercase tracking-wider text-white/40">
          {response ? `${response.agents_used.length}/${ALL_AGENTS.length} agents` : "no agents"}
        </span>
      </div>

      <section className="relative flex flex-1 flex-col overflow-hidden rounded-2xl border border-line bg-black/40 shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        {/* Header — drag handle + title + actions */}
        <header
          data-drag-handle="true"
          className="flex cursor-grab items-center justify-between border-b border-line bg-white/[0.02] px-4 py-2.5 active:cursor-grabbing select-none"
        >
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-neon shadow-neon-sm" />
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/60">
              AI Manager Recommendation
            </span>
            {(previewing || busy) && (
              <Loader2 size={11} className="ml-1 animate-spin text-neon/70" />
            )}
          </div>

          <div className="flex items-center gap-1">
            <ActionButton
              label={copied ? "Copied" : "Copy"}
              onClick={handleCopy}
              disabled={!text}
              icon={copied ? Check : Copy}
              accent={copied}
            />
            <ActionButton
              label="Word"
              onClick={handleDownloadDoc}
              disabled={!text}
              icon={FileText}
            />
            <button
              type="button"
              aria-label={expanded ? "Collapse" : "Expand"}
              onClick={onToggleExpand}
              className="flex h-6 w-6 items-center justify-center rounded-md text-white/50 transition hover:bg-white/5 hover:text-white"
            >
              <ExpandIcon size={13} />
            </button>
          </div>
        </header>

        {/* Body — read-only output */}
        <div className="relative flex-1 overflow-y-auto px-4 py-3 scrollbar-thin">
          {!response ? (
            <div className="grid h-full place-items-center text-center text-xs text-white/35">
              {previewing
                ? "AI Manager javobni tayyorlayapti…"
                : "AI Manager chatga savol yozing — javob bu yerda avtomatik chiqadi."}
            </div>
          ) : (
            <>
              <pre className="whitespace-pre-wrap select-text font-sans text-sm leading-relaxed text-white/90">
                {text}
              </pre>
              <div className="mt-3 border-t border-line pt-2 text-[10px] text-white/35">
                {response.agents_used.join(" · ")} · {response.ms_total}ms
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  disabled,
  icon: Icon,
  accent,
}: {
  label: string;
  onClick(): void;
  disabled?: boolean;
  icon: typeof Copy;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className={`flex h-6 items-center gap-1 rounded-md px-2 text-[10px] font-medium transition ${
        disabled
          ? "cursor-not-allowed text-white/20"
          : accent
            ? "bg-neon-soft text-neon"
            : "text-white/60 hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon size={11} />
      <span>{label}</span>
    </button>
  );
}

function renderText(r: ChatResponse): string {
  const parts: string[] = [];
  const agents = (r.response as { agents?: Record<string, unknown> }).agents;
  if (agents) {
    for (const [name, payload] of Object.entries(agents)) {
      parts.push(`— ${name} —\n${JSON.stringify(payload, null, 2)}`);
    }
  }
  if (r.citations && r.citations.length > 0) {
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

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
