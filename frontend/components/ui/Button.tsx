import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost";

export function Button({
  className,
  variant = "primary",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2 text-sm font-medium transition",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary"
          ? "bg-neon text-black shadow-neon-sm hover:bg-neon/90 hover:shadow-neon-md active:translate-y-px"
          : "border border-line text-text-dim hover:text-white hover:border-neon",
        className,
      )}
      {...rest}
    />
  );
}
