#!/usr/bin/env python3
"""Marker diagrams for the long-form panel (remotion/src/LongEdit.tsx "panel" with body.type "diagram").

    python3 diagrams.py demo        self-check

Each template turns a short spec into drawn elements in panel-local design px (the panel is
1364 x 970; the numbered header owns the top 220). Strokes wobble like a hand-drawn marker
(seeded, so a re-plan draws the same lines) and every element carries `at`: seconds into the
panel when it draws on, from the word that names it. Measured in the references
(styles/axis-story/teardown.md): a stroke draws in 0.6 s, a label writes on letter by letter in
about 1 s with its underline, blue for the shape, red for emphasis, dark grey for words, green
for small side notes.

Templates (spec keys; every item is {"text", "at"}):
  flow      items: 2-5 steps left to right, a box each, arrows between
  swoosh    items: 2-5 stages along a rising hockey-stick curve (growth, a journey)
  pyramid   items: 2-4 levels, top first
  mindmap   center: {"text", "at"}, items: 2-6 branches
  list      items: 2-5 lines, each with a marker arrow; `cross`: true strikes them through when said
  compare   left: {"text", "at"}, right: {"text", "at"}, left_items, right_items: 0-4 each
  letters   items: 2-5 words whose first letters spell the title (P / E / G), letter big in red
Stdlib only.
"""
import math
import random
import sys

W, H = 1364, 970
UW = 1190            # the usable width: the speaker card covers the panel's right edge from x 1262 (measured
                     # layout), so content stops short of it
TOP = 250            # content starts under the header
BLUE, RED, GREEN, INK = "#2655A3", "#C71338", "#2F8A5B", "#3A3A3A"
CHAR_W = 0.5         # marker caps: width of a character per px of font size (Patrick Hand, measured ~0.48)


def _rng(seed):
    return random.Random(seed)


def wobble_line(x1, y1, x2, y2, r, amt=0.012):
    """A marker line: a cubic through two points nudged off the straight line, and a slight overshoot."""
    L = math.hypot(x2 - x1, y2 - y1) or 1
    nx, ny = -(y2 - y1) / L, (x2 - x1) / L
    j = lambda: r.uniform(-1, 1) * amt * L  # noqa: E731
    over = r.uniform(0.0, 0.02)
    ex, ey = x2 + (x2 - x1) * over, y2 + (y2 - y1) * over
    c1 = (x1 + (x2 - x1) / 3 + nx * j(), y1 + (y2 - y1) / 3 + ny * j())
    c2 = (x1 + 2 * (x2 - x1) / 3 + nx * j(), y1 + 2 * (y2 - y1) / 3 + ny * j())
    return f"M {x1:.1f} {y1:.1f} C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {ex:.1f} {ey:.1f}"


def box(x, y, w, h, r):
    """Four strokes in one path, each corner overshooting a little, as a marker box is drawn."""
    o = lambda: r.uniform(4, 10)  # noqa: E731
    segs = [wobble_line(x - o(), y, x + w + o(), y + r.uniform(-3, 3), r, 0.006),
            wobble_line(x + w, y - o(), x + w + r.uniform(-3, 3), y + h + o(), r, 0.01),
            wobble_line(x + w + o(), y + h, x - o(), y + h + r.uniform(-3, 3), r, 0.006),
            wobble_line(x, y + h + o(), x + r.uniform(-3, 3), y - o(), r, 0.01)]
    return " ".join(segs)


def ellipse(cx, cy, rx, ry, r):
    """A loop drawn in one go that overshoots where it started, like the references' circled words."""
    pts, n = [], 28
    a0 = r.uniform(-2.4, -1.8)
    for i in range(n + 3):
        a = a0 + 2 * math.pi * i / n
        k = 1 + r.uniform(-0.03, 0.03)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1, 2):
        d += f" Q {pts[i][0]:.1f} {pts[i][1]:.1f} {pts[i + 1][0]:.1f} {pts[i + 1][1]:.1f}"
    return d


def arrow(x1, y1, x2, y2, r, head=26):
    a = math.atan2(y2 - y1, x2 - x1)
    d = wobble_line(x1, y1, x2, y2, r)
    for s in (2.6, -2.6):
        d += " " + wobble_line(x2, y2, x2 + head * math.cos(a + s), y2 + head * math.sin(a + s), r, 0.03)
    return d


def path(d, at, color=BLUE, w=9, dur=0.6):
    return {"t": "path", "d": d, "at": round(max(0.0, at), 3), "color": color, "w": w, "dur": dur}


