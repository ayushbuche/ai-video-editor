// Long-form 16:9 edit in a measured style (styles/<name>/style.json "design"). Every graphic kind here was
// measured in the references (styles/axis-story/teardown.md): the panel + speaker card with a marker diagram
// that draws on as it is said, the full-screen quote and chapter cards, title + bullets, red buttons, pills.
// No captions: the references have none. Shapes: skills/style-edit/references/longform.md.
// All positions are design px on a 1920 x 1080 frame, scaled to the render size.
import React from "react";
import { AbsoluteFill, Audio, CalculateMetadataFunction, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame,
  useVideoConfig } from "remotion";
import { loadFont as loadSerif } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadSans } from "@remotion/google-fonts/Inter";
import { loadFont as loadMarker } from "@remotion/google-fonts/PatrickHand";
import { loadFont as loadScript } from "@remotion/google-fonts/Caveat";
import { loadFont as loadSpoken } from "@remotion/google-fonts/Gloock";

const SERIF = loadSerif("normal", { weights: ["500", "600"], subsets: ["latin"] }).fontFamily;
const SANS = loadSans("normal", { weights: ["400", "500", "700", "800"], subsets: ["latin"] }).fontFamily;
const MARKER = loadMarker("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
// the references' spoken-words overlay (m_D2yOUapNQ 2:18 "$20k to $400k"): a heavy high-contrast display serif
const SPOKEN = loadSpoken("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
const SCRIPT = loadScript("normal", { weights: ["500", "600"], subsets: ["latin"] }).fontFamily;

export type Palette = { cream: string; ink: string; blue: string; red: string; panel: string; white: string; pip_glow: string;
  green: string; grey: string };
export const PALETTE: Palette = { cream: "#F5F3E4", ink: "#111111", blue: "#2655A3", red: "#C71338", panel: "#DDE1E0",
  white: "#FFFFFF", pip_glow: "#C9DBF8", green: "#2F8A5B", grey: "#3A3A3A" };

// ---------- plan shape ----------
type Timed = { at: number; dur?: number };
export type El =
  | ({ t: "path"; d: string; color?: string; w?: number; fill?: string } & Timed)
  | ({ t: "text"; text: string; x: number; y: number; size?: number; color?: string; font?: "marker" | "script" | "sans";
      anchor?: "start" | "middle" | "end"; rot?: number; underline?: string } & Timed);
type Bullet = { text: string; at: number };
type Item = { text: string; at: number };
export type Graphic = { start: number; end: number } & (
  | { kind: "panel"; number?: number; title?: string; body: { type: "diagram"; els: El[] } | { type: "image"; src: string;
      fit?: "cover" | "contain" | "frame"; focus?: [number, number] } | { type: "bullets"; heading: string; bullets: Bullet[] } }
  | { kind: "title"; heading: string; bullets: Bullet[] } // white page, serif heading, blue bullets, speaker card
  | { kind: "quote"; text: string } // **bold** marks the key phrase
  | { kind: "chapter"; number: number; title: string }
  | { kind: "pills"; items: Item[] } // full-screen white, red buttons pop in as each is said
  | { kind: "buttons"; items: Item[] } // red pills over the speaker, under the chin, popping in as each is said
  | { kind: "label"; text: string } // small white pill, bottom-left
  | { kind: "lower"; words: Item[] } // big white serif words over the speaker, each fading in as it is said
  | { kind: "script"; heading: string; lines: Item[][] } // a script he says: white page, serif heading, the script in blue
                                                          // quotes, each sentence sweeping on as he starts it (reference "How to Pitch")
);
type Zoom = { start: number; end: number; scale: number };
type Face = { cx: number; top: number; h: number }; // the head box (hair to chin) in the source, fractions of the frame (face.py)
type Track = { src: string; start: number; volume?: number };
export type LongPlan = { video: string; width: number; height: number; fps: number; durationInFrames: number; face: Face;
  zooms: Zoom[]; graphics: Graphic[]; music?: Track; sfx?: Track[]; palette?: Partial<Palette>;
  voice?: string }; // the cut's voice as a stereo file (longplan.py); else the cut's own audio

export const longMeta: CalculateMetadataFunction<LongPlan> = ({ props }) => ({
  width: props.width, height: props.height, fps: props.fps, durationInFrames: props.durationInFrames,
});

// ---------- timing (measured: references at 5-10 fps) ----------
const DRAW_S = 0.6; // a stroke draws on (the panel's first curve: 0.6 s)
const WRITE_S = 0.9; // a marker label writes on letter by letter (SAME: 1.0 s)
const INK_S = 1.0; // a chapter title inks in
const POP_S = 0.55; // a red pill eases in (was a 0.25 s pop; smooth, Ayush 2026-10-10)
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
// smooth motion (Ayush, 2026-10-10): long, soft ease-outs, no snap and no overshoot
const easeSoft = (x: number) => 1 - Math.pow(1 - clamp01(x), 5); // quint out: quick start, a long gentle settle
const EXIT_S = 0.5;       // overlays on the speaker leave over this, never cut off
const easeInOut = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };

// ---------- layout (design px, measured on the references' 1920 x 1080 frames) ----------
const PANEL = { x: 76, y: 55, w: 1364, h: 970, r: 48 };
const CARD = { x: 1338, y: 128, w: 520, h: 822, r: 44 };

/** The speaker: the cut's footage, zoomed (a hard punch) or cropped into a box around the head. */
const Footage: React.FC<{ video: string; face: Face; box?: { w: number; h: number }; zoom: number; S: number }> = ({ video, face, box, zoom, S }) => {
  const { width, height } = useVideoConfig();
  if (!box) {
    // full frame: scale about the head, never past the frame's edge
    const ox = face.cx * 100, oy = face.top * 100; // the top of the head holds its place: the hair never leaves the frame
    return (
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${ox}% ${oy}%` }}>
        <OffthreadVideo muted src={staticFile(video)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
    );
  }
  // card: the head box 42% of the card high, its top 9% down (measured on the references' speaker card),
  // the frame always covering the card
  const bw = box.w * S, bh = box.h * S;
  const k = Math.max(bh / height, bw / width, (0.42 * bh) / (face.h * height));
  const vw = width * k, vh = height * k;
  const left = Math.min(0, Math.max(bw - vw, bw / 2 - face.cx * vw));
  const top = Math.min(0, Math.max(bh - vh, bh * 0.09 - face.top * vh));
  return (
    <div style={{ position: "absolute", left, top, width: vw, height: vh }}>
      <OffthreadVideo muted src={staticFile(video)} style={{ width: "100%", height: "100%" }} />
    </div>
  );
};

const SpeakerCard: React.FC<{ video: string; face: Face; S: number; pal: Palette }> = ({ video, face, S, pal }) => (
  <div style={{ position: "absolute", left: CARD.x * S, top: CARD.y * S, width: CARD.w * S, height: CARD.h * S, borderRadius: CARD.r * S,
    overflow: "hidden", border: `${4 * S}px solid rgba(255,255,255,0.85)`,
    boxShadow: `0 0 ${46 * S}px ${10 * S}px ${pal.pip_glow}, 0 0 ${8 * S}px ${2 * S}px ${pal.pip_glow}` }}>
    <Footage video={video} face={face} box={{ w: CARD.w, h: CARD.h }} zoom={1} S={S} />
  </div>
);

/** A whiteboard surface: the panel grey with the soft uneven light of a real board. */
const Board: React.FC<{ S: number; pal: Palette; children?: React.ReactNode; white?: boolean }> = ({ S, pal, children, white }) => (
  <div style={{ position: "absolute", left: PANEL.x * S, top: PANEL.y * S, width: PANEL.w * S, height: PANEL.h * S, borderRadius: PANEL.r * S,
    overflow: "hidden", background: white ? pal.white
      : `radial-gradient(120% 90% at 35% 30%, #E9EBEA 0%, ${pal.panel} 55%, #D3D8D7 100%)` }}>
    {children}
  </div>
);

/** One element of a diagram, drawn on from `at` (seconds into the graphic). Panel-local design px. */
const Draw: React.FC<{ el: El; lt: number; pal: Palette }> = ({ el, lt, pal }) => {
  if (el.t === "path") {
    const p = easeInOut((lt - el.at) / (el.dur ?? DRAW_S));
    if (p <= 0) return null;
    return <path d={el.d} pathLength={1} fill={el.fill && p >= 1 ? el.fill : "none"} stroke={el.color ?? pal.blue}
      strokeWidth={el.w ?? 9} strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" strokeDashoffset={1 - p} />;
  }
  const dur = el.dur ?? WRITE_S;
  const p = clamp01((lt - el.at) / dur);
  if (p <= 0) return null;
  const chars = [...el.text];
  const per = 1 / Math.max(1, chars.length);
  const size = el.size ?? 72;
  const fam = el.font === "script" ? SCRIPT : el.font === "sans" ? SANS : MARKER;
  const anchor = el.anchor ?? "start";
  const under = el.underline;
  const width = chars.length * size * (el.font === "script" ? 0.42 : 0.5);
  const ux = anchor === "middle" ? el.x - width / 2 : anchor === "end" ? el.x - width : el.x;
  return (
    <g transform={el.rot ? `rotate(${el.rot} ${el.x} ${el.y})` : undefined}>
      <text x={el.x} y={el.y} fontFamily={fam} fontSize={size} fill={el.color ?? pal.grey} textAnchor={anchor}
        fontWeight={el.font === "script" ? 600 : 400}>
        {/* each letter fades in over 1.6 letters' time; the run is stretched so the last one finishes too */}
        {chars.map((c, i) => <tspan key={i} opacity={clamp01((p * (1 + 0.6 * per) - i * per) / (per * 1.6))}>{c}</tspan>)}
      </text>
      {under ? <path d={`M ${ux - 6} ${el.y + size * 0.3} Q ${ux + width / 2} ${el.y + size * 0.36} ${ux + width + 10} ${el.y + size * 0.26}`}
        pathLength={1} fill="none" stroke={under} strokeWidth={6} strokeLinecap="round" strokeDasharray="1 1"
        strokeDashoffset={1 - easeOut(p * 1.1)} /> : null}
    </g>
  );
};

/** The numbered marker header every panel in a part carries: a red circled number, a blue script title. */
const Header: React.FC<{ n?: number; title?: string; lt: number; pal: Palette }> = ({ n, title, lt, pal }) => (
  <>
    {n ? <>
      <Draw lt={lt} pal={pal} el={{ t: "path", at: 0, dur: 0.45, w: 4.5, color: pal.red,
        d: "M 118 84 C 82 84 52 110 54 146 C 56 182 92 198 126 192 C 162 186 182 158 176 126 C 170 96 144 78 108 88" }} />
      <Draw lt={lt} pal={pal} el={{ t: "text", at: 0.1, dur: 0.3, text: String(n), x: 116, y: 162, size: 60, color: pal.red,
        anchor: "middle", font: "marker" }} />
    </> : null}
    {title ? <Draw lt={lt} pal={pal} el={{ t: "text", at: 0.05, dur: Math.min(0.9, 0.12 * title.length), text: title, x: n ? 206 : 66,
      y: 178, size: 128, color: pal.blue, font: "script" }} /> : null}
  </>
);

const Bullets: React.FC<{ heading: string; bullets: Bullet[]; lt: number; S: number; pal: Palette; x: number; y: number; size: number }> = (
  { heading, bullets, lt, S, pal, x, y, size }) => (
  <div style={{ position: "absolute", left: x * S, top: y * S, width: 1180 * S }}>
    <div style={{ fontFamily: SERIF, fontWeight: 500, fontSize: size * S, color: pal.ink, letterSpacing: -0.5 * S, lineHeight: 1.1 }}>
      {heading}
    </div>
    {bullets.map((b, i) => {
      const p = easeOut((lt - b.at) / 0.35);
      return p <= 0 ? null : (
        <div key={i} style={{ fontFamily: SANS, fontWeight: 400, fontSize: size * 0.42 * S, color: pal.blue, marginTop: 14 * S,
          opacity: p, transform: `translateY(${(1 - p) * 12 * S}px)` }}>- {b.text}</div>
      );
    })}
  </div>
);

const Pill: React.FC<{ text: string; S: number; pal: Palette; p: number; size?: number; serif?: boolean }> = ({ text, S, pal, p, size = 44, serif = true }) => (
  <div style={{ display: "inline-block", background: pal.red, color: pal.white, fontFamily: serif ? SERIF : SANS, fontWeight: 500,
    fontSize: size * S, padding: `${size * 0.28 * S}px ${size * 0.9 * S}px`, borderRadius: size * 0.42 * S, lineHeight: 1.15,
    transform: `translateY(${(1 - easeSoft(p)) * size * 0.45 * S}px) scale(${0.94 + 0.06 * easeSoft(p)})`,
    opacity: easeSoft(p * 1.4), filter: p < 1 ? `blur(${(1 - easeSoft(p)) * 5 * S}px)` : undefined, whiteSpace: "nowrap" }}>{text}</div>
);

const Quote: React.FC<{ text: string; lt: number; S: number; pal: Palette }> = ({ text, lt, S, pal }) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/).filter(Boolean);
  const p = easeOut(lt / 0.4);
  // the references' 92 px, smaller only when the quote would run past four lines across 1560 px
  const fs = Math.min(92, 12500 / Math.max(1, text.replace(/\*/g, "").length));
  return (
    <AbsoluteFill style={{ background: pal.cream }}>
      <Paper S={S} />
      <svg width={1920 * S} height={1080 * S} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
        {/* the faint giant close-quote behind the text, bottom right (measured: x 960-1920, y 400-1080) */}
        <g fill="rgba(140,165,140,0.12)"><QuoteMark x={955} y={400} s={6.6} flip /><QuoteMark x={1470} y={400} s={6.6} flip /></g>
        <g fill={pal.blue} opacity={p}><QuoteMark x={177} y={172} s={2.08} /><QuoteMark x={300} y={172} s={2.08} /></g>
      </svg>
      <div style={{ position: "absolute", left: 176 * S, top: 430 * S, width: 1560 * S, fontFamily: SANS, fontWeight: 400, fontSize: fs * S,
        lineHeight: 1.08, letterSpacing: -1 * S, color: pal.blue, opacity: p, transform: `translateY(${(1 - p) * 14 * S}px)` }}>
        {parts.map((s, i) => s.startsWith("**") ? <b key={i} style={{ fontWeight: 800 }}>{s.slice(2, -2)}</b> : <span key={i}>{s}</span>)}
      </div>
    </AbsoluteFill>
  );
};

/** One heavy square-shouldered quote mark, 52 x 100 units at s = 1 (flip: the closing mark, tail at the top). */
const QuoteMark: React.FC<{ x: number; y: number; s: number; flip?: boolean }> = ({ x, y, s, flip }) => (
  <path transform={`translate(${x} ${y}) scale(${s})${flip ? " rotate(180 26 50)" : ""}`}
    d="M 52 0 L 52 24 C 40 24 30 30 30 44 L 52 44 L 52 100 L 0 100 L 0 48 C 0 14 18 0 52 0 Z" />
);

/** The cream paper's faint speckle (the chapter and quote cards). Seeded, so every frame is the same. */
const Paper: React.FC<{ S: number }> = ({ S }) => {
  const dots = React.useMemo(() => {
    let s = 7;
    const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    return Array.from({ length: 160 }, () => [r() * 1920, r() * 1080, 0.8 + r() * 1.6, 0.05 + r() * 0.12]);
  }, []);
  return (
    <svg width={1920 * S} height={1080 * S} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0 }}>
      {dots.map(([x, y, rr, o], i) => <circle key={i} cx={x} cy={y} r={rr} fill={`rgba(60,50,30,${o})`} />)}
    </svg>
  );
};

