"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";

import { AgentCard } from "@/components/AgentCard";
import type { AgentSlug } from "@/components/avatars";

interface AgentNodeData {
  slug: AgentSlug;
  name: string;
  role: string;
  active: boolean;
  size: "sm" | "md" | "lg";
}

function AgentFlowNode({ data }: NodeProps<AgentNodeData>) {
  return (
    <div className="relative">
      <Handle type="target" position={Position.Top} className="!bg-accent !border-0 !w-2 !h-2" />
      <AgentCard
        slug={data.slug}
        name={data.name}
        role={data.role}
        active={data.active}
        size={data.size}
        asLink={true}
      />
      <Handle type="source" position={Position.Bottom} className="!bg-accent !border-0 !w-2 !h-2" />
    </div>
  );
}

const NODE_TYPES = { agent: AgentFlowNode };

interface AgentSpec {
  slug: AgentSlug;
  name: string;
  role: string;
}

const MANAGER: AgentSpec = { slug: "manager", name: "AI Manager", role: "Team Lead" };

const SUBS: AgentSpec[] = [
  { slug: "architect", name: "AI Architect", role: "Pipeline" },
  { slug: "searcher", name: "AI Searcher", role: "Retrieval" },
  { slug: "metodist", name: "AI Metodist", role: "Normative" },
  { slug: "shadow", name: "AI Shadow", role: "Confidential" },
  { slug: "secure", name: "AI Secure", role: "Egress Guard" },
  { slug: "regulyator", name: "AI Regulyator", role: "External" },
];

interface Props {
  activeAgents?: string[];
  className?: string;
}

export function AgentOrgChart({ activeAgents = [], className }: Props) {
  const active = useMemo(() => new Set(activeAgents), [activeAgents]);

  const { nodes, edges } = useMemo(() => {
    const COL_W = 220;
    const totalWidth = SUBS.length * COL_W;
    const leftPad = -totalWidth / 2 + COL_W / 2;

    const managerNode: Node<AgentNodeData> = {
      id: "manager",
      type: "agent",
      position: { x: -110, y: 0 },
      data: { ...MANAGER, active: active.has(MANAGER.name), size: "lg" },
      draggable: false,
    };

    const subNodes: Node<AgentNodeData>[] = SUBS.map((s, i) => ({
      id: s.slug,
      type: "agent",
      position: { x: leftPad + i * COL_W - 88, y: 280 },
      data: { ...s, active: active.has(s.name), size: "md" },
      draggable: false,
    }));

    const subEdges: Edge[] = SUBS.map((s) => ({
      id: `mgr-${s.slug}`,
      source: "manager",
      target: s.slug,
      type: "smoothstep",
      animated: active.has(s.name),
      style: { strokeWidth: 1.6 },
    }));

    return {
      nodes: [managerNode, ...subNodes],
      edges: subEdges,
    };
  }, [active]);

  return (
    <div className={`neo h-full w-full overflow-hidden ${className ?? ""}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        panOnDrag
        zoomOnScroll
        zoomOnPinch
        minZoom={0.4}
        maxZoom={1.4}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} color="rgba(34,213,143,0.10)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
