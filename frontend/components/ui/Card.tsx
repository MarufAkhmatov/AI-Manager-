import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function GlassCard({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass p-6", className)} {...rest} />;
}

export function NeoCard({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("neo p-6", className)} {...rest} />;
}