const Chapter: React.FC<{ n: number; title: string; lt: number; S: number; pal: Palette }> = ({ n, title, lt, S, pal }) => {
  const chars = [...title];
  const p = clamp01((lt - 0.15) / INK_S);
  const fs = Math.min(230, 1500 / Math.max(6, title.length) * 1.55);
  return (
    <AbsoluteFill style={{ background: pal.cream }}>
      <Paper S={S} />
      <div style={{ position: "absolute", left: (960 - 118) * S, top: 196 * S, width: 236 * S, height: 236 * S, borderRadius: 64 * S,
        background: pal.white, boxShadow: `0 ${10 * S}px ${40 * S}px rgba(120,110,80,0.18)`, display: "flex", alignItems: "center",
        justifyContent: "center", fontFamily: SANS, fontWeight: 700, fontSize: 150 * S, color: pal.red }}>{n}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 500 * S, textAlign: "center", fontFamily: SERIF, fontWeight: 500,
        fontSize: fs * S, color: pal.ink, letterSpacing: -2 * S, lineHeight: 1, fontVariantNumeric: "lining-nums" }}>
        {chars.map((c, i) => {
          // each letter inks in: a thin outline first, then the fill (measured: stroke, then solid, ~1 s for the word)
          const q = clamp01((p - (i / chars.length) * 0.55) / 0.45);
          return <span key={i} style={{ color: q < 0.5 ? "transparent" : pal.ink, opacity: q > 0 ? 1 : 0,
            WebkitTextStroke: q < 1 ? `${2 * S}px ${pal.ink}` : undefined, transition: "none" }}>{c}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};

const SPOKEN_EM = 0.6;   // Gloock's average character width, em (measured: "$100M SaaS company" at 175 px ran 1.2x the 0.52 guess)
const CHIN_IN_HEAD = 0.9; // face.py's head box runs 15% of the face past the chin: the chin is 90% of the way down it

/** The bottom of the shot darkens a little under the spoken words (measured on the reference: before the first word). */
const BottomShade: React.FC<{ S: number; p: number }> = ({ p }) => (
  <AbsoluteFill style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0) 45%, rgba(0,0,0,0.42) 100%)", opacity: p }} />
);

