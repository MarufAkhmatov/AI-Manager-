import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-line bg-surface-2 px-4 py-3 text-sm text-white placeholder:text-white/40",
        "outline-none transition focus:border-neon/50 focus:ring-1 focus:ring-neon/50",
        className,
      )}
      {...rest}
    />
  );
}
