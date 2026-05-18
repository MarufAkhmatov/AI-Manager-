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
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-accent !border-0 !w-1.5 !h-1.5 !opacity-50"
      />
      <AgentCard
        slug={data.slug}
        name={data.name}
        role={data.role}
        active={data.active}
        size={data.size}
        asLink={true}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-accent !border-0 !w-1.5 !h-1.5 !opacity-50"
      />
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

// Ordered left-to-right around the fan. Intake on the far left, egress on
// the far right; analysis agents at the bottom of the arc.
const FAN: AgentSpec[] = [
  { slug: "architect", name: "AI Architect", role: "Pipeline" },     // leftmost
  { slug: "searcher", name: "AI Searcher", role: "Retrieval" },
  { slug: "metodist", name: "AI Metodist", role: "Normative" },
  { slug: "shadow", name: "AI Shadow", role: "Confidential" },
  { slug: "regulyator", name: "AI Regulyator", role: "External" },
  { slug: "secure", name: "AI Secure", role: "Egress" },             // rightmost
];

// Fan geometry — half-circle arc opening downward, Manager at top centre.
const ARC_RADIUS = 360;
const ARC_CENTER_Y = 80;
const CARD_HALF_W_MANAGER = 112;  // lg card ≈ 224 wide
const CARD_HALF_W_SUB = 88;       // md card ≈ 176 wide
const CARD_HALF_H = 95;

function fanPosition(i: number, total: number) {
  // theta sweeps from ~165° (left) down to ~15° (right) so node 0 is
  // leftmost. Step is (180° − 2×padding) / (total − 1).
  const padDeg = 15;
  const startDeg = 180 - padDeg;
  const endDeg = padDeg;
  const t = total === 1 ? 0 : i / (total - 1);
  const deg = startDeg + (endDeg - startDeg) * t;
  const rad = (deg * Math.PI) / 180;
  return {
    x: Math.cos(rad) * ARC_RADIUS - CARD_HALF_W_SUB,
    y: ARC_CENTER_Y + Math.sin(rad) * ARC_RADIUS * 0.78 - CARD_HALF_H,
  };
}

interface Props {
  activeAgents?: string[];
  className?: string;
}

export function AgentWorkflow({ activeAgents = [], className }: Props) {
  const active = useMemo(() => new Set(activeAgents), [activeAgents]);

  const { nodes, edges } = useMemo(() => {
    const managerNode: Node<AgentNodeData> = {
      id: "manager",
      type: "agent",
      position: { x: -CARD_HALF_W_MANAGER, y: -CARD_HALF_H },
      data: { ...MANAGER, active: active.has(MANAGER.name), size: "lg" },
      draggable: false,
      selectable: false,
    };

    const fanNodes: Node<AgentNodeData>[] = FAN.map((s, i) => ({
      id: s.slug,
      type: "agent",
      position: fanPosition(i, FAN.length),
      data: { ...s, active: active.has(s.name), size: "md" },
      draggable: false,
      selectable: false,
    }));

    // Manager → every sub-agent.
    const fanEdges: Edge[] = FAN.map((s) => ({
      id: `mgr-${s.slug}`,
      source: "manager",
      target: s.slug,
      type: "smoothstep",
      animated: active.has(s.name),
      style: { strokeWidth: 1.4 },
    }));

    // Secure → Manager dashed return (egress sanitisation loop).
    fanEdges.push({
      id: "secure-return",
      source: "secure",
      target: "manager",
      type: "smoothstep",
      animated: active.has("AI Secure"),
      style: { strokeWidth: 1.4, strokeDasharray: "5 5" },
    });

    return { nodes: [managerNode, ...fanNodes], edges: fanEdges };
  }, [active]);

  return (
    <div className={`neo h-full w-full overflow-hidden ${className ?? ""}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.16 }}
        panOnDrag
        zoomOnScroll
        zoomOnPinch
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        minZoom={0.4}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={22}
          color="var(--line)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
