"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";

interface Props {
  activeAgents: string[];
}

const AGENTS = [
  "AI Manager",
  "AI Searcher",
  "AI Metodist",
  "AI Shadow",
  "AI Regulyator",
  "AI Architect",
  "AI Secure",
];

function nodeFor(agent: string, i: number, active: boolean): Node {
  const angle = (i / (AGENTS.length - 1)) * Math.PI;
  return {
    id: agent,
    position: {
      x: agent === "AI Manager" ? 360 : 360 + Math.cos(angle) * 260,
      y: agent === "AI Manager" ? 60 : 260 + Math.sin(angle) * 120,
    },
    data: { label: agent },
    style: {
      padding: 10,
      borderRadius: 16,
      background: active ? "#0a0a0a" : "#121212",
      color: active ? "#7CE7FF" : "#cccccc",
      border: active ? "1px solid #7CE7FF" : "1px solid rgba(255,255,255,0.06)",
      boxShadow: active
        ? "0 0 24px rgba(124,231,255,0.25), 0 0 0 1px rgba(124,231,255,0.4)"
        : "8px 8px 24px rgba(0,0,0,0.5)",
      fontSize: 12,
      width: 140,
      textAlign: "center" as const,
    },
  };
}

export function WorkflowCanvas({ activeAgents }: Props) {
  const { nodes, edges } = useMemo(() => {
    const set = new Set(activeAgents);
    const n: Node[] = AGENTS.map((a, i) => nodeFor(a, i, set.has(a)));
    const e: Edge[] = AGENTS.filter((a) => a !== "AI Manager").map((a) => ({
      id: `mgr-${a}`,
      source: "AI Manager",
      target: a,
      animated: set.has(a),
      className: set.has(a) ? "active" : undefined,
    }));
    e.push({
      id: "secure-out",
      source: "AI Secure",
      target: "AI Manager",
      animated: set.has("AI Secure"),
      style: { strokeDasharray: "4 4" },
    });
    return { nodes: n, edges: e };
  }, [activeAgents]);

  return (
    <div className="neo h-full w-full overflow-hidden">
      <ReactFlow nodes={nodes} edges={edges} fitView panOnDrag={false} nodesDraggable={false}>
        <Background variant={BackgroundVariant.Dots} gap={18} color="rgba(255,255,255,0.06)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
