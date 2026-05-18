"use client";

import { useState } from "react";
import { Maximize2, Minimize2, Minus } from "lucide-react";
import { motion } from "framer-motion";
import { ChatPanel } from "@/components/ChatPanel";
import { cn } from "@/lib/cn";

type Size = "compact" | "normal" | "large";

const HEIGHTS: Record<Size, string> = {
  compact: "h-[180px]",
  normal: "h-[340px]",
  large: "h-[68vh]",
};

interface Props {
  onAgentsActive(agents: string[]): void;
}

export function ResizableChatPanel({ onAgentsActive }: Props) {
  const [size, setSize] = useState<Size>("normal");

  return (
    <motion.section
      layout
      transition={{ type: "spring", stiffness: 220, damping: 28 }}
      className={cn(
        "glass mx-auto flex w-full max-w-4xl flex-col overflow-hidden p-4",
        HEIGHTS[size],
      )}
    >
      <header className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-accent shadow-glow" />
          <span className="text-xs font-medium uppercase tracking-wider text-text-dim">
            AI Manager — chat
          </span>
        </div>
        <div className="flex items-center gap-1">
          <SizeBtn
            label="Compact"
            icon={Minus}
            on={size === "compact"}
            onClick={() => setSize("compact")}
          />
          <SizeBtn
            label="Normal"
            icon={Minimize2}
            on={size === "normal"}
            onClick={() => setSize("normal")}
          />
          <SizeBtn
            label="Large"
            icon={Maximize2}
            on={size === "large"}
            onClick={() => setSize("large")}
          />
        </div>
      </header>
      <div className="flex-1 min-h-0">
        <ChatPanel onAgentsActive={onAgentsActive} />
      </div>
    </motion.section>
  );
}

function SizeBtn({
  label,
  icon: Icon,
  on,
  onClick,
}: {
  label: string;
  icon: typeof Minus;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded-lg transition",
        on
          ? "bg-accent-soft text-accent"
          : "text-text-dim hover:bg-surface hover:text-text",
      )}
    >
      <Icon size={13} />
    </button>
  );
}