/** Spoken words, the references' overlay: white display serif with a soft white glow, centred low in the frame, each
 *  word fading in out of a slight blur as it is said (0.3 s). The size fits the width and keeps the type under the chin. */
const Spoken: React.FC<{ words: Item[]; lt: number; S: number; face: Face; max: number; lines?: number }> = ({ words, lt, S, face, max, lines = 1 }) => {
  const text = words.map((w) => w.text).join(" ");
  const chinPx = (face.top + face.h * CHIN_IN_HEAD) * 1080;
  const base = 990; // the last line's baseline, design px (reference: about 960 for a 230 px line)
  const byWidth = (1640 * lines) / Math.max(1, text.length * SPOKEN_EM); // Gloock: about 0.6 em a character
  const byChin = (base - chinPx - 24) / (0.72 + 1.05 * (lines - 1));
  const fs = Math.max(56, Math.min(max, byWidth, byChin));
  return (
    <div style={{ position: "absolute", left: 140 * S, right: 140 * S, bottom: (1080 - base - fs * 0.24) * S, textAlign: "center",
      fontFamily: SPOKEN, fontSize: fs * S, lineHeight: 1.05, color: "#FFFFFF", fontVariantNumeric: "lining-nums",
      whiteSpace: lines === 1 ? "nowrap" : undefined, // one line never wraps up over the face
      textShadow: `0 0 ${14 * S}px rgba(255,255,255,0.55), 0 0 ${38 * S}px rgba(255,255,255,0.28), 0 ${3 * S}px ${18 * S}px rgba(0,0,0,0.35)` }}>
      {words.map((w, i) => {
        const q = easeSoft((lt - w.at) / 0.45);
        // words not said yet keep their place (the line never re-centres as it grows), unseen
        return (
          <span key={i} style={{ opacity: q, filter: q > 0 && q < 1 ? `blur(${(1 - q) * 6 * S}px)` : undefined }}>{w.text}{i < words.length - 1 ? " " : ""}</span>
        );
      })}
    </div>
  );
};

