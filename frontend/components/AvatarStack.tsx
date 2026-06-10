"use client";

import { AgentAvatar } from "@/components/AgentAvatar";
import type { AgentSlug } from "@/components/avatars";
import { cn } from "@/lib/cn";

interface Item {
  slug: AgentSlug;
  name: string;
  active?: boolean;
}

interface Props {
  items: Item[];
  size?: number;
  className?: string;
}

// Overlapping circular portraits — sits above the Recommendation panel and
// shows which agents contributed to the current response. Active agents
// glow neon; idle ones fade.
export function AvatarStack({ items, size = 28, className }: Props) {
  return (
    <div className={cn("flex items-center", className)}>
      {items.map((it, i) => (
        <div
          key={it.slug}
          title={it.name}
          className={cn(
            "overflow-hidden rounded-full border-2 transition-all",
            it.active
              ? "border-neon shadow-neon-sm"
              : "border-bg opacity-60 grayscale",
          )}
          style={{
            width: size,
            height: size,
            marginLeft: i === 0 ? 0 : -size * 0.35,
            zIndex: items.length - i,
          }}
        >
          <AgentAvatar slug={it.slug} size={size} className="h-full w-full object-cover" />
        </div>
      ))}
    </div>
  );
}
