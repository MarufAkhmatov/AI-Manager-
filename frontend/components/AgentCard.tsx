"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { AVATARS, type AgentSlug } from "@/components/avatars";
import { cn } from "@/lib/cn";

interface AgentCardProps {
  slug: AgentSlug;
  name: string;
  role?: string;          // e.g. "Team Lead", "Specialist"
  active?: boolean;       // pulses + accent ring
  size?: "sm" | "md" | "lg";
  asLink?: boolean;       // wrap in Link to /agents/[slug]
}

const SIZES = {
  sm: { card: "w-36 p-3", avatar: 56, name: "text-xs", role: "text-[10px]" },
  md: { card: "w-44 p-4", avatar: 72, name: "text-sm", role: "text-[11px]" },
  lg: { card: "w-56 p-5", avatar: 96, name: "text-base", role: "text-xs" },
} as const;

export function AgentCard({
  slug,
  name,
  role,
  active,
  size = "md",
  asLink = true,
}: AgentCardProps) {
  const Avatar = AVATARS[slug];
  const dims = SIZES[size];

  const body = (
    <motion.div
      initial={false}
      animate={active ? { scale: [1, 1.03, 1] } : { scale: 1 }}
      transition={{ duration: 1.6, repeat: active ? Infinity : 0 }}
      className={cn(
        "neo group flex flex-col items-center gap-2",
        "transition-shadow hover:accent-pulse",
        active && "accent-pulse",
        dims.card,
      )}
      style={{ borderRadius: 22 }}
    >
      <div
        className={cn(
          "rounded-full overflow-hidden border border-line",
          "bg-surface-2 shadow-neo-in",
        )}
        style={{ width: dims.avatar, height: dims.avatar }}
      >
        <Avatar width={dims.avatar} height={dims.avatar} />
      </div>
      <div className="flex flex-col items-center">
        <span className={cn("font-medium text-text", dims.name)}>{name}</span>
        {role && (
          <span className={cn("text-text-dim mt-0.5 uppercase tracking-wider", dims.role)}>
            {role}
          </span>
        )}
      </div>
    </motion.div>
  );

  if (!asLink) return body;
  return (
    <Link href={`/agents/${slug}`} className="block">
      {body}
    </Link>
  );
}
