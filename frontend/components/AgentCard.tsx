"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { AgentAvatar } from "@/components/AgentAvatar";
import type { AgentSlug } from "@/components/avatars";
import { cn } from "@/lib/cn";

export type AgentStatus = "online" | "idle" | "active" | "error";

interface AgentCardProps {
  slug: AgentSlug;
  name: string;          // e.g. "AI MANAGER"
  role?: string;         // e.g. "Team Lead" / "Sub Agent"
  status?: AgentStatus;  // drives the corner dot
  active?: boolean;      // accent-pulse + scale animation
  size?: "sm" | "md" | "lg";
  asLink?: boolean;
}

const SIZES = {
  sm: { card: "w-32", pad: "p-3", avatar: 56, name: "text-[11px]", role: "text-[9px]" },
  md: { card: "w-36", pad: "p-3", avatar: 64, name: "text-xs", role: "text-[9px]" },
  lg: { card: "w-44", pad: "p-4", avatar: 80, name: "text-sm", role: "text-[10px]" },
} as const;

const DOT_COLOR: Record<AgentStatus, string> = {
  online: "bg-[#0CF500]",
  active: "bg-[#F5DC00]",
  idle:   "bg-[#F5DC00]",
  error:  "bg-[#F50000]",
};

export function AgentCard({
  slug,
  name,
  role,
  status = "idle",
  active = false,
  size = "md",
  asLink = true,
}: AgentCardProps) {
  const dims = SIZES[size];

  const body = (
    <motion.div
      initial={false}
      animate={active ? { scale: [1, 1.025, 1] } : { scale: 1 }}
      transition={{ duration: 1.6, repeat: active ? Infinity : 0 }}
      className={cn(
        "relative flex flex-col items-center gap-2 rounded-2xl border bg-[#0E0E11]",
        "transition-shadow hover:border-white/20",
        active ? "border-[#F5DC00]/70 shadow-[0_0_0_1px_rgba(245,220,0,0.35),0_0_22px_rgba(245,220,0,0.18)]"
               : "border-white/10",
        dims.card,
        dims.pad,
      )}
    >
      <div
        className="overflow-hidden rounded-full ring-1 ring-white/15"
        style={{ width: dims.avatar, height: dims.avatar }}
      >
        <AgentAvatar slug={slug} size={dims.avatar} className="h-full w-full object-cover" />
      </div>

      <div className="flex flex-col items-center leading-tight">
        {role && (
          <span className={cn("uppercase tracking-[0.18em] text-white/45", dims.role)}>
            {role}
          </span>
        )}
        <span className={cn("font-semibold uppercase tracking-wider text-white", dims.name)}>
          {name}
        </span>
      </div>

      <span
        aria-label={`status ${status}`}
        className={cn(
          "absolute bottom-2.5 right-3 h-1.5 w-1.5 rounded-full",
          DOT_COLOR[status],
          status === "online" && "shadow-[0_0_8px_rgba(12,245,0,0.7)]",
          active && status !== "online" && "shadow-[0_0_8px_rgba(245,220,0,0.7)]",
        )}
      />
    </motion.div>
  );

  if (!asLink) return body;
  return (
    <Link href={`/agents/${slug}`} className="block">
      {body}
    </Link>
  );
}
