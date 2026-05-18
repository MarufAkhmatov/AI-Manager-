"use client";

import { useState } from "react";
import Link from "next/link";
import { ActivityPanel } from "@/components/ActivityPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";

export default function ManagerPage() {
  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  return (
    <main className="grid h-screen grid-cols-[260px_1fr_360px] gap-4 p-4">
      <aside className="neo p-4">
        <Link href="/dashboard" className="block text-sm text-bone-200 hover:text-accent">
          ← Dashboard
        </Link>
        <h2 className="mt-6 text-xs uppercase tracking-wider text-bone-300">
          Conversations
        </h2>
        <p className="mt-2 text-xs text-bone-400">
          Multi-conversation history is local-only and lands in a follow-up.
        </p>
      </aside>

      <section className="grid grid-rows-[1fr_280px] gap-4">
        <div className="neo p-4">
          <ChatPanel onAgentsActive={setActiveAgents} />
        </div>
        <div>
          <WorkflowCanvas activeAgents={activeAgents} />
        </div>
      </section>

      <aside>
        <ActivityPanel />
      </aside>
    </main>
  );
}
