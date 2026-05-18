"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { AgentAvatar } from "@/components/AgentAvatar";
import type { AgentSlug } from "@/components/avatars";
import { cn } from "@/lib/cn";

interface Props {
  slug: AgentSlug;
  name: string;
  role?: string;
  active?: boolean;
  size?: number;          // avatar diameter
  asLink?: boolean;
}

// Circular agent portrait + name label. Used as the workflow canvas node:
// the avatar is the connector anchor; the label sits underneath; the active
// state pulses a neon ring around the circle, matching the AI-Workflow
// running-state styling.
export function AgentNode({
  slug,
  name,
  role,
  active = false,
  size = 88,
  asLink = true,
}: Props) {
  const body = (
    <div className="flex flex-col items-center">
      <motion.div
        initial={false}
        animate={active ? { scale: [1, 1.04, 1] } : { scale: 1 }}
        transition={{ duration: 1.6, repeat: active ? Infinity : 0 }}
        className="relative"
      >
        {/* outer ring + glow */}
        <div
          className={cn(
            "absolute inset-0 -m-1 rounded-full transition-all duration-500",
            active
              ? "ring-2 ring-neon shadow-neon-md"
              : "ring-1 ring-white/15",
          )}
        />
        <div
          className="relative overflow-hidden rounded-full bg-[#0E0E11]"
          style={{ width: size, height: size }}
        >
          <AgentAvatar
            slug={slug}
            size={size}
            className="h-full w-full object-cover"
          />
        </div>
        {/* status dot */}
        <span
          className={cn(
            "absolute -bottom-0.5 right-0 h-2.5 w-2.5 rounded-full border-2 border-bg transition-colors",
            active ? "bg-neon shadow-neon-sm" : "bg-amber",
          )}
        />
      </motion.div>
      <div className="mt-2 flex flex-col items-center text-center">
        {role && (
          <span className="text-[9px] uppercase tracking-[0.18em] text-white/40">
            {role}
          </span>
        )}
        <span
          className={cn(
            "text-xs font-semibold uppercase tracking-wider transition-colors",
            active ? "text-neon" : "text-white",
          )}
        >
          {name}
        </span>
      </div>
    </div>
  );

  if (!asLink) return body;
  return (
    <Link href={`/agents/${slug}`} className="block">
      {body}
    </Link>
  );
}
