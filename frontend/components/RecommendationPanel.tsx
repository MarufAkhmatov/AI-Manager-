"use client";

import { useState } from "react";
import {
  Building2,
  Check,
  ChevronDown,
  Copy,
  ExternalLink,
  FileText,
  GitCompare,
  Lightbulb,
  Loader2,
  Maximize2,
  Minimize2,
  ScrollText,
} from "lucide-react";
import { AvatarStack } from "@/components/AvatarStack";
import type { CaseAnalysis, ChatResponse } from "@/components/ChatPanel";
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

// Read-only output panel — copy + Word + maximise. When the backend ships
// a `case_analysis` field on the response, we render structured sections
// (summary, affected internal docs, external basis, conflicts,
// recommendations, departments) instead of the raw JSON dump.
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
  const ca = response?.case_analysis ?? null;

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

        <div className="relative flex-1 overflow-y-auto px-4 py-3 scrollbar-thin">
          {!response ? (
            <Empty previewing={previewing} />
          ) : ca ? (
            <StructuredCase ca={ca} response={response} />
          ) : (
            <RawDump response={response} text={text} />
          )}
        </div>
      </section>
    </div>
  );
}

// ───────────────────────── Empty + raw fallback ─────────────────────────

function Empty({ previewing }: { previewing: boolean }) {
  return (
    <div className="grid h-full place-items-center text-center text-xs text-white/35">
      {previewing
        ? "AI Manager javobni tayyorlayapti…"
        : "AI Manager chatga savol yozing — javob bu yerda avtomatik chiqadi."}
    </div>
  );
}

function RawDump({ response, text }: { response: ChatResponse; text: string }) {
  return (
    <>
      <pre className="whitespace-pre-wrap select-text font-sans text-sm leading-relaxed text-white/90">
        {text}
      </pre>
      <div className="mt-3 border-t border-line pt-2 text-[10px] text-white/35">
        {response.agents_used.join(" · ")} · {response.ms_total}ms
      </div>
    </>
  );
}

// ───────────────────────── Structured sections ──────────────────────────

