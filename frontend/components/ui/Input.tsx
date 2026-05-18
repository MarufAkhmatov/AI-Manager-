import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "neo-in w-full px-4 py-3 text-sm text-text placeholder:text-text-dim",
        "outline-none focus:accent-pulse",
        className,
      )}
      {...rest}
    />
  );
}
