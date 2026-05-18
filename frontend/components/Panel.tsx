"use client";

import { useState, type ReactNode } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface Props {
  title: string;            // e.g. "AI MANAGER  CHAT"
  dotColor?: string;        // header status dot (defaults to green)
  rightSlot?: ReactNode;    // optional extra content right of the title
  expandable?: boolean;     // show maximise toggle (default true)
  className?: string;
  children: ReactNode;
}

// Dark rounded panel matching the Figma frame: header bar with a status dot,
// title in dim caps, optional rightSlot, and a maximise toggle. The body
// switches between normal (340px) and expanded (~70vh) heights.
export function Panel({
  title,
  dotColor = "#0CF500",
  rightSlot,
  expandable = true,
  className,
  children,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const Icon = expanded ? Minimize2 : Maximize2;

  return (
    <section
      className={cn(
        "flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0E0E11]",
        expanded ? "h-[68vh]" : "h-[340px]",
        className,
      )}
    >
      <header className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: dotColor }}
          />
          <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {rightSlot}
          {expandable && (
            <button
              type="button"
              aria-label={expanded ? "Collapse" : "Expand"}
              onClick={() => setExpanded((v) => !v)}
              className="flex h-6 w-6 items-center justify-center rounded-md text-white/45 transition hover:bg-white/5 hover:text-white"
            >
              <Icon size={13} />
            </button>
          )}
        </div>
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
