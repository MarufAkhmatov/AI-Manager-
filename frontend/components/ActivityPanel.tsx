"use client";

import { useEffect, useState } from "react";
import { openActivityWS } from "@/lib/api";

interface ActivityEvent {
  ts: string;
  agent: string;
  event: string;
  task_id: string | null;
  payload: Record<string, unknown>;
}

const MAX_EVENTS = 200;

export function ActivityPanel() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    const ws = openActivityWS();
    ws.onmessage = (msg) => {
      try {
        const ev: ActivityEvent = JSON.parse(msg.data);
        setEvents((prev) => [ev, ...prev].slice(0, MAX_EVENTS));
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="neo p-4 h-full overflow-hidden flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-text-dim">Activity</h3>
        <span className="text-xs text-text-dim">{events.length}</span>
      </div>
      <ul className="flex-1 overflow-y-auto space-y-2 pr-2">
        {events.map((e, i) => (
          <li key={i} className="neo-in px-3 py-2 text-xs">
            <div className="flex items-center justify-between text-text-dim">
              <span className="font-medium text-accent">{e.agent}</span>
              <span className="font-mono text-[10px] text-text-dim">{e.event}</span>
            </div>
            {Object.keys(e.payload).length > 0 && (
              <pre className="mt-1 truncate font-mono text-[10px] text-text-dim">
                {JSON.stringify(e.payload)}
              </pre>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
