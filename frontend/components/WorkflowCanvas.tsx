"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AgentNode } from "@/components/AgentNode";
import { ChatPanel, type ChatResponse } from "@/components/ChatPanel";
import type { AgentSlug } from "@/components/avatars";

// ────────────────────────────────────────────────────────────────────
// Layout
// ────────────────────────────────────────────────────────────────────
const MANAGER_SIZE = 132;
const SUB_SIZE = 92;
const RADIUS = 280; // manager-centre to sub-agent-centre
const CHAT_W = 340;
const CHAT_H = 400;

// Order around the circle, starting at -90° (top) clockwise so the operator
// reads it like a clock face.
const SUBS: Array<{ slug: AgentSlug; name: string; angle: number }> = [
  { slug: "architect",  name: "AI Architect",  angle: -90 },
  { slug: "metodist",   name: "AI Metodist",   angle: -30 },
  { slug: "searcher",   name: "AI Searcher",   angle: 30 },
  { slug: "shadow",     name: "AI Shadow",     angle: 90 },
  { slug: "regulyator", name: "AI Regulyator", angle: 150 },
  { slug: "secure",     name: "AI Secure",     angle: 210 },
];

interface Pos { x: number; y: number }

function radial(cx: number, cy: number, angleDeg: number, r: number): Pos {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + Math.cos(rad) * r, y: cy + Math.sin(rad) * r };
}

function initialPositions(w: number, h: number): Record<string, Pos> {
  // Manager sits slightly above the canvas centre so the chat panel can live
  // in the lower-left without overlapping the radial cluster.
  const cx = w / 2;
  const cy = Math.max(h / 2 - 40, 280);

  const positions: Record<string, Pos> = {
    // top-left of the manager card
    manager: { x: cx - MANAGER_SIZE / 2, y: cy - MANAGER_SIZE / 2 },
    // chat lives bottom-left
    chat: { x: 32, y: h - CHAT_H - 32 },
  };
  for (const s of SUBS) {
    const c = radial(cx, cy, s.angle, RADIUS);
    positions[s.slug] = { x: c.x - SUB_SIZE / 2, y: c.y - SUB_SIZE / 2 };
  }
  return positions;
}

// Centre of a node, used as the connector endpoint.
function nodeCentre(id: string, p: Pos): Pos {
  if (id === "manager") return { x: p.x + MANAGER_SIZE / 2, y: p.y + MANAGER_SIZE / 2 };
  if (id === "chat")    return { x: p.x + CHAT_W / 2,        y: p.y };
  return { x: p.x + SUB_SIZE / 2, y: p.y + SUB_SIZE / 2 };
}

// Smooth bezier between two centres, biased so the curve flows out along the
// line to the destination — gives the connectors a clean organic shape
// instead of straight lines.
function bezier(a: Pos, b: Pos): string {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cp1 = { x: a.x + dx * 0.35, y: a.y + dy * 0.05 };
  const cp2 = { x: b.x - dx * 0.35, y: b.y - dy * 0.05 };
  return `M ${a.x} ${a.y} C ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${b.x} ${b.y}`;
}

// ────────────────────────────────────────────────────────────────────

interface Props {
  isRunning: boolean;
  activeAgents: string[];
  onAgentsActive(agents: string[]): void;
  onResponse?(r: ChatResponse): void;
}