const SWEEP_S = 0.6; // a sentence sweeps on left to right (reference: the second script in "How to Pitch", about 0.6 s)

/** A script he says, as the references show one ("How to Pitch", m_D2yOUapNQ 6:43): a large black serif heading, the
 *  script under it in blue in curly quotes with the opening mark hanging, left of the speaker card. Each sentence
 *  sweeps on as he starts it and stays, so the whole script is up by the end (Ayush, 2026-10-10). The type is the
 *  reference's 62 px, smaller only so a long script still fits above the foot of the page. */
const Script: React.FC<{ heading: string; lines: Item[][]; lt: number; S: number; pal: Palette }> = ({ heading, lines, lt, S, pal }) => {
  const all = lines.flat();
  // the largest size (at most the reference's 62 px) at which the whole script, wrapped word by word at Inter's
  // ~0.52 em a character across 1150 px, ends above the page's foot
  const fits = (f: number, top: number) => {
    let n = 1, x = 0;
    for (const w of all) {
      const ww = (w.text.length + 1) * 0.52 * f;
      if (x + ww > 1150 && x > 0) { n += 1; x = 0; }
      x += ww;
    }
    return top + 124 + 46 + n * 1.3 * f <= 1000;
  };
  let fs = 62, top = 260;
  while (fs > 34 && !fits(fs, top)) { if (top > 130) top -= 10; else fs -= 1; }
  return (
    <div style={{ position: "absolute", left: 100 * S, top: top * S, width: 1190 * S }}>
      <div style={{ fontFamily: SERIF, fontWeight: 500, fontSize: 124 * S, lineHeight: 1, color: pal.ink, letterSpacing: -1.5 * S,
        marginBottom: 46 * S }}>{heading}</div>
      <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: fs * S, lineHeight: 1.3, color: pal.blue, letterSpacing: -0.6 * S,
        textIndent: -0.38 * fs * S, paddingLeft: 0.38 * fs * S }}>
        {all.map((w, i) => {
          const line = lines.find((l) => l.includes(w))!;
          const start = line[0].at, k = line.indexOf(w);
          // the sweep: a sentence's words come up left to right across SWEEP_S from its first word
          const q = easeOut((lt - start - (k / Math.max(1, line.length)) * SWEEP_S * 0.7) / (SWEEP_S * 0.45));
          const open = i === 0 ? "\u201C" : "", close = i === all.length - 1 ? "\u201D" : "";
          return <span key={i} style={{ opacity: q }}>{open}{w.text}{close}{i < all.length - 1 ? " " : ""}</span>;
        })}
      </div>
    </div>
  );
};

