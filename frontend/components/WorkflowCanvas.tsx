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

// Default chat sizes — keep slim so they fit on small viewports.
const CHAT_W = 440;
const CHAT_H = 280;
// Expanded targets — capped at runtime against the canvas dimensions so
// the panel never escapes the visible area.
const CHAT_W_EXPANDED = 720;
const CHAT_H_EXPANDED = 520;

const CHAT_GAP = 24;
const CANVAS_MARGIN = 24;

// The Recommendation panel renders an avatar strip above its section.
// We treat that strip as part of the draggable box so the section beneath
// it lines up exactly with the chat panel's section (same top + bottom).
const REC_STACK_H = 32;

const SUBS: Array<{ slug: AgentSlug; name: string }> = [
  { slug: "architect",  name: "AI Architect" },
  { slug: "metodist",   name: "AI Metodist" },
  { slug: "searcher",   name: "AI Searcher" },
  { slug: "shadow",     name: "AI Shadow" },
  { slug: "regulyator", name: "AI Regulyator" },
  { slug: "secure",     name: "AI Secure" },
];

interface Pos { x: number; y: number }
interface Box { w: number; h: number }

function clampPos(p: Pos, box: Box, canvas: Box): Pos {
  return {
    x: Math.max(0, Math.min(canvas.w - box.w, p.x)),
    y: Math.max(0, Math.min(canvas.h - box.h, p.y)),
  };
}

function chatBox(expanded: boolean, canvas: Box, extraH = 0): Box {
  const baseW = expanded ? CHAT_W_EXPANDED : CHAT_W;
  const baseH = expanded ? CHAT_H_EXPANDED : CHAT_H;
  return {
    w: Math.min(baseW, canvas.w - 2 * CANVAS_MARGIN),
    h: Math.min(baseH + extraH, canvas.h - CANVAS_MARGIN),
  };
}

// Recompute the chat position when toggling expand so that the requested
// "anchor" corner stays put — Chat anchors bottom-right (grows up + left),
// Recommendation anchors bottom-left (grows up + right). Output is clamped
// to the canvas so nothing escapes the boundary.
function repositionForExpand(
  oldPos: Pos,
  oldBox: Box,
  newBox: Box,
  anchor: "bottom-right" | "bottom-left",
  canvas: Box,
): Pos {
  const anchorX = anchor === "bottom-right" ? oldPos.x + oldBox.w : oldPos.x;
  const anchorY = oldPos.y + oldBox.h;
  const x = anchor === "bottom-right" ? anchorX - newBox.w : anchorX;
  const y = anchorY - newBox.h;
  return clampPos({ x, y }, newBox, canvas);
}

function initialPositions(canvas: Box): Record<string, Pos> {
  const cx = canvas.w / 2;

  // Manager: top centre.
  const manager: Pos = { x: cx - MANAGER_SIZE / 2, y: 32 };

  // Sub-agent row: scale the gap down if the viewport is too narrow to fit
  // the desired spacing.
  const desiredGap = 160;
  const minGap = SUB_SIZE + 24;
  const usableWidth = canvas.w - 2 * CANVAS_MARGIN;
  const gap = Math.max(
    minGap,
    Math.min(desiredGap, usableWidth / (SUBS.length - 1)),
  );
  const subRowWidth = (SUBS.length - 1) * gap;
  const subStartX = cx - subRowWidth / 2;
  const subY = manager.y + MANAGER_SIZE + 80;     // leave room for manager label

  const subs: Record<string, Pos> = {};
  for (let i = 0; i < SUBS.length; i++) {
    subs[SUBS[i].slug] = {
      x: subStartX + i * gap - SUB_SIZE / 2,
      y: subY,
    };
  }

  // Chats: symmetric, both panel SECTIONS at the same y, with a fixed gap.
  // Bottom-aligned to (canvas.h - CANVAS_MARGIN), but pushed UP if sub-agent
  // labels would overlap. Rec sits REC_STACK_H higher so the avatar strip
  // above it stays inside the draggable box (and doesn't overflow above
  // when the user drags Rec to the top).
  const subBottom = subY + SUB_SIZE + 40;          // 40 ≈ label space
  const chatBottom = canvas.h - CANVAS_MARGIN;
  const sectionTopY = Math.max(subBottom + 16, chatBottom - CHAT_H);

  return {
    manager,
    ...subs,
    chat: clampPos(
      { x: cx - CHAT_GAP / 2 - CHAT_W, y: sectionTopY },
      { w: CHAT_W, h: CHAT_H },
      canvas,
    ),
    rec: clampPos(
      { x: cx + CHAT_GAP / 2, y: sectionTopY - REC_STACK_H },
      { w: CHAT_W, h: CHAT_H + REC_STACK_H },
      canvas,
    ),
  };
}

