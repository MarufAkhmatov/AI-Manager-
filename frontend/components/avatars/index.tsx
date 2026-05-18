/**
 * Hand-drawn SVG avatars, one per agent.
 * No external network calls — every face is inline SVG rendered by React.
 *
 *   AI Manager     male,   navy tie, calm leader
 *   AI Architect   male,   builder, bandana
 *   AI Secure      male,   guardian, beard + collar
 *   AI Searcher    female, glasses, ponytail, researcher
 *   AI Metodist    female, scholarly bun, soft smile
 *   AI Shadow      female, hood, quiet
 *   AI Regulyator  female, headset, active scout
 */

import type { SVGProps } from "react";

type AvatarProps = SVGProps<SVGSVGElement>;

const ACCENT = "#22D58F";
const SKIN_LIGHT = "#f4d3b0";
const SKIN_MED = "#e0b48a";
const HAIR_DARK = "#221b1a";
const HAIR_BROWN = "#5a3a25";
const HAIR_AUBURN = "#8a4a2a";

function Frame({
  bg,
  children,
  ...rest
}: { bg: string; children: React.ReactNode } & AvatarProps) {
  return (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" {...rest}>
      <defs>
        <radialGradient id="bgGrad" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stopColor={bg} stopOpacity="1" />
          <stop offset="100%" stopColor={bg} stopOpacity="0.55" />
        </radialGradient>
        <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={ACCENT} stopOpacity="0.55" />
          <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="49" fill="url(#bgGrad)" />
      <circle cx="50" cy="50" r="48" fill="none" stroke="url(#ringGrad)" strokeWidth="1.5" />
      {children}
    </svg>
  );
}

function Mouth({ smile = 0.6, x = 50, y = 62 }: { smile?: number; x?: number; y?: number }) {
  return (
    <path
      d={`M ${x - 6} ${y} Q ${x} ${y + smile * 6} ${x + 6} ${y}`}
      stroke="#2a1a14"
      strokeWidth="1.6"
      strokeLinecap="round"
      fill="none"
    />
  );
}

function Eyes({ y = 50, color = "#1a1a1a" }: { y?: number; color?: string }) {
  return (
    <>
      <ellipse cx="40" cy={y} rx="2" ry="2.6" fill={color} />
      <ellipse cx="60" cy={y} rx="2" ry="2.6" fill={color} />
    </>
  );
}

/* ───────────────────────── Manager (male, lead) ───────────────────────── */
export const ManagerAvatar = (props: AvatarProps) => (
  <Frame bg="#143f2c" {...props}>
    {/* short hair */}
    <path d="M28 42 Q50 22 72 42 L70 50 Q50 36 30 50 Z" fill={HAIR_DARK} />
    {/* face */}
    <circle cx="50" cy="54" r="20" fill={SKIN_LIGHT} />
    <Eyes y="52" />
    {/* brow */}
    <path d="M36 46 Q40 44 44 46" stroke="#1a1a1a" strokeWidth="1.4" fill="none" strokeLinecap="round" />
    <path d="M56 46 Q60 44 64 46" stroke="#1a1a1a" strokeWidth="1.4" fill="none" strokeLinecap="round" />
    <Mouth smile={0.55} y="64" />
    {/* tie */}
    <path d="M46 76 L50 82 L54 76 L52 96 L48 96 Z" fill={ACCENT} />
    {/* collar */}
    <path d="M30 76 L46 76 L50 82 L54 76 L70 76 L66 96 L34 96 Z" fill="#0e2418" />
  </Frame>
);

/* ───────────────────────── Architect (male, builder) ──────────────────── */
export const ArchitectAvatar = (props: AvatarProps) => (
  <Frame bg="#0e2a1f" {...props}>
    {/* bandana */}
    <path d="M26 42 Q50 28 74 42 L74 48 L26 48 Z" fill={ACCENT} />
    <path d="M70 46 L82 48 L78 52 L70 50 Z" fill={ACCENT} />
    {/* face */}
    <circle cx="50" cy="56" r="20" fill={SKIN_MED} />
    {/* hair bits */}
    <path d="M30 48 Q34 60 32 66" stroke={HAIR_BROWN} strokeWidth="2" fill="none" />
    <path d="M70 48 Q66 60 68 66" stroke={HAIR_BROWN} strokeWidth="2" fill="none" />
    <Eyes y="56" />
    <Mouth smile={0.45} y="68" />
    {/* body */}
    <path d="M28 80 Q50 72 72 80 L72 96 L28 96 Z" fill="#1a3a2a" />
  </Frame>
);

/* ───────────────────────── Secure (male, guardian) ────────────────────── */
export const SecureAvatar = (props: AvatarProps) => (
  <Frame bg="#0c2218" {...props}>
    {/* short hair */}
    <path d="M30 46 Q50 26 70 46 L70 52 Q50 40 30 52 Z" fill={HAIR_DARK} />
    {/* face */}
    <circle cx="50" cy="56" r="20" fill={SKIN_LIGHT} />
    <Eyes y="54" />
    <Mouth smile={0.25} y="64" />
    {/* beard */}
    <path d="M36 64 Q50 78 64 64 Q60 76 50 78 Q40 76 36 64 Z" fill={HAIR_DARK} opacity="0.85" />
    {/* shield collar */}
    <path d="M30 80 L50 88 L70 80 L66 96 L34 96 Z" fill="#163524" />
    <path d="M44 82 L50 86 L56 82 L54 90 L46 90 Z" fill={ACCENT} opacity="0.85" />
  </Frame>
);

