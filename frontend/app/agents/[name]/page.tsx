"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { NeoCard } from "@/components/ui/Card";
import { api } from "@/lib/api";

const DESCRIPTIONS: Record<string, { full: string; blurb: string }> = {
  manager: {
    full: "AI Manager",
    blurb: "Detects intent, dispatches sub-agents in parallel, aggregates, and pipes the result through AI Secure.",
  },
  searcher: {
    full: "AI Searcher",
    blurb: "pgvector top-k retrieval with cosine similarity and a Redis response cache.",
  },
  metodist: {
    full: "AI Metodist",
    blurb: "Normative analysis — flags conflicts, gaps, inconsistencies and the impacted departments.",
  },
  shadow: {
    full: "AI Shadow",
    blurb: "Lotus-only retrieval. Returns summary, date, and authority — never document id, title, path, or source.",
  },
  secure: {
    full: "AI Secure",
    blurb: "Mandatory final node on every response. Masks PII and enforces the Shadow-guard.",
  },
  regulyator: {
    full: "AI Regulyator",
    blurb: "Daily crawl of lex.uz, cbu.uz, and ipakyulibank.uz. Dedupes and supersedes prior versions.",
  },
  architect: {
    full: "AI Architect",
    blurb: "Owns the filesystem and pipeline. Initial scan, watcher, OCR > chunk > embed > store.",
  },
};

interface AgentLog {
  id: number;
  event: string;
  payload: Record<string, unknown>;
  ms_elapsed: number | null;
  created_at: string;
  task_id: string | null;
}

export default function AgentPage({ params }: { params: Promise<{ name: string }> }) {
  const { name } = use(params);
  const meta = DESCRIPTIONS[name];
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!meta) return;
    void api<AgentLog[]>(`/api/agents/${encodeURIComponent(meta.full)}/logs?limit=50`)
      .then(setLogs)
      .catch((e: Error) => setErr(e.message));
  }, [meta]);

  if (!meta) {
    return (
      <main className="p-8">
        <Link href="/dashboard" className="text-sm text-bone-200 hover:text-accent">
          ← Dashboard
        </Link>
        <p className="mt-6 text-bone-300">Unknown agent.</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen p-8">
      <Link href="/dashboard" className="text-sm text-bone-200 hover:text-accent">
        ← Dashboard
      </Link>
      <h1 className="mt-6 text-2xl font-semibold">{meta.full}</h1>
      <p className="mt-2 max-w-2xl text-sm text-bone-200">{meta.blurb}</p>

      <NeoCard className="mt-8">
        <h2 className="mb-4 text-sm uppercase tracking-wider text-bone-300">
          Recent activity
        </h2>
        {err && <p className="text-xs text-red-400">{err}</p>}
        {logs.length === 0 && !err && (
          <p className="text-xs text-bone-400">No events yet.</p>
        )}
        <ul className="space-y-2">
          {logs.map((l) => (
            <li key={l.id} className="neo-in px-3 py-2 text-xs">
              <div className="flex items-center justify-between text-white/70">
                <span className="font-medium text-accent">{l.event}</span>
                <span className="font-mono text-[10px] text-bone-300">
                  {l.ms_elapsed ?? "-"}ms
                </span>
              </div>
              <div className="mt-1 font-mono text-[10px] text-bone-200">
                {new Date(l.created_at).toLocaleTimeString()}
              </div>
            </li>
          ))}
        </ul>
      </NeoCard>
    </main>
  );
}