/** The graphic up at t, if any (graphics never overlap; plan check). */
const at = (gs: Graphic[], t: number) => gs.find((g) => t >= g.start && t < g.end);

export const LongEdit: React.FC<LongPlan> = ({ video, face, zooms, graphics, music, sfx, palette, voice }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const t = frame / fps;
  const S = width / 1920;
  const pal = { ...PALETTE, ...(palette ?? {}) };
  const g = at(graphics, t);
  const lt = g ? t - g.start : 0;
  const zoom = zooms.find((z) => t >= z.start && t < z.end)?.scale ?? 1;
  const audio = (
    <>
      {/* the voice: its own track for the whole cut, so no graphic (a full-screen card shows no footage) silences it */}
      <Audio src={staticFile(voice ?? video)} />
      {/* the bed (longplan.py): already levelled, faded and padded to the cut's length */}
      {music ? <Sequence from={Math.round(music.start * fps)} layout="none"><Audio src={staticFile(music.src)} volume={music.volume ?? 1} /></Sequence> : null}
      {(sfx ?? []).map((s, i) => (
        <Sequence key={`s${i}`} from={Math.round(s.start * fps)} layout="none"><Audio src={staticFile(s.src)} volume={s.volume ?? 1} /></Sequence>
      ))}
    </>
  );
  const speaker = <Footage video={video} face={face} zoom={zoom} S={S} />;
  let view: React.ReactNode = speaker;
  let overlay: React.ReactNode = null; // buttons, label, lower: drawn over the speaker (below)
  if (g?.kind === "panel") {
    const b = g.body;
    view = (
      <AbsoluteFill style={{ background: pal.white }}>
        <Board S={S} pal={pal} white={b.type === "bullets"}>
          {b.type === "image" && b.fit === "frame" ? (
            // a picture of something (an episode's thumbnail): framed under the panel's marker title, clear of the
            // speaker card, landing with a short rise
            <>
              <svg width="100%" height="100%" viewBox={`0 0 ${PANEL.w} ${PANEL.h}`} style={{ position: "absolute", inset: 0 }}>
                <Header n={g.number} title={g.title} lt={lt} pal={pal} />
              </svg>
              <Img src={staticFile(b.src)} style={{ position: "absolute", left: 66 * S, top: 250 * S, width: 1120 * S, height: 630 * S,
                objectFit: "cover", borderRadius: 26 * S, boxShadow: `0 ${14 * S}px ${44 * S}px rgba(20,30,50,0.22)`,
                opacity: easeOut((lt - 0.2) / 0.35), transform: `translateY(${(1 - easeOut((lt - 0.2) / 0.35)) * 24 * S}px)` }} />
            </>
          ) : b.type === "image" ? (
            <Img src={staticFile(b.src)} style={{ width: "100%", height: "100%", objectFit: b.fit === "contain" ? "contain" : "cover",
              objectPosition: b.focus ? `${b.focus[0]}% ${b.focus[1]}%` : "50% 0%" }} />
          ) : b.type === "bullets" ? (
            <Bullets heading={b.heading} bullets={b.bullets} lt={lt} S={S} pal={pal} x={60} y={70} size={112} />
          ) : (
            <svg width="100%" height="100%" viewBox={`0 0 ${PANEL.w} ${PANEL.h}`}>
              <Header n={g.number} title={g.title} lt={lt} pal={pal} />
              {b.els.map((el, i) => <Draw key={i} el={el} lt={lt} pal={pal} />)}
            </svg>
          )}
        </Board>
        <SpeakerCard video={video} face={face} S={S} pal={pal} />
      </AbsoluteFill>
    );
  } else if (g?.kind === "title") {
    view = (
      <AbsoluteFill style={{ background: pal.white }}>
        <Bullets heading={g.heading} bullets={g.bullets} lt={lt} S={S} pal={pal} x={110} y={140} size={124} />
        <SpeakerCard video={video} face={face} S={S} pal={pal} />
      </AbsoluteFill>
    );
  } else if (g?.kind === "quote") {
    view = <Quote text={g.text} lt={lt} S={S} pal={pal} />;
  } else if (g?.kind === "chapter") {
    view = <Chapter n={g.number} title={g.title} lt={lt} S={S} pal={pal} />;
  } else if (g?.kind === "pills") {
    view = (
      <AbsoluteFill style={{ background: "#F4F7FB", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 22 * S, width: 1300 * S }}>
          {g.items.map((it, i) => <Pill key={i} text={it.text} S={S} pal={pal} p={Math.max(0, (lt - it.at) / POP_S)} size={58} />)}
        </div>
      </AbsoluteFill>
    );
  } else if (g?.kind === "buttons") {
    // one centred row under the chin (the references put them over the chest), shrunk to fit the room there
    const chinPx = (face.top + face.h * CHIN_IN_HEAD) * 1080;
    const size = Math.max(40, Math.min(64, (1040 - chinPx - 40) / 1.7));
    overlay = (
      <>
        <BottomShade S={S} p={easeSoft(lt / 0.5)} />
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 44 * S, display: "flex", flexWrap: "wrap", justifyContent: "center",
          gap: 22 * S, padding: `0 ${120 * S}px` }}>
          {/* every pill keeps its place from the start (the row never re-centres), unseen until it is said */}
          {g.items.map((it, i) => <Pill key={i} text={it.text} S={S} pal={pal} p={Math.max(0, (lt - it.at) / POP_S)} size={size} />)}
        </div>
      </>
    );
  } else if (g?.kind === "label") {
    overlay = (
      <div style={{ position: "absolute", left: 40 * S, bottom: 46 * S, background: pal.white, color: pal.ink, fontFamily: SANS,
        fontWeight: 600, fontSize: 40 * S, padding: `${16 * S}px ${38 * S}px`, borderRadius: 50 * S, opacity: easeSoft(lt / 0.5) }}>{g.text}</div>
    );
  } else if (g?.kind === "lower") {
    overlay = (
      <>
        <BottomShade S={S} p={easeSoft(lt / 0.5)} />
        <Spoken words={g.words} lt={lt} S={S} face={face} max={230} />
      </>
    );
  } else if (g?.kind === "script") {
    view = (
      <AbsoluteFill style={{ background: "#F8F9FA" }}>
        <Paper S={S} />
        <Script heading={g.heading} lines={g.lines} lt={lt} S={S} pal={pal} />
        <SpeakerCard video={video} face={face} S={S} pal={pal} />
      </AbsoluteFill>
    );
  }
  if (g && overlay) {
    // an overlay on the speaker eases out over its last EXIT_S: words, pills and shade fade, drift down and soften
    // together, never cut off (Ayush, 2026-10-10); the speaker under them is untouched
    const out = easeInOut((g.end - t) / EXIT_S);
    view = (
      <AbsoluteFill>
        {speaker}
        <AbsoluteFill style={{ opacity: out, transform: `translateY(${(1 - out) * 18 * S}px)`,
          filter: out < 1 ? `blur(${(1 - out) * 6 * S}px)` : undefined }}>{overlay}</AbsoluteFill>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {view}
      {audio}
    </AbsoluteFill>
  );
};
