"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

export interface AgentNodeProps {
  name: string;
  slug: string;
  active?: boolean;
  size?: number;
}

export function AgentNode({ name, slug, active, size = 120 }: AgentNodeProps) {
  return (
    <Link href={`/agents/${slug}`} className="group block">
      <motion.div
        initial={false}
        animate={active ? { scale: [1, 1.03, 1] } : { scale: 1 }}
        transition={{ duration: 1.4, repeat: active ? Infinity : 0 }}
        className={cn(
          "neo flex items-center justify-center rounded-full text-center",
          "transition-shadow group-hover:accent-pulse",
          active && "accent-pulse",
        )}
        style={{ width: size, height: size }}
      >
        <span className="px-3 text-xs font-medium leading-tight text-white/90">
          {name}
        </span>
      </motion.div>
    </Link>
  );
}