// Manager bottom port → sub-agent top port. Vertical-biased S-curve so
// the fan looks clean regardless of horizontal offset.
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
  const [canvas, setCanvas] = useState<Box | null>(null);
  const [positions, setPositions] = useState<Record<string, Pos> | null>(null);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [recExpanded, setRecExpanded] = useState(false);

  // Measure the container once on mount, then on resize. The very first
  // measurement also seeds the positions — we deliberately don't seed with
  // a placeholder size, because the first render's positions would then
  // be wrong for wider viewports (the whole layout would appear pushed to
  // the left of centre).
  useEffect(() => {
    function measure() {
      if (!containerRef.current) return;
      const r = containerRef.current.getBoundingClientRect();
      if (r.width < 100 || r.height < 100) return;
      const next = { w: r.width, h: r.height };
      setCanvas(next);
      setPositions((prev) => prev ?? initialPositions(next));
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const activeSet = useMemo(() => new Set(activeAgents), [activeAgents]);

  // Size of each draggable, in current state (used for clamping on drag).
  function boxOf(id: string): Box {
    if (id === "manager") return { w: MANAGER_SIZE, h: MANAGER_SIZE };
    if (id === "chat")    return chatBox(chatExpanded, canvas!);
    if (id === "rec")     return chatBox(recExpanded, canvas!, REC_STACK_H);
    return { w: SUB_SIZE, h: SUB_SIZE };
  }

  function move(id: string, p: Pos) {
    if (!canvas) return;
    setPositions((prev) =>
      prev ? { ...prev, [id]: clampPos(p, boxOf(id), canvas) } : prev,
    );
  }

  function toggleChatExpand() {
    if (!canvas || !positions) return;
    const oldBox = chatBox(chatExpanded, canvas);
    const newBox = chatBox(!chatExpanded, canvas);
    const next = repositionForExpand(
      positions.chat,
      oldBox,
      newBox,
      "bottom-right",
      canvas,
    );
    setPositions((prev) => (prev ? { ...prev, chat: next } : prev));
    setChatExpanded((v) => !v);
  }

  function toggleRecExpand() {
    if (!canvas || !positions) return;
    const oldBox = chatBox(recExpanded, canvas, REC_STACK_H);
    const newBox = chatBox(!recExpanded, canvas, REC_STACK_H);
    const next = repositionForExpand(
      positions.rec,
      oldBox,
      newBox,
      "bottom-left",
      canvas,
    );
    setPositions((prev) => (prev ? { ...prev, rec: next } : prev));
    setRecExpanded((v) => !v);
  }

  // First render: canvas is still being measured; show the empty surface
  // so the very next render can use the real dimensions.
  if (!canvas || !positions) {
    return (
      <div
        ref={containerRef}
        className="canvas-bg ambient-glow relative h-full w-full overflow-hidden"
      />
    );
  }

  const managerCentre: Pos = {
    x: positions.manager.x + MANAGER_SIZE / 2,
    y: positions.manager.y + MANAGER_SIZE / 2,
  };
  const managerBottom: Pos = {
    x: managerCentre.x,
    y: positions.manager.y + MANAGER_SIZE,
  };

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
          const sub = positions[s.slug];
          const toPort: Pos = { x: sub.x + SUB_SIZE / 2, y: sub.y };
          const path = fanBezier(managerBottom, toPort);
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

      {/* ───── Chat (left, grows up + left) ───── */}
      <DraggableLayer
        position={positions.chat}
        onChange={(p) => move("chat", p)}
        dragHandle='[data-drag-handle="true"]'
        zIndex={30}
        style={(() => {
          const b = chatBox(chatExpanded, canvas);
          return { width: b.w, height: b.h };
        })()}
      >
        <ChatPanel
          draft={draft}
          onDraftChange={onDraftChange}
          history={history}
          onSend={onSend}
          busy={busy}
          expanded={chatExpanded}
          onToggleExpand={toggleChatExpand}
        />
      </DraggableLayer>

      {/* ───── Recommendation (right, grows up + right) ───── */}
      <DraggableLayer
        position={positions.rec}
        onChange={(p) => move("rec", p)}
        dragHandle='[data-drag-handle="true"]'
        zIndex={30}
        style={(() => {
          const b = chatBox(recExpanded, canvas, REC_STACK_H);
          return { width: b.w, height: b.h };
        })()}
      >
        <RecommendationPanel
          response={response}
          previewing={previewing}
          busy={busy}
          expanded={recExpanded}
          onToggleExpand={toggleRecExpand}
        />
      </DraggableLayer>
    </div>
  );
}