def text(s, x, y, at, size=72, color=INK, anchor="middle", rot=0, underline=None, font="marker"):
    e = {"t": "text", "text": s, "x": round(x, 1), "y": round(y, 1), "at": round(max(0.0, at), 3), "size": size,
         "color": color, "anchor": anchor, "font": font}
    if rot:
        e["rot"] = rot
    if underline:
        e["underline"] = underline
    return e


def fit(s, max_w, size):
    """The largest font size, at most `size`, at which s fits max_w px."""
    return max(34, min(size, int(max_w / max(1, len(s)) / CHAR_W)))


def flow(spec, r):
    items = spec["items"][:5]
    n = len(items)
    gap = 90
    bw = (UW - 120 - gap * (n - 1)) / n
    bh = 190
    y = TOP + (H - TOP - bh) / 2 - 20
    els = []
    for i, it in enumerate(items):
        x = 60 + i * (bw + gap)
        els.append(path(box(x, y, bw, bh, r), it["at"] - 0.1))
        words = it["text"].upper()
        els.append(text(words, x + bw / 2, y + bh / 2 + 24, it["at"] + 0.2, fit(words, bw - 30, 70)))
        if i:
            px = x - gap
            els.append(path(arrow(px + 12, y + bh / 2, x - 14, y + bh / 2, r), it["at"] - 0.45, RED, 7, 0.4))
    return els


def swoosh(spec, r):
    items = spec["items"][:5]
    # the references' hockey stick: a short hook down-left, a long rise to the top right with a loop
    d = ("M 300 420 L 250 495 M 300 420 C 230 560 250 680 340 690 C 540 700 820 430 1010 280 "
         "C 1090 220 1130 200 1080 220 C 1040 236 990 280 930 320")
    els = [path(d, items[0]["at"] - 0.7 if items else 0, BLUE, 9, 0.6)]
    # stage points just under the curve, low left to high right, clear of each other and of the speaker card
    spots = [(300, 790, 0), (560, 730, -16), (740, 615, -27), (890, 505, -33), (1020, 410, -35)]
    pick = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 2, 4], 5: [0, 1, 2, 3, 4]}.get(len(items), [0])
    for it, k in zip(items, pick):
        x, y, rot = spots[k]
        s = it["text"].upper()
        els.append(text(s, x, y, it["at"], fit(s, 250, 62), INK, "middle", rot, BLUE))
    return els


def pyramid(spec, r):
    items = spec["items"][:4]
    n = len(items)
    top, base, cx = (TOP + 10, H - 70, UW * 0.45)
    half = (base - top) * 0.72
    els = [path(wobble_line(cx, top, cx - half, base, r) + " " + wobble_line(cx - half, base, cx + half, base, r) + " "
                + wobble_line(cx + half, base, cx, top, r), items[0]["at"] - 0.7 if items else 0)]
    for i, it in enumerate(items):
        y1 = top + (base - top) * (i + 1) / n
        w1 = half * (y1 - top) / (base - top)
        if i < n - 1:
            els.append(path(wobble_line(cx - w1, y1, cx + w1, y1, r, 0.008), it["at"] - 0.3, BLUE, 7, 0.4))
        ym = top + (base - top) * (i + 0.62) / n
        s = it["text"]
        wmid = 2 * half * (ym - top) / (base - top)
        if wmid > 260:
            els.append(text(s.upper(), cx, ym + 20, it["at"], fit(s, wmid - 60, 64)))
        else:
            els.append(text(s, cx + half * 0.55 + 60, ym + 20, it["at"], 58, GREEN, "start"))
    return els


def mindmap(spec, r):
    c = spec["center"]
    items = spec["items"][:6]
    cx, cy = UW * 0.5, TOP + (H - TOP) / 2
    s = c["text"]
    rx = max(150, len(s) * 40)
    els = [path(ellipse(cx, cy, rx, 95, r), c["at"] - 0.2, INK, 6, 0.6), text(s, cx, cy + 26, c["at"] + 0.2, fit(s, 2 * rx - 60, 86), INK,
                                                                           font="script")]
    angs = {2: [200, -20], 3: [210, -90, -30], 4: [215, 145, -35, 35], 5: [210, 150, -90, -30, 30],
            6: [210, 150, -90, -30, 30, 90]}[max(2, len(items))]
    for it, a in zip(items, angs):
        t = math.radians(a)
        x1, y1 = cx + (rx + 8) * math.cos(t), cy + 103 * math.sin(t)
        x2, y2 = cx + (rx + 90) * math.cos(t), cy + 230 * math.sin(t)
        els.append(path(wobble_line(x1, y1, x2, y2, r), it["at"] - 0.3, INK, 5, 0.35))
        anchor = "end" if math.cos(t) < -0.3 else "start" if math.cos(t) > 0.3 else "middle"
        lx = x2 + (12 if anchor == "start" else -12 if anchor == "end" else 0)
        room = UW - lx - 10 if anchor == "start" else lx - 30 if anchor == "end" else 2 * min(lx - 30, UW - lx - 10)
        els.append(text(it["text"], lx,
                        y2 + (16 if math.sin(t) >= 0 else -14) + (40 if abs(math.cos(t)) < 0.3 and math.sin(t) > 0 else 0),
                        it["at"], fit(it["text"], room, 56), GREEN, anchor))
    return els