function StructuredCase({
  ca,
  response,
}: {
  ca: CaseAnalysis;
  response: ChatResponse;
}) {
  const hasInternal = ca.affected_internal.length > 0;
  const hasExternal = ca.external_basis.length > 0;
  const hasConflicts = ca.conflicts.length > 0;
  const hasRecs = ca.recommendations.length > 0;
  const hasDepts = ca.affected_departments.length > 0;

  return (
    <div className="space-y-4">
      {ca.summary && (
        <p className="select-text whitespace-pre-wrap text-sm leading-relaxed text-white/90">
          {ca.summary}
        </p>
      )}

      {hasDepts && (
        <div className="flex flex-wrap items-center gap-1.5">
          <Building2 size={12} className="text-white/40" />
          {ca.affected_departments.map((d) => (
            <span
              key={d}
              className="rounded-full border border-neon/30 bg-neon-soft px-2 py-[2px] text-[10px] font-medium uppercase tracking-wider text-neon"
            >
              {d}
            </span>
          ))}
        </div>
      )}

      <Section
        title="Affected internal documents"
        icon={ScrollText}
        count={ca.affected_internal.length}
        defaultOpen={hasInternal}
        empty="No internal docs identified."
      >
        <ul className="space-y-1.5">
          {ca.affected_internal.map((it, i) => (
            <li
              key={i}
              className="rounded-lg border border-line bg-white/[0.02] px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="truncate text-white/85">
                  {it.title ?? "(redacted)"}
                </span>
                <span className="ml-2 shrink-0 text-[10px] text-white/40">
                  {it.score.toFixed(2)}
                </span>
              </div>
              <p className="mt-1 line-clamp-3 text-[11px] text-white/55">
                {it.snippet}
              </p>
              {(it.section || it.department) && (
                <div className="mt-1 flex gap-2 text-[10px] text-white/40">
                  {it.section && <span>§ {it.section}</span>}
                  {it.department && <span>· {it.department}</span>}
                </div>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Section
        title="External basis"
        icon={ExternalLink}
        count={ca.external_basis.length}
        defaultOpen={hasExternal}
        empty="No external acts cited."
      >
        <ul className="space-y-1.5">
          {ca.external_basis.map((ex, i) => (
            <li
              key={i}
              className="rounded-lg border border-line bg-white/[0.02] px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="truncate text-white/85">
                  {ex.title ?? ex.authority ?? "external act"}
                </span>
                {ex.authority && (
                  <span className="ml-2 shrink-0 rounded-full bg-white/5 px-1.5 py-[1px] text-[9px] uppercase text-white/55">
                    {ex.authority}
                  </span>
                )}
              </div>
              {ex.source_url && (
                <a
                  href={ex.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 block truncate text-[10px] text-neon/70 hover:text-neon hover:underline"
                >
                  {ex.source_url}
                </a>
              )}
              <p className="mt-1 line-clamp-3 text-[11px] text-white/55">
                {ex.snippet}
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        title="Conflicts"
        icon={GitCompare}
        count={ca.conflicts.length}
        defaultOpen={hasConflicts}
        empty="Hech qanday konflikt aniqlanmadi (yoki Metodist hali strukturalashgan diff bermayapti)."
      >
        <ul className="space-y-1.5">
          {ca.conflicts.map((c, i) => (
            <li
              key={i}
              className="rounded-lg border border-amber/30 bg-amber-soft px-3 py-2 text-xs"
            >
              <div className="text-[10px] font-medium uppercase tracking-wider text-amber">
                {c.internal_ref} ⇄ {c.external_ref}
              </div>
              <p className="mt-1 text-white/85">{c.why}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        title="Recommendations"
        icon={Lightbulb}
        count={ca.recommendations.length}
        defaultOpen={hasRecs}
        empty="Hech qanday tavsiya yo'q (Metodist strukturalashgan tavsiya bermagan)."
      >
        <ul className="space-y-1.5">
          {ca.recommendations.map((r, i) => (
            <li
              key={i}
              className="rounded-lg border border-neon/30 bg-neon-soft px-3 py-2 text-xs"
            >
              <div className="text-[10px] font-medium uppercase tracking-wider text-neon">
                {r.action}
                {r.target_doc && <span className="ml-2 text-white/55">{r.target_doc}</span>}
                {r.target_clause && <span className="text-white/40"> § {r.target_clause}</span>}
              </div>
              <p className="mt-1 text-white/85">{r.suggested_text}</p>
            </li>
          ))}
        </ul>
      </Section>

      <div className="border-t border-line pt-2 text-[10px] text-white/35">
        {response.agents_used.join(" · ")} · {response.ms_total}ms
      </div>
    </div>
  );
}

// ───────────────────────── Section helper ───────────────────────────────

function Section({
  title,
  icon: Icon,
  count,
  defaultOpen,
  empty,
  children,
}: {
  title: string;
  icon: typeof Building2;
  count: number;
  defaultOpen: boolean;
  empty: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-md px-1 py-1 text-left text-[10px] uppercase tracking-[0.18em] text-white/45 transition hover:bg-white/[0.02] hover:text-white/70"
      >
        <span className="flex items-center gap-1.5">
          <Icon size={11} />
          {title}
          <span className="ml-1 text-white/30">({count})</span>
        </span>
        <ChevronDown
          size={11}
          className={`transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="mt-1.5">
          {count === 0 ? (
            <p className="px-2 py-1 text-[11px] italic text-white/30">{empty}</p>
          ) : (
            children
          )}
        </div>
      )}
    </section>
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

// ───────────────────────── Plain-text export ────────────────────────────

function renderText(r: ChatResponse): string {
  // If the structured case_analysis is present, prefer that as the source
  // of truth for the copy / Word export — it's better organised than the
  // raw agent payload dump.
  const ca = r.case_analysis;
  if (ca) {
    const parts: string[] = [];
    if (ca.summary) parts.push(ca.summary);
    if (ca.affected_departments.length) {
      parts.push("Affected departments: " + ca.affected_departments.join(", "));
    }
    if (ca.affected_internal.length) {
      parts.push(
        "Affected internal documents:\n" +
          ca.affected_internal
            .map(
              (i, n) =>
                `  ${n + 1}. ${i.title ?? "(redacted)"}` +
                (i.section ? ` · § ${i.section}` : "") +
                (i.department ? ` · ${i.department}` : "") +
                `\n     ${i.snippet}`,
            )
            .join("\n"),
      );
    }
    if (ca.external_basis.length) {
      parts.push(
        "External basis:\n" +
          ca.external_basis
            .map(
              (e, n) =>
                `  ${n + 1}. ${e.title ?? "external act"} (${e.authority ?? "—"})` +
                (e.source_url ? `\n     ${e.source_url}` : "") +
                `\n     ${e.snippet}`,
            )
            .join("\n"),
      );
    }
    if (ca.conflicts.length) {
      parts.push(
        "Conflicts:\n" +
          ca.conflicts
            .map(
              (c, n) =>
                `  ${n + 1}. ${c.internal_ref} ⇄ ${c.external_ref}\n     ${c.why}`,
            )
            .join("\n"),
      );
    }
    if (ca.recommendations.length) {
      parts.push(
        "Recommendations:\n" +
          ca.recommendations
            .map(
              (r, n) =>
                `  ${n + 1}. ${r.action}` +
                (r.target_doc ? ` — ${r.target_doc}` : "") +
                (r.target_clause ? ` § ${r.target_clause}` : "") +
                `\n     ${r.suggested_text}`,
            )
            .join("\n"),
      );
    }
    return parts.join("\n\n");
  }

  // Fallback: dump the raw agent payload.
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
