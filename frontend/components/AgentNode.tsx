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
  size?: number;          // avatar diameter — also the bbox size
  asLink?: boolean;
}

// Circular agent portrait with a label rendered ABSOLUTELY below the
// avatar — keeps the bounding box exactly `size × size` so the parent
// can anchor connector endpoints and drag handles to the avatar's true
// centre regardless of how long the name is.
export function AgentNode({
  slug,
  name,
  role,
  active = false,
  size = 88,
  asLink = true,
}: Props) {
  const body = (
    <div className="relative" style={{ width: size, height: size }}>
      <motion.div
        initial={false}
        animate={active ? { scale: [1, 1.04, 1] } : { scale: 1 }}
        transition={{ duration: 1.6, repeat: active ? Infinity : 0 }}
        className="relative h-full w-full"
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
        <div className="relative h-full w-full overflow-hidden rounded-full bg-[#0E0E11]">
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

      {/* Label — absolute so it doesn't widen the bbox. */}
      <div className="pointer-events-none absolute left-1/2 top-full mt-2 flex -translate-x-1/2 flex-col items-center whitespace-nowrap text-center">
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