def listing(spec, r):
    items = spec["items"][:5]
    n = len(items)
    step = min(150, (H - TOP - 60) / max(1, n))
    els = []
    for i, it in enumerate(items):
        y = TOP + 60 + i * step
        els.append(path(arrow(90, y - 18, 190, y - 18, r, 22), it["at"] - 0.25, RED, 7, 0.3))
        s = it["text"]
        size = fit(s, UW - 280, 78)
        els.append(text(s, 230, y + 6, it["at"], size, INK, "start"))
        if spec.get("cross") and it.get("cross_at") is not None:
            els.append(path(wobble_line(220, y - size * 0.25, 240 + len(s) * size * CHAR_W, y - size * 0.3, r, 0.01),
                            it["cross_at"], RED, 8, 0.35))
    return els


def compare(spec, r):
    els = [path(wobble_line(UW / 2, TOP + 10, UW / 2 + 6, H - 60, r, 0.005), spec["left"]["at"] - 0.5, INK, 5, 0.5)]
    for side, x0 in (("left", UW * 0.25), ("right", UW * 0.75)):
        h = spec[side]
        els.append(text(h["text"], x0, TOP + 70, h["at"], fit(h["text"], UW * 0.44, 84), BLUE if side == "left" else RED,
                        underline=BLUE if side == "left" else RED, font="script"))
        for i, it in enumerate(spec.get(f"{side}_items", [])[:4]):
            els.append(text(it["text"], x0, TOP + 200 + i * 120, it["at"], fit(it["text"], UW * 0.42, 62), INK))
    return els


def letters(spec, r):
    items = spec["items"][:5]
    n = len(items)
    step = min(170, (H - TOP - 40) / max(1, n))
    els = []
    for i, it in enumerate(items):
        y = TOP + 90 + i * step
        s = it["text"]
        els.append(text(s[0].upper(), 150, y + 20, it["at"] - 0.15, 120, RED, "middle", font="script"))
        els.append(text(s, 260, y, it["at"] + 0.1, fit(s, UW - 300, 80), INK, "start", underline=BLUE))
    return els


TEMPLATES = {"flow": flow, "swoosh": swoosh, "pyramid": pyramid, "mindmap": mindmap, "list": listing,
             "compare": compare, "letters": letters}


def build(spec, seed=0):
    """spec {"type": <template>, ...} with every `at` already in seconds into the panel -> elements."""
    kind = spec.get("type")
    if kind not in TEMPLATES:
        raise ValueError(f"unknown diagram {kind!r}: one of {', '.join(TEMPLATES)}")
    return TEMPLATES[kind](spec, _rng(seed))


def bounds(els):
    """Elements drawn outside the panel (a text estimate: marker caps at CHAR_W em)."""
    bad = []
    for e in els:
        if e["t"] != "text":
            continue
        w = len(e["text"]) * e.get("size", 72) * CHAR_W
        a = e.get("anchor", "start")
        x0 = e["x"] - (w / 2 if a == "middle" else w if a == "end" else 0)
        if x0 < 20 or x0 + w > UW or e["y"] > H - 10 or e["y"] - e.get("size", 72) < TOP - 30:
            bad.append(e["text"])
    return bad


def demo():
    items = [{"text": t, "at": 1 + i} for i, t in enumerate(["Meeting", "Pilot", "First dollars", "Intros"])]
    for k in TEMPLATES:
        spec = {"type": k, "items": items, "center": {"text": "You", "at": 0.5},
                "left": {"text": "Convince", "at": 0.5}, "right": {"text": "Discover", "at": 2}}
        els = build(spec, 3)
        assert els and all(e["at"] >= 0 for e in els), k
        assert build(spec, 3) == els, f"{k} is not deterministic"
        assert not bounds(els), (k, bounds(els))
    assert bounds([text("x" * 60, 100, 500, 0)]) == ["x" * 60]
    print("diagrams ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["demo"]:
        demo()
    else:
        sys.exit(__doc__)
