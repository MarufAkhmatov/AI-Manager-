"use client";

import type { ChatResponse } from "@/components/ChatPanel";

interface Props {
  response: ChatResponse | null;
}

interface MetodistFinding {
  kind?: string;
  severity?: string;
  message?: string;
  impacted_departments?: string[];
}

// Read-only feed derived from the most recent /api/chat reply. We surface
// Metodist's structured findings first (those are the actual operator-facing
// recommendations), then a short citations list. AI Secure has already passed
// over this payload by the time it reaches the client.
export function RecommendationPanel({ response }: Props) {
  if (!response) {
    return (
      <div className="grid h-full place-items-center px-6 text-center text-xs text-white/35">
        Tavsiyalar bu yerda chiqadi. <br />
        AI Manager&apos;ga savol bering — Metodist xulosalari va manbalar shu panelga keladi.
      </div>
    );
  }

  const agents = (response.response as { agents?: Record<string, unknown> }).agents ?? {};
  const metodist = agents["metodist"] as { findings?: MetodistFinding[] } | undefined;
  const findings = metodist?.findings ?? [];

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto px-4 py-3 scrollbar-thin">
      {findings.length > 0 && (
        <section>
          <h4 className="mb-2 text-[10px] uppercase tracking-[0.18em] text-white/40">
            Findings
          </h4>
          <ul className="space-y-2">
            {findings.map((f, i) => (
              <li
                key={i}
                className="rounded-xl border border-white/10 bg-white/[0.02] px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-white/45">
                    {f.kind ?? "finding"}
                  </span>
                  {f.severity && (
                    <SeverityPill severity={f.severity} />
                  )}
                </div>
                <p className="mt-1 text-sm text-white/85">{f.message}</p>
                {f.impacted_departments && f.impacted_departments.length > 0 && (
                  <p className="mt-1 text-[11px] text-white/40">
                    Impacts: {f.impacted_departments.join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {response.citations.length > 0 && (
        <section>
          <h4 className="mb-2 text-[10px] uppercase tracking-[0.18em] text-white/40">
            Sources
          </h4>
          <ul className="space-y-2">
            {response.citations.map((c, i) => (
              <li
                key={i}
                className="rounded-xl border border-white/5 bg-black/40 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="truncate text-xs text-white/85">
                    {c.title ?? "(redacted)"}
                  </span>
                  <span className="ml-2 shrink-0 text-[10px] text-white/40">
                    {c.score.toFixed(2)}
                  </span>
                </div>
                {c.snippet && (
                  <p className="mt-1 line-clamp-3 text-[11px] text-white/55">
                    {c.snippet}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-auto pt-1 text-[10px] text-white/30">
        {response.agents_used.join(" · ")} · {response.ms_total}ms
      </div>
    </div>
  );
}

function SeverityPill({ severity }: { severity: string }) {
  const tone =
    severity === "high" || severity === "critical"
      ? "bg-[#F50000]/15 text-[#F50000] border-[#F50000]/30"
      : severity === "medium"
        ? "bg-[#F5DC00]/15 text-[#F5DC00] border-[#F5DC00]/30"
        : "bg-white/5 text-white/60 border-white/10";
  return (
    <span
      className={`rounded-full border px-2 py-[1px] text-[9px] uppercase tracking-wider ${tone}`}
    >
      {severity}
    </span>
  );
}
