"use client";

import { AgentAvatar } from "@/components/AgentAvatar";
import type { AgentSlug } from "@/components/avatars";
import { cn } from "@/lib/cn";

interface Props {
  slugs: AgentSlug[];
  size?: number;
  className?: string;
}

// Cluster of overlapping circular portraits — used as the "team" indicator
// above the Recommendation panel.
export function AvatarStack({ slugs, size = 28, className }: Props) {
  return (
    <div className={cn("flex items-center", className)}>
      {slugs.map((slug, i) => (
        <div
          key={slug}
          className="overflow-hidden rounded-full border border-white/15 bg-[#0E0E11]"
          style={{
            width: size,
            height: size,
            marginLeft: i === 0 ? 0 : -size * 0.35,
            zIndex: slugs.length - i,
          }}
        >
          <AgentAvatar slug={slug} size={size} className="h-full w-full object-cover" />
        </div>
      ))}
    </div>
  );
}
