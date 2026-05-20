"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, GitCompare, Lightbulb, X } from "lucide-react";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "@/lib/api";

interface Props {
  // Bumping this number triggers an immediate refetch — the dashboard
  // increments it when a `audit.finding` WS event arrives.
  refreshSignal: number;
  onView(item: NotificationItem): void;
}

const POLL_MS = 20_000;

export function NotificationsBell({ refreshSignal, onView }: Props) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetchNotifications();
      setItems(res.items);
      setUnread(res.unread);
    } catch {
      /* network / auth errors are handled elsewhere; bell stays quiet */
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  // Refetch when the dashboard signals a fresh audit.finding event.
  useEffect(() => {
    if (refreshSignal > 0) void load();
  }, [refreshSignal, load]);

  // Close on outside click.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  async function handleView(item: NotificationItem) {
    onView(item);
    setOpen(false);
    if (!item.read) {
      try {
        await markNotificationRead(item.id);
        setItems((prev) =>
          prev.map((n) => (n.id === item.id ? { ...n, read: true } : n)),
        );
        setUnread((u) => Math.max(0, u - 1));
      } catch {
        /* ignore */
      }
    }
  }

  async function handleMarkAll() {
    try {
      await markAllNotificationsRead();
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    } catch {
      /* ignore */
    }
  }

  return (
    <div ref={boxRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        className="relative grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-white/70 transition hover:text-white"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full border-2 border-bg bg-danger px-1 text-[9px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[360px] overflow-hidden rounded-2xl border border-line bg-[#0b0b0d] shadow-[0_8px_40px_rgba(0,0,0,0.6)]">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
              Audit findings
            </span>
            <div className="flex items-center gap-2">
              {unread > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAll}
                  className="text-[10px] text-neon/80 hover:text-neon"
                >
                  Mark all read
                </button>
              )}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-white/40 hover:text-white"
                aria-label="Close"
              >
                <X size={13} />
              </button>
            </div>
          </div>

          <div className="max-h-[420px] overflow-y-auto scrollbar-thin">
            {items.length === 0 ? (
              <div className="grid h-24 place-items-center px-6 text-center text-xs text-white/35">
                Hozircha audit topilmadi. AI Regulyator yangi normativ akt
                olganda bu yerda paydo bo&apos;ladi.
              </div>
            ) : (
              <ul>
                {items.map((n) => {
                  const conflicts = n.case_analysis?.conflicts?.length ?? 0;
                  const recs = n.case_analysis?.recommendations?.length ?? 0;
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => handleView(n)}
                        className={`flex w-full flex-col gap-1 border-b border-line px-4 py-3 text-left transition hover:bg-white/[0.03] ${
                          n.read ? "opacity-60" : ""
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          {!n.read && (
                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-neon shadow-neon-sm" />
                          )}
                          <span className="text-xs font-medium text-white/90">
                            {n.title}
                          </span>
                        </div>
                        <p className="line-clamp-2 pl-3.5 text-[11px] text-white/50">
                          {n.summary}
                        </p>
                        <div className="flex items-center gap-3 pl-3.5 text-[10px] text-white/40">
                          <span className="flex items-center gap-1">
                            <GitCompare size={10} /> {conflicts}
                          </span>
                          <span className="flex items-center gap-1">
                            <Lightbulb size={10} /> {recs}
                          </span>
                          {n.source_url && (
                            <span className="truncate text-neon/60">
                              {new URL(n.source_url).host}
                            </span>
                          )}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
