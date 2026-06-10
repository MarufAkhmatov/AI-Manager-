"use client";

import { useState } from "react";
import { AVATARS, type AgentSlug } from "@/components/avatars";

interface Props {
  slug: AgentSlug;
  size: number;
  className?: string;
}

// Renders the character portrait at /avatars/<slug>.png. Falls back to the
// hand-drawn inline SVG (components/avatars/index.tsx) if the PNG is missing,
// so the dashboard still ships before the operator drops their assets in.
export function AgentAvatar({ slug, size, className }: Props) {
  const [failed, setFailed] = useState(false);
  const Fallback = AVATARS[slug];

  if (failed) {
    return <Fallback width={size} height={size} className={className} />;
  }

  return (
    <img
      src={`/avatars/${slug}.png`}
      alt={slug}
      width={size}
      height={size}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
