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
          ? "bg-white text-black hover:bg-bone-100 active:bg-bone-200"
          : "border border-white/10 text-white/80 hover:text-white hover:border-white/20",
        className,
      )}
      {...rest}
    />
  );
}
