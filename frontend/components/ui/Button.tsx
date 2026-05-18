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
        "inline-flex items-center justify-center gap-2 rounded-2xl px-5 py-2 text-sm font-medium transition",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary"
          ? "bg-accent text-[#03150b] hover:bg-accent-dim active:translate-y-px"
          : "border border-line text-text-dim hover:text-text hover:border-accent",
        className,
      )}
      {...rest}
    />
  );
}
