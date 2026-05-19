"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AgentNode } from "@/components/AgentNode";
import { ChatPanel, type ChatResponse } from "@/components/ChatPanel";
import { RecommendationPanel } from "@/components/RecommendationPanel";
import { DraggableLayer } from "@/components/DraggableLayer";
import type { AgentSlug } from "@/components/avatars";

// ────────────────────────────────────────────────────────────────────
// Sizing
// ────────────────────────────────────────────────────────────────────
const MANAGER_SIZE = 132;
const SUB_SIZE = 88;
const CHAT_W = 460;
const CHAT_H = 340;
const CHAT_W_EXPANDED = 720;
const CHAT_H_EXPANDED = 560;

// Order across the horizontal row, left → right.
const SUBS: Array<{ slug: AgentSlug; name: string }> = [
  { slug: "architect",  name: "AI Architect" },
  { slug: "metodist",   name: "AI Metodist" },
  { slug: "searcher",   name: "AI Searcher" },
  { slug: "shadow",     name: "AI Shadow" },
  { slug: "regulyator", name: "AI Regulyator" },
  { slug: "secure",     name: "AI Secure" },
];

interface Pos { x: number; y: number }

function initialPositions(w: number, h: number): Record<string, Pos> {
  const cx = w / 2;

  // Manager: top centre, ~64 px below the canvas top so the name label fits.
  const manager: Pos = { x: cx - MANAGER_SIZE / 2, y: 64 };

  // Sub-agents: horizontal row, evenly spaced, centred.
  // Reserve ~120 px between centres so the names don't collide.
  const subGap = 132;
  const subRowWidth = (SUBS.length - 1) * subGap;
  const subStartX = cx - subRowWidth / 2;
  const subY = 260;
  const subs: Record<string, Pos> = {};
  for (let i = 0; i < SUBS.length; i++) {
    subs[SUBS[i].slug] = {
      x: subStartX + i * subGap - SUB_SIZE / 2,
      y: subY,
    };
  }

  // Chat + Recommendation: side-by-side, anchored to bottom of canvas.
  const chatY = Math.max(h - CHAT_H - 32, subY + 180);
  const totalChatWidth = CHAT_W * 2 + 24;
  const chatStartX = cx - totalChatWidth / 2;

  return {
    manager,
    ...subs,
    chat: { x: chatStartX, y: chatY },
    rec:  { x: chatStartX + CHAT_W + 24, y: chatY },
  };
}

// Centre of a node, used as the connector endpoint.
function nodeCentre(id: string, p: Pos): Pos {
  if (id === "manager") {
    return { x: p.x + MANAGER_SIZE / 2, y: p.y + MANAGER_SIZE / 2 };
  }
  return { x: p.x + SUB_SIZE / 2, y: p.y + SUB_SIZE / 2 };
}

// Manager bottom port → sub-agent top port. Vertical-biased S-curve so the
// edges fan cleanly to each sub-agent regardless of horizontal offset.
function fanBezier(from: Pos, to: Pos): string {
  const dy = Math.max(to.y - from.y, 40);
  const cp1 = { x: from.x, y: from.y + dy * 0.55 };
  const cp2 = { x: to.x,   y: to.y - dy * 0.55 };
  return `M ${from.x} ${from.y} C ${cp1.x} ${cp1.y}, ${cp2.x} ${cp2.y}, ${to.x} ${to.y}`;
}

// ────────────────────────────────────────────────────────────────────

interface Props {
  isRunning: boolean;
  activeAgents: string[];

  // Chat state lifted into the dashboard so RecommendationPanel can react
  // to typing live.
  draft: string;
  onDraftChange(v: string): void;
  history: string[];
  onSend(): void;
  busy: boolean;
  previewing: boolean;
  response: ChatResponse | null;
}

export function WorkflowCanvas({
  isRunning,
  activeAgents,
  draft,
  onDraftChange,
  history,
  onSend,
  busy,
  previewing,
  response,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({ w: 1400, h: 820 });
  const [initialized, setInitialized] = useState(false);
  const [positions, setPositions] = useState<Record<string, Pos>>(() =>
    initialPositions(1400, 820),
  );
  const [chatExpanded, setChatExpanded] = useState(false);
  const [recExpanded, setRecExpanded] = useState(false);

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

  function move(id: string, p: Pos) {
    setPositions((prev) => ({ ...prev, [id]: p }));
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
        </defs>

        {SUBS.map((s) => {
          const subCentre = nodeCentre(s.slug, positions[s.slug]);
          // Manager's bottom edge → sub-agent's top edge.
          const fromPort = {
            x: managerCentre.x,
            y: positions.manager.y + MANAGER_SIZE,
          };
          const toPort = {
            x: subCentre.x,
            y: positions[s.slug].y,
          };
          const path = fanBezier(fromPort, toPort);
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
      </svg>

      {/* ───── Manager ───── */}
      <DraggableLayer
        position={positions.manager}
        onChange={(p) => move("manager", p)}
        zIndex={20}
        className="cursor-grab active:cursor-grabbing"
      >
        <AgentNode
          slug="manager"
          name="AI Manager"
          role="Team Lead"
          active={activeSet.has("AI Manager") || isRunning}
          size={MANAGER_SIZE}
          asLink={false}
        />
      </DraggableLayer>

      {/* ───── Sub-agents ───── */}
      {SUBS.map((s) => (
        <DraggableLayer
          key={s.slug}
          position={positions[s.slug]}
          onChange={(p) => move(s.slug, p)}
          zIndex={10}
          className="cursor-grab active:cursor-grabbing"
        >
          <AgentNode
            slug={s.slug}
            name={s.name}
            role="Sub Agent"
            active={activeSet.has(s.name)}
            size={SUB_SIZE}
            asLink={false}
          />
        </DraggableLayer>
      ))}

      {/* ───── Chat (left) ───── */}
      <DraggableLayer
        position={positions.chat}
        onChange={(p) => move("chat", p)}
        dragHandle='[data-drag-handle="true"]'
        zIndex={30}
        style={{
          width: chatExpanded ? CHAT_W_EXPANDED : CHAT_W,
          height: chatExpanded ? CHAT_H_EXPANDED : CHAT_H,
        }}
      >
        <ChatPanel
          draft={draft}
          onDraftChange={onDraftChange}
          history={history}
          onSend={onSend}
          busy={busy}
          expanded={chatExpanded}
          onToggleExpand={() => setChatExpanded((v) => !v)}
        />
      </DraggableLayer>

      {/* ───── Recommendation (right) ───── */}
      <DraggableLayer
        position={positions.rec}
        onChange={(p) => move("rec", p)}
        dragHandle='[data-drag-handle="true"]'
        zIndex={30}
        style={{
          width: recExpanded ? CHAT_W_EXPANDED : CHAT_W,
          height: recExpanded ? CHAT_H_EXPANDED : CHAT_H,
        }}
      >
        <RecommendationPanel
          response={response}
          previewing={previewing}
          busy={busy}
          expanded={recExpanded}
          onToggleExpand={() => setRecExpanded((v) => !v)}
        />
      </DraggableLayer>
    </div>
  );
}