export function WorkflowCanvas({
  isRunning,
  activeAgents,
  onAgentsActive,
  onResponse,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 1280, h: 720 });
  const [initialized, setInitialized] = useState(false);
  const [positions, setPositions] = useState<Record<string, Pos>>(() =>
    initialPositions(1280, 720),
  );

  // Track container size so positions re-centre on first mount and after
  // a viewport resize (only when nodes haven't been dragged yet).
  useEffect(() => {
    function measure() {
      if (!containerRef.current) return;
      const r = containerRef.current.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useEffect(() => {
    if (!initialized && size.w > 100) {
      setPositions(initialPositions(size.w, size.h));
      setInitialized(true);
    }
  }, [size, initialized]);

  const activeSet = useMemo(() => new Set(activeAgents), [activeAgents]);

  function handleDrag(id: string, delta: { x: number; y: number }) {
    setPositions((prev) => ({
      ...prev,
      [id]: { x: prev[id].x + delta.x, y: prev[id].y + delta.y },
    }));
  }

  const managerCentre = nodeCentre("manager", positions.manager);

  return (
    <div
      ref={containerRef}
      className="canvas-bg ambient-glow relative h-full w-full overflow-hidden"
    >
      {/* ───── Connector SVG layer ───── */}
      <svg className="pointer-events-none absolute inset-0 z-0 h-full w-full">
        <defs>
          <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="amber-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Manager ↔ each sub-agent */}
        {SUBS.map((s) => {
          const subCentre = nodeCentre(s.slug, positions[s.slug]);
          const path = bezier(managerCentre, subCentre);
          const on = activeSet.has(s.name);
          const stroke = on
            ? "#22ff88"
            : isRunning
              ? "rgba(34, 255, 136, 0.25)"
              : "rgba(255, 255, 255, 0.10)";
          return (
            <g key={`edge-${s.slug}`}>
              <path
                d={path}
                fill="none"
                stroke={stroke}
                strokeWidth={on ? 2.4 : 1.6}
                filter={on ? "url(#neon-glow)" : undefined}
                className="transition-all duration-500 ease-in-out"
              />
              {on && (
                <circle r="4" fill="#22ff88" filter="url(#neon-glow)">
                  <animateMotion dur="2.2s" repeatCount="indefinite" path={path} />
                </circle>
              )}
            </g>
          );
        })}

        {/* Chat → Manager input edge */}
        {(() => {
          const chatCentre = nodeCentre("chat", positions.chat);
          const path = bezier(chatCentre, managerCentre);
          return (
            <g>
              <path
                d={path}
                fill="none"
                stroke={
                  isRunning
                    ? "#22ff88"
                    : "rgba(255, 255, 255, 0.10)"
                }
                strokeWidth={isRunning ? 2.4 : 1.6}
                strokeDasharray={isRunning ? undefined : "5 5"}
                filter={isRunning ? "url(#neon-glow)" : undefined}
                className="transition-all duration-500 ease-in-out"
              />
              {isRunning && (
                <circle r="4" fill="#22ff88" filter="url(#neon-glow)">
                  <animateMotion dur="1.8s" repeatCount="indefinite" path={path} />
                </circle>
              )}
            </g>
          );
        })()}
      </svg>

      {/* ───── Nodes ───── */}

      {/* Manager */}
      <motion.div
        drag
        dragMomentum={false}
        dragConstraints={containerRef}
        onDrag={(_e, info) => handleDrag("manager", info.delta)}
        initial={false}
        animate={{ x: positions.manager.x, y: positions.manager.y }}
        className="absolute left-0 top-0 z-20 cursor-grab active:cursor-grabbing"
      >
        <AgentNode
          slug="manager"
          name="AI Manager"
          role="Team Lead"
          active={activeSet.has("AI Manager") || isRunning}
          size={MANAGER_SIZE}
          asLink={false}
        />
      </motion.div>

      {/* Sub-agents */}
      {SUBS.map((s) => (
        <motion.div
          key={s.slug}
          drag
          dragMomentum={false}
          dragConstraints={containerRef}
          onDrag={(_e, info) => handleDrag(s.slug, info.delta)}
          initial={false}
          animate={{ x: positions[s.slug].x, y: positions[s.slug].y }}
          className="absolute left-0 top-0 z-10 cursor-grab active:cursor-grabbing"
        >
          <AgentNode
            slug={s.slug}
            name={s.name}
            role="Sub Agent"
            active={activeSet.has(s.name)}
            size={SUB_SIZE}
            asLink={false}
          />
        </motion.div>
      ))}

      {/* Chat panel — draggable. Clicks inside the input still focus/type
          because framer-motion only initiates drag on pointermove, not on a
          simple click-and-release. */}
      <motion.div
        drag
        dragMomentum={false}
        dragConstraints={containerRef}
        onDrag={(_e, info) => handleDrag("chat", info.delta)}
        initial={false}
        animate={{ x: positions.chat.x, y: positions.chat.y }}
        className="absolute left-0 top-0 z-30"
        style={{ width: CHAT_W }}
      >
        <ChatPanel
          onAgentsActive={onAgentsActive}
          onResponse={onResponse}
        />
      </motion.div>
    </div>
  );
}
