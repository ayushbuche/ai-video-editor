// The white-page graphics of the sdr-mastery style (styles/sdr-mastery/teardown.md), drawn by LongEdit: full-screen
// white pages with one red accent, a clean sans for the text and an italic serif for spoken lines and headers. Words
// arrive as he says them (a soft fade up from light grey). Every size and colour here was measured on the reference's
// 1920 x 1080 frames (Wkxg6XCiSwE); positions are design px, scaled by S.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { loadFont as loadItalic } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadSans } from "@remotion/google-fonts/Inter";

const ITALIC = loadItalic("italic", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;
const SANS = loadSans("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] }).fontFamily;

export type Item = { text: string; at: number };
export type Words = Item[];
export type PagePal = { red: string; ink: string; marker: string; page: string; white: string };
export const PAGE_PAL: PagePal = { red: "#FF4A4A", ink: "#333333", marker: "#FE2828", page: "#FFFFFF", white: "#FFFFFF" };

export type PageGraphic =
  | { kind: "list"; heading?: string; sub?: Words; items: Words[]; marker: "number" | "dot" | "none"; card?: boolean }
  | { kind: "rows"; items: { label: string; text: Words; at: number | null }[]; preview?: boolean }
  | { kind: "dialogue"; turns: { head: string; head_at: number; line: Words }[] }
  | { kind: "rule"; heading: string; heading_at?: number; items: Words[]; dots?: boolean; card?: boolean }
  | { kind: "acronym"; word: string; items: Item[] }
  | { kind: "illustration"; image: string; line: Words; side_image?: string; side_text?: Words; side_at?: number }
  | { kind: "shot"; image: string; fit?: "full" | "frame"; scroll?: boolean }
  | { kind: "phrase"; lines: { words: Words; italic?: boolean }[] };
export const PAGE_KINDS = ["list", "rows", "dialogue", "rule", "acronym", "illustration", "shot"];

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const easeSoft = (x: number) => 1 - Math.pow(1 - clamp01(x), 5);
const easeInOut = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };

const WORD_S = 0.45;   // a word fades up from light grey to ink as it is said (reference: "1. Get specific on your")
const ENTER_S = 0.5;   // a page's content scales up into place (reference: from 0.4-0.8x with a fade, 0.25-1 s)
const UNDER_S = 0.7;   // a red marker underline draws on left to right
const BAR_S = 0.45;    // a red highlighter bar sweeps on behind a header

/** The page's content arriving: a quick scale up with a fade (power3 in-out), then still. */
const Enter: React.FC<{ lt: number; children: React.ReactNode }> = ({ lt, children }) => {
  const p = easeInOut(lt / ENTER_S);
  return <AbsoluteFill style={{ opacity: clamp01(lt / (ENTER_S * 0.6)), transform: `scale(${0.8 + 0.2 * p})` }}>{children}</AbsoluteFill>;
};

/** Words that arrive as they are said: unseen, then a light grey, then ink. Unsaid words keep their place. */
const Said: React.FC<{ words: Words; lt: number; color: string; ghost?: string }> = ({ words, lt, color, ghost = "#B9B9B9" }) => (
  <>
    {words.map((w, i) => {
      const q = clamp01((lt - w.at) / WORD_S);
      const c = q < 0.6 ? ghost : color;
      return <span key={i} style={{ opacity: easeSoft(q * 1.6), color: c, transition: "none" }}>{w.text}{i < words.length - 1 ? " " : ""}</span>;
    })}
  </>
);

/** The reference's hand-drawn red underline: a long stroke under the text that runs past its end and loops back
 *  under the last third (measured on "Things to do while list building:"). w: the text's width, design px. */
const Swoosh: React.FC<{ w: number; p: number; color: string; S: number; loop?: boolean; stroke?: number; lead?: number }> = (
  { w, p, color, S, loop = true, stroke = 9, lead = 80 }) => {
  const d = loop
    ? `M 0 14 C ${w * 0.35} 10 ${w * 0.75} 6 ${w + 70} 14 C ${w + 110} 20 ${w + 90} 28 ${w + 40} 30 C ${w * 0.85} 34 ${w * 0.72} 38 ${w * 0.66} 50`
    : `M 0 14 C ${w * 0.4} 8 ${w * 0.8} 6 ${w + 30} 12`;
  return (
    <svg width={(w + 140) * S} height={60 * S} viewBox={`0 0 ${w + 140} 60`} style={{ position: "absolute", left: -lead * S, overflow: "visible" }}>
      <path d={d} pathLength={1} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray="1 1"
        strokeDashoffset={1 - easeOut(p)} />
    </svg>
  );
};

/** An italic serif header with the red highlighter bar through its lower half ("Let's say someone said:"). */
const Highlit: React.FC<{ text: string; size: number; lt: number; at: number; S: number; pal: PagePal }> = ({ text, size, lt, at, S, pal }) => {
  const q = clamp01((lt - at) / BAR_S);
  return (
    <div style={{ position: "relative", display: "inline-block", fontFamily: ITALIC, fontStyle: "italic", fontWeight: 500, fontSize: size * S,
      lineHeight: 1.15, color: pal.ink, letterSpacing: -1 * S, whiteSpace: "nowrap", fontVariantNumeric: "lining-nums",
      opacity: easeSoft(clamp01((lt - at) / 0.3)) }}>
      <div style={{ position: "absolute", left: -6 * S, top: size * 0.52 * S, height: size * 0.42 * S, width: `calc(${easeOut(q) * 100}% - ${size * 0.15 * S}px)`,
        background: pal.red }} />
      <span style={{ position: "relative" }}>{text}</span>
    </div>
  );
};

const Card: React.FC<{ S: number; children: React.ReactNode; pad?: number }> = ({ S, children, pad = 48 }) => (
  <div style={{ background: "#F6F6F6", borderRadius: 28 * S, padding: `${pad * 0.8 * S}px ${pad * S}px`,
    boxShadow: `0 ${10 * S}px ${40 * S}px rgba(0,0,0,0.14), 0 ${2 * S}px ${6 * S}px rgba(0,0,0,0.06)` }}>{children}</div>
);

const textWidth = (s: string, size: number, em = 0.52) => s.length * size * em;

/** A title and its list: a centred sans heading on the red underline, the lines (numbered or red-dotted) arriving as
 *  he says them. With no heading, just the list, centred. card: the list sits on a soft shadowed card. */
const List: React.FC<{ g: Extract<PageGraphic, { kind: "list" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  const longest = Math.max(1, ...g.items.map((it) => it.map((w) => w.text).join(" ").length + (g.marker === "none" ? 0 : 3)));
  const n = g.items.length;
  // the reference's 68 px lines, smaller for a long line or a long list so it all fits under the heading
  const size = Math.max(40, Math.min(68, 1500 / (longest * 0.5), (g.heading ? 640 : 860) / Math.max(1, n * 1.5)));
  const hs = g.heading ? Math.min(100, 1650 / (g.heading.length * 0.52)) : 0;
  const body = (
    <div style={{ display: "inline-block", textAlign: "left" }}>
      {g.items.map((it, i) => it.length && lt >= it[0].at - 0.05 ? (
        <div key={i} style={{ fontFamily: SANS, fontWeight: 400, fontSize: size * S, lineHeight: 1.5, color: pal.ink, letterSpacing: -0.5 * S,
          display: "flex", alignItems: "baseline", gap: 14 * S }}>
          {g.marker === "dot" ? <span style={{ width: size * 0.32 * S, height: size * 0.32 * S, borderRadius: "50%", background: pal.red,
            flex: "none", transform: `translateY(${-size * 0.08 * S}px)` }} /> : g.marker === "number" ? <span>{i + 1}.</span> : null}
          <span><Said words={it} lt={lt} color={pal.ink} /></span>
        </div>
      ) : <div key={i} style={{ height: size * 1.5 * S }} />)}
    </div>
  );
  return (
    <AbsoluteFill style={{ background: pal.page }}>
      <Enter lt={lt}>
        <div style={{ position: "absolute", left: 0, right: 0, top: (g.heading ? 110 : 300) * S, textAlign: "center" }}>
          {g.heading ? (
            <div style={{ position: "relative", display: "inline-block", fontFamily: SANS, fontWeight: 600, fontSize: hs * S, color: pal.ink,
              letterSpacing: -2 * S, lineHeight: 1.1 }}>
              {g.heading}
              <div style={{ position: "absolute", left: 0, top: hs * 1.08 * S }}>
                <Swoosh w={textWidth(g.heading, hs)} p={(lt - 0.15) / UNDER_S} color={pal.marker} S={S} />
              </div>
            </div>
          ) : null}
          {g.sub ? (
            <div style={{ fontFamily: ITALIC, fontStyle: "italic", fontSize: hs * 0.62 * S, marginTop: 36 * S, lineHeight: 1.1 }}>
              <Said words={g.sub} lt={lt} color={pal.ink} />
            </div>
          ) : null}
          <div style={{ marginTop: (g.heading ? 120 : 0) * S }}>{g.card ? <div style={{ display: "inline-block" }}><Card S={S}>{body}</Card></div> : body}</div>
        </div>
      </Enter>
    </AbsoluteFill>
  );
};

/** Label rows: a filled red rounded label joined to a red-outlined box with the text (measured on "1% of my calls |
 *  Converted to a meeting"). A row arrives when it is said; with preview (the part card) every row is up from the start
 *  and a row's text stays blurred until it is said, so the parts still to come read as blurred. */
const Rows: React.FC<{ g: Extract<PageGraphic, { kind: "rows" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  const lw = Math.max(...g.items.map((r) => textWidth(r.label, 64, 0.55))) + 120;
  const tw = Math.max(...g.items.map((r) => textWidth(r.text.map((w) => w.text).join(" "), 54, 0.55))) + 120;
  const total = lw - 160 + tw + 120;
  const k = Math.min(1, 1600 / total);   // a long row shrinks to fit the frame
  const h = 148 * k, gap = 52 * k;
  const top = 540 - (g.items.length * h + (g.items.length - 1) * gap) / 2;
  return (
    <AbsoluteFill style={{ background: pal.page }}>
      <Enter lt={lt}>
        {g.items.map((r, i) => {
          const appear = g.preview ? 0 : (r.at ?? 0);
          const p = easeInOut((lt - appear) / 0.45);
          if (p <= 0) return null;
          const said = r.at !== null && lt >= r.at - 0.1;
          const blur = said ? 0 : 1;
          const x0 = 960 - (total * k) / 2;
          return (
            <div key={i} style={{ position: "absolute", left: x0 * S, top: (top + i * (h + gap)) * S, height: h * S, opacity: p,
              transform: `translateY(${(1 - p) * 20 * S}px)` }}>
              {/* the outlined box sits a little lower and runs from under the label to the right */}
              <div style={{ position: "absolute", left: (lw - 180) * k * S, top: 10 * k * S, width: (tw + 180) * k * S, height: h * S,
                border: `${4 * k * S}px solid ${pal.red}`, borderRadius: 36 * k * S, background: pal.white,
                display: "flex", alignItems: "center", justifyContent: "center", paddingLeft: 180 * k * S, boxSizing: "border-box" }}>
                <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 54 * k * S, color: pal.ink, letterSpacing: -1 * S, whiteSpace: "nowrap",
                  filter: g.preview && blur ? `blur(${9 * k * S}px)` : undefined, opacity: g.preview ? 1 : easeSoft(clamp01((lt - (r.at ?? 0)) / WORD_S)) }}>
                  {g.preview ? r.text.map((w) => w.text).join(" ") : <Said words={r.text} lt={lt} color={pal.ink} />}
                </span>
              </div>
              <div style={{ position: "absolute", left: 0, top: 0, width: lw * k * S, height: h * S, background: pal.red, opacity: 0.97,
                borderRadius: 34 * k * S, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: SANS, fontWeight: 600,
                fontSize: 64 * k * S, color: pal.white, letterSpacing: -1 * S, whiteSpace: "nowrap" }}>{r.label}</div>
            </div>
          );
        })}
      </Enter>
    </AbsoluteFill>
  );
};

/** A call script as the reference shows one: each turn an italic serif header on the red highlighter ("Let's say
 *  someone said:", "I will say:") with the line in sans quotes under it. Turns add on and stay. */
const Dialogue: React.FC<{ g: Extract<PageGraphic, { kind: "dialogue" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  // the reference's 110 px headers and 46 px lines with two turns; more turns or long lines get smaller, wrapping in 1080 px
  const lineRows = (f: number) => g.turns.reduce((n, t) => n + Math.ceil(t.line.map((w) => w.text).join(" ").length * 0.5 * f / 1080), 0);
  const longHead = Math.max(...g.turns.map((t) => t.head.length));
  let k = Math.min(1, 1050 / (longHead * 0.47 * 110));
  while (k > 0.45 && g.turns.length * 110 * k * 1.25 + lineRows(46 * k) * 46 * k * 1.3 + g.turns.length * 40 * k > 900) k -= 0.03;
  return (
    <AbsoluteFill style={{ background: "#FAFAFA" }}>
      <Enter lt={lt}>
        <div style={{ position: "absolute", left: 420 * S, top: 60 * S, width: 1100 * S }}>
          {g.turns.map((t, i) => lt < t.head_at - 0.05 ? null : (
            <div key={i} style={{ marginBottom: 34 * k * S }}>
              <div style={{ marginLeft: 50 * k * S }}><Highlit text={t.head} size={110 * k} lt={lt} at={t.head_at} S={S} pal={pal} /></div>
              <div style={{ fontFamily: SANS, fontWeight: 400, fontSize: 46 * k * S, lineHeight: 1.3, letterSpacing: -0.5 * S, marginTop: 6 * k * S }}>
                <Said words={t.line.map((w, j) => ({ ...w, text: (j === 0 ? "“" : "") + w.text + (j === t.line.length - 1 ? "”" : "") }))}
                  lt={lt} color={pal.ink} />
              </div>
            </div>
          ))}
        </div>
      </Enter>
    </AbsoluteFill>
  );
};

/** One rule: the italic header on the highlighter and a sans line or red-dotted lines under it, on a soft card or on
 *  the page ("The one rule that I have is:" / "I call every prospect:"). */
const Rule: React.FC<{ g: Extract<PageGraphic, { kind: "rule" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  const hs = Math.min(96, 1500 / (g.heading.length * 0.42));
  const inner = (
    <div style={{ textAlign: g.card ? "left" : "center" }}>
      <Highlit text={g.heading} size={hs} lt={lt} at={g.heading_at ?? 0} S={S} pal={pal} />
      {g.items.map((it, i) => it.length && lt >= it[0].at - 0.05 ? (
        <div key={i} style={{ fontFamily: SANS, fontWeight: 500, fontSize: 48 * S, color: pal.ink, marginTop: (i ? 10 : 22) * S,
          display: "flex", alignItems: "baseline", gap: 14 * S, justifyContent: g.card ? "flex-start" : "center", letterSpacing: -0.5 * S }}>
          {g.dots ? <span style={{ width: 16 * S, height: 16 * S, borderRadius: "50%", background: pal.red, flex: "none" }} /> : null}
          <span><Said words={it} lt={lt} color={pal.ink} /></span>
        </div>
      ) : null)}
    </div>
  );
  return (
    <AbsoluteFill style={{ background: "#FAFAFA", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Enter lt={lt}>
        <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          {g.card ? <Card S={S} pad={56}>{inner}</Card> : inner}
        </AbsoluteFill>
      </Enter>
    </AbsoluteFill>
  );
};

/** An acronym ("BANT"): huge heavy letters on a red bar on a soft card, the word for each letter written under it in
 *  italic serif as he says it, joined to its letter by a thin hand-drawn line. */
const Acronym: React.FC<{ g: Extract<PageGraphic, { kind: "acronym" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  const letters = [...g.word];
  const lsz = Math.min(230, 1250 / (letters.length * 1.05));
  const cw = lsz * 1.05;   // each letter's column: wide enough for the word under it (reference: "Budget  Authority  Need  Timing")
  const w = cw * letters.length;
  return (
    <AbsoluteFill style={{ background: "#FAFAFA", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Enter lt={lt}>
        <AbsoluteFill style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Card S={S} pad={90}>
            <div style={{ position: "relative", width: (w + 120) * S, height: (lsz * 1.75) * S }}>
              <div style={{ position: "absolute", left: 50 * S, top: lsz * 0.45 * S, height: lsz * 0.5 * S, width: (w + 20) * easeOut(lt / BAR_S) * S,
                background: pal.red }} />
              {letters.map((c, i) => (
                <div key={i} style={{ position: "absolute", left: (60 + i * cw) * S, width: cw * S, top: 0, textAlign: "center", fontFamily: SANS,
                  fontWeight: 800, fontSize: lsz * S, lineHeight: 1, color: pal.ink }}>{c}</div>
              ))}
              {g.items.map((it, i) => {
                const q = clamp01((lt - it.at) / WORD_S);
                if (q <= 0) return null;
                const cx = 60 + (i + 0.5) * cw;
                return (
                  <React.Fragment key={i}>
                    <svg width={cw * S} height={lsz * 0.4 * S} viewBox={`0 0 ${cw} ${lsz * 0.4}`} style={{ position: "absolute",
                      left: (cx - cw / 2) * S, top: lsz * 0.92 * S }}>
                      <path d={`M ${cw * 0.5} 4 C ${cw * 0.38} ${lsz * 0.12} ${cw * 0.36} ${lsz * 0.22} ${cw * 0.4} ${lsz * 0.34}`} pathLength={1}
                        fill="none" stroke={pal.ink} strokeWidth={2.5} strokeDasharray="1 1" strokeDashoffset={1 - easeOut(q * 1.4)} />
                    </svg>
                    <div style={{ position: "absolute", left: (cx - cw) * S, width: cw * 2 * S, top: lsz * 1.3 * S, textAlign: "center",
                      fontFamily: ITALIC, fontStyle: "italic", fontSize: lsz * 0.2 * S, color: pal.ink, opacity: easeSoft(q * 1.6) }}>{it.text}</div>
                  </React.Fragment>
                );
              })}
            </div>
          </Card>
        </AbsoluteFill>
      </Enter>
    </AbsoluteFill>
  );
};

/** An illustration made for this video (navy line-art, one character style), its line in italic serif on a red
 *  underline beneath; optionally a picture or a short line beside it, arriving when it is said. */
const Illustration: React.FC<{ g: Extract<PageGraphic, { kind: "illustration" }>; lt: number; S: number; pal: PagePal }> = ({ g, lt, S, pal }) => {
  const side = !!(g.side_image || g.side_text);
  const sideP = easeInOut((lt - (g.side_at ?? 0)) / 0.45);
  const lineText = g.line.map((w) => w.text).join(" ");
  const ls = Math.min(72, (side ? 1000 : 1500) / (lineText.length * 0.47));
  const enter = easeOut(lt / 0.35);
  return (
    <AbsoluteFill style={{ background: pal.page }}>
      <div style={{ position: "absolute", left: (side ? 200 : 560) * S, top: 120 * S, width: 800 * S, height: 600 * S,
        opacity: enter, transform: `translateY(${(1 - enter) * -60 * S}px)` }}>
        <Img src={staticFile(g.image)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      </div>
      <div style={{ position: "absolute", left: (side ? 140 : 0) * S, right: (side ? 860 : 0) * S, top: 760 * S, textAlign: "center" }}>
        <div style={{ position: "relative", display: "inline-block", fontFamily: ITALIC, fontStyle: "italic", fontSize: ls * S, lineHeight: 1.1,
          letterSpacing: -0.8 * S, whiteSpace: "nowrap", fontVariantNumeric: "lining-nums" }}>
          <Said words={g.line} lt={lt} color={pal.ink} ghost="#C9C9C9" />
          <div style={{ position: "absolute", left: 0, top: ls * 1.05 * S }}>
            <Swoosh w={textWidth(lineText, ls, 0.45)} p={(lt - (g.line[0]?.at ?? 0)) / (UNDER_S * 1.4)} color={pal.marker} S={S} stroke={7} />
          </div>
        </div>
      </div>
      {side && sideP > 0 ? (
        <div style={{ position: "absolute", left: 1080 * S, top: 200 * S, width: 700 * S, height: 600 * S, opacity: sideP,
          transform: `scale(${0.85 + 0.15 * sideP})`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 30 * S }}>
          {g.side_image ? <Img src={staticFile(g.side_image)} style={{ maxWidth: "100%", maxHeight: 380 * S, objectFit: "contain" }} /> : null}
          {g.side_text ? <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 62 * S, lineHeight: 1.1, color: pal.ink, textAlign: "center",
            letterSpacing: -1 * S }}><Said words={g.side_text} lt={lt} color={pal.ink} /></div> : null}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/** A real screenshot: full frame (a slow scroll down a tall page when asked) or framed with a soft shadow on white. */
const Shot: React.FC<{ g: Extract<PageGraphic, { kind: "shot" }>; lt: number; dur: number; S: number; pal: PagePal }> = ({ g, lt, dur, S, pal }) => {
  const p = easeInOut(lt / ENTER_S);
  if (g.fit === "frame") {
    return (
      <AbsoluteFill style={{ background: pal.page, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Img src={staticFile(g.image)} style={{ maxWidth: 1500 * S, maxHeight: 860 * S, borderRadius: 18 * S, objectFit: "contain",
          boxShadow: `0 ${16 * S}px ${50 * S}px rgba(0,0,0,0.18)`, opacity: clamp01(lt / 0.3), transform: `scale(${0.6 + 0.4 * p})` }} />
      </AbsoluteFill>
    );
  }
  const scroll = g.scroll ? easeInOut((lt - 0.8) / Math.max(1, dur - 1.6)) : 0;
  return (
    <AbsoluteFill style={{ background: pal.page, opacity: clamp01(lt / 0.3), transform: `scale(${0.6 + 0.4 * p})` }}>
      <Img src={staticFile(g.image)} style={{ width: "100%", height: g.scroll ? "auto" : "100%", objectFit: "cover",
        objectPosition: "50% 0%", transform: g.scroll ? `translateY(calc(${-scroll} * (100% - ${1080 * S}px)))` : undefined }} />
    </AbsoluteFill>
  );
};

/** A short spoken phrase over the speaker, low in the frame: a line of white bold sans and a larger line of white
 *  italic serif on a red underline ("Most people mess up / because they start off wrong"), each word fading in as it
 *  is said. The type keeps under the chin. */
export const Phrase: React.FC<{ lines: { words: Words; italic?: boolean }[]; lt: number; S: number; chinPx: number; pal: PagePal }> = (
  { lines, lt, S, chinPx, pal }) => {
  const room = 1040 - chinPx;   // design px between the chin and the frame's foot
  const longest = Math.max(...lines.map((l) => l.words.map((w) => w.text).join(" ").length * (l.italic ? 0.42 : 0.55)));
  const base = Math.max(44, Math.min(110, 1600 / Math.max(1, longest), room / (lines.length * 1.1)));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 40 * S, textAlign: "center", color: "#FFFFFF",
      textShadow: `0 ${2 * S}px ${16 * S}px rgba(0,0,0,0.35)` }}>
      {lines.map((l, i) => {
        const size = l.italic ? base * 1.15 : base * 0.82;
        const text = l.words.map((w) => w.text).join(" ");
        return (
          <div key={i} style={{ position: "relative", display: "block", fontFamily: l.italic ? ITALIC : SANS, fontStyle: l.italic ? "italic" : "normal",
            fontWeight: l.italic ? 400 : 700, fontSize: size * S, lineHeight: 1.05, letterSpacing: (l.italic ? -1 : -1.5) * S, whiteSpace: "nowrap" }}>
            {l.words.map((w, j) => {
              const q = easeSoft((lt - w.at) / WORD_S);
              return <span key={j} style={{ opacity: q, filter: q > 0 && q < 1 ? `blur(${(1 - q) * 5 * S}px)` : undefined }}>{w.text}{j < l.words.length - 1 ? " " : ""}</span>;
            })}
            {l.italic && l.words.length ? (
              <div style={{ position: "absolute", left: `calc(50% - ${(textWidth(text, size, 0.45) / 2 + 20) * S}px)`, top: size * 0.98 * S,
                textShadow: "none" }}>
                <Swoosh w={textWidth(text, size, 0.45) * 0.85} p={(lt - l.words[0].at) / (UNDER_S * 1.5)} color={pal.marker} S={S} loop={false}
                  stroke={6} lead={0} />
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};

/** One full-screen page graphic (not phrase: that one is an overlay on the speaker). */
export const Page: React.FC<{ g: PageGraphic; lt: number; dur: number; S: number; pal: PagePal }> = ({ g, lt, dur, S, pal }) => {
  switch (g.kind) {
    case "list": return <List g={g} lt={lt} S={S} pal={pal} />;
    case "rows": return <Rows g={g} lt={lt} S={S} pal={pal} />;
    case "dialogue": return <Dialogue g={g} lt={lt} S={S} pal={pal} />;
    case "rule": return <Rule g={g} lt={lt} S={S} pal={pal} />;
    case "acronym": return <Acronym g={g} lt={lt} S={S} pal={pal} />;
    case "illustration": return <Illustration g={g} lt={lt} S={S} pal={pal} />;
    case "shot": return <Shot g={g} lt={lt} dur={dur} S={S} pal={pal} />;
    default: return null;
  }
};
