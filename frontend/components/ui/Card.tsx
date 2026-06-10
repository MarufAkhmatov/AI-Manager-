import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Two surfaces matching the workflow theme: GlassCard for floating panels,
// NeoCard for the slightly more solid blocks used on the per-agent and KB
// pages. Both share the line/border tone with the rest of the dashboard.

export function GlassCard({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-line bg-black/40 p-6 backdrop-blur-xl",
        className,
      )}
      {...rest}
    />
  );
}

export function NeoCard({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-line bg-surface-2 p-6",
        className,
      )}
      {...rest}
    />
  );
}