/* ───────────────────────── Searcher (female, researcher) ──────────────── */
export const SearcherAvatar = (props: AvatarProps) => (
  <Frame bg="#0e2a1f" {...props}>
    {/* hair (ponytail) */}
    <path d="M26 44 Q50 22 74 44 L74 64 Q70 72 64 70 L36 70 Q30 72 26 64 Z" fill={HAIR_BROWN} />
    <path d="M72 56 Q82 68 78 84 L74 82 Q76 70 70 62 Z" fill={HAIR_BROWN} />
    {/* face */}
    <circle cx="50" cy="56" r="18" fill={SKIN_LIGHT} />
    {/* glasses */}
    <circle cx="42" cy="54" r="5" fill="none" stroke="#1a1a1a" strokeWidth="1.4" />
    <circle cx="58" cy="54" r="5" fill="none" stroke="#1a1a1a" strokeWidth="1.4" />
    <path d="M47 54 L53 54" stroke="#1a1a1a" strokeWidth="1.4" />
    {/* eyes inside lenses */}
    <circle cx="42" cy="54" r="1.5" fill="#1a1a1a" />
    <circle cx="58" cy="54" r="1.5" fill="#1a1a1a" />
    <Mouth smile={0.65} y="66" />
    {/* body */}
    <path d="M28 82 Q50 74 72 82 L72 96 L28 96 Z" fill="#163524" />
  </Frame>
);

/* ───────────────────────── Metodist (female, scholar) ─────────────────── */
export const MetodistAvatar = (props: AvatarProps) => (
  <Frame bg="#102a20" {...props}>
    {/* hair bun + sides */}
    <circle cx="50" cy="30" r="10" fill={HAIR_AUBURN} />
    <path d="M28 50 Q30 42 36 40 L36 60 Z" fill={HAIR_AUBURN} />
    <path d="M72 50 Q70 42 64 40 L64 60 Z" fill={HAIR_AUBURN} />
    {/* face */}
    <circle cx="50" cy="56" r="18" fill={SKIN_LIGHT} />
    <Eyes y="54" />
    {/* soft brow */}
    <path d="M37 48 Q42 47 46 49" stroke="#3a2a20" strokeWidth="1.2" fill="none" strokeLinecap="round" />
    <path d="M54 49 Q58 47 63 48" stroke="#3a2a20" strokeWidth="1.2" fill="none" strokeLinecap="round" />
    <Mouth smile={0.6} y="66" />
    {/* high collar */}
    <path d="M30 82 Q50 76 70 82 L70 96 L30 96 Z" fill="#1d3a2c" />
    <path d="M44 80 L50 86 L56 80 L52 92 L48 92 Z" fill="#0c1f17" />
  </Frame>
);

/* ───────────────────────── Shadow (female, hooded) ────────────────────── */
export const ShadowAvatar = (props: AvatarProps) => (
  <Frame bg="#06140d" {...props}>
    {/* hood */}
    <path
      d="M16 56 Q18 24 50 22 Q82 24 84 56 L80 80 Q50 70 20 80 Z"
      fill="#0a1f15"
    />
    <path
      d="M22 58 Q24 32 50 30 Q76 32 78 58"
      fill="none"
      stroke={ACCENT}
      strokeOpacity="0.35"
      strokeWidth="1.2"
    />
    {/* face partial */}
    <ellipse cx="50" cy="58" rx="14" ry="16" fill={SKIN_MED} />
    <Eyes y="58" color="#0a1a12" />
    <Mouth smile={0.15} y="68" />
    {/* hair wisp */}
    <path d="M36 52 Q40 58 42 64" stroke={HAIR_DARK} strokeWidth="1.4" fill="none" />
    <path d="M64 52 Q60 58 58 64" stroke={HAIR_DARK} strokeWidth="1.4" fill="none" />
  </Frame>
);

/* ─────────────────────── Regulyator (female, scout) ───────────────────── */
export const RegulyatorAvatar = (props: AvatarProps) => (
  <Frame bg="#0e2418" {...props}>
    {/* long hair sides */}
    <path d="M24 46 Q26 28 50 22 Q74 28 76 46 L72 84 L28 84 Z" fill={HAIR_AUBURN} />
    {/* face */}
    <circle cx="50" cy="56" r="18" fill={SKIN_LIGHT} />
    <Eyes y="55" />
    <Mouth smile={0.7} y="66" />
    {/* headset */}
    <path
      d="M30 50 Q32 36 50 34 Q68 36 70 50"
      stroke="#1a1a1a"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
    />
    <rect x="26" y="48" width="6" height="10" rx="2" fill={ACCENT} />
    <rect x="68" y="48" width="6" height="10" rx="2" fill={ACCENT} />
    <path d="M32 58 Q38 64 42 60" stroke="#1a1a1a" strokeWidth="1.4" fill="none" />
    {/* body */}
    <path d="M28 82 Q50 74 72 82 L72 96 L28 96 Z" fill="#163524" />
  </Frame>
);

export const AVATARS = {
  manager: ManagerAvatar,
  architect: ArchitectAvatar,
  secure: SecureAvatar,
  searcher: SearcherAvatar,
  metodist: MetodistAvatar,
  shadow: ShadowAvatar,
  regulyator: RegulyatorAvatar,
} as const;

export type AgentSlug = keyof typeof AVATARS;
