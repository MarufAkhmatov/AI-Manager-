"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { NeoCard } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

interface Stats {
  total: number;
  by_category: Record<string, number>;
}
interface Doc {
  id: string | null;
  title: string | null;
  category: string;
  authority: string | null;
  status: string;
  issued_at: string | null;
  is_confidential: boolean;
}

export default function KbPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const [s, d] = await Promise.all([
        api<Stats>("/api/kb/stats"),
        api<Doc[]>("/api/kb/documents"),
      ]);
      setStats(s);
      setDocs(d);
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);

  async function reindex() {
    setBusy(true);
    try {
      await api("/api/kb/reindex", { method: "POST" });
      await refresh();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen p-8">
      <header className="mb-8 flex items-center justify-between">
        <Link href="/dashboard" className="text-sm text-bone-200 hover:text-accent">
          ← Dashboard
        </Link>
        <Button variant="ghost" onClick={reindex} disabled={busy}>
          {busy ? "Reindexing…" : "Reindex (admin)"}
        </Button>
      </header>

      {stats && (
        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-4">
          <NeoCard>
            <div className="text-xs uppercase tracking-wider text-bone-300">Total</div>
            <div className="mt-2 text-3xl font-semibold">{stats.total}</div>
          </NeoCard>
          {Object.entries(stats.by_category).map(([k, v]) => (
            <NeoCard key={k}>
              <div className="text-xs uppercase tracking-wider text-bone-300">{k}</div>
              <div className="mt-2 text-3xl font-semibold">{v}</div>
            </NeoCard>
          ))}
        </div>
      )}

      {err && <p className="text-xs text-red-400">{err}</p>}

      <NeoCard className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-bone-300">
            <tr>
              <th className="pb-3">Title</th>
              <th className="pb-3">Category</th>
              <th className="pb-3">Authority</th>
              <th className="pb-3">Issued</th>
              <th className="pb-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d, i) => (
              <tr key={d.id ?? i} className="border-t border-white/5">
                <td className="py-2">{d.title ?? "—"}</td>
                <td className="py-2">{d.category}</td>
                <td className="py-2">{d.authority ?? "—"}</td>
                <td className="py-2">{d.issued_at ?? "—"}</td>
                <td className="py-2">
                  <span
                    className={
                      d.is_confidential
                        ? "rounded-full bg-white/5 px-2 py-0.5 text-xs text-accent"
                        : "rounded-full bg-white/5 px-2 py-0.5 text-xs text-bone-200"
                    }
                  >
                    {d.is_confidential ? "lotus" : d.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </NeoCard>
    </main>
  );
}
