"use client";

import { useRef, type CSSProperties, type ReactNode } from "react";

interface Pos {
  x: number;
  y: number;
}

interface Props {
  position: Pos;
  onChange(pos: Pos): void;
  // CSS selector for the drag handle. If unset the whole element is a handle.
  // For chat panels we set this to `[data-drag-handle="true"]` so clicks
  // inside inputs don't trigger drag.
  dragHandle?: string;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  zIndex?: number;
}

// Pointer-based drag with absolute positioning. The framer-motion drag was
// fighting with `animate={{ x, y }}` and accumulating offsets on each frame,
// which made nodes drift away from the cursor. This version captures the
// pointer at down-time and computes the next position from the absolute
// pointer delta — no accumulation, no drift.
export function DraggableLayer({
  position,
  onChange,
  dragHandle,
  children,
  className,
  style,
  zIndex,
}: Props) {
  const startRef = useRef<{ pos: Pos; pointer: Pos } | null>(null);

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (dragHandle) {
      const target = e.target as HTMLElement;
      if (!target.closest(dragHandle)) return;
    }
    // Don't start a drag from form controls — typing in the chat input
    // should not relocate the panel.
    const tag = (e.target as HTMLElement).tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "BUTTON") return;

    e.currentTarget.setPointerCapture(e.pointerId);
    startRef.current = {
      pos: { ...position },
      pointer: { x: e.clientX, y: e.clientY },
    };
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!startRef.current) return;
    onChange({
      x: startRef.current.pos.x + (e.clientX - startRef.current.pointer.x),
      y: startRef.current.pos.y + (e.clientY - startRef.current.pointer.y),
    });
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    if (!startRef.current) return;
    startRef.current = null;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  }

  return (
    <div
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className={className}
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        touchAction: "none",
        zIndex,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
