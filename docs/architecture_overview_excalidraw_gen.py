#!/usr/bin/env python3
"""Génère docs/architecture.excalidraw (version lisible) + un aperçu SVG.

Modèle : boîtes (rectangles avec texte lié), zones (rectangles pointillés + titre),
flèches liées (startBinding/endBinding) avec étiquette optionnelle.
"""

from __future__ import annotations

import json
import math
import random
import sys
import textwrap
from pathlib import Path

random.seed(42)
NOW = 1760000000000

# ---------- palette (Excalidraw) ----------
C_EXT = "#e9ecef"      # externe
C_ORCH = "#fcc2d7"     # orchestration
C_COMPUTE = "#ffd8a8"  # compute
C_STORE = "#b2f2bb"    # stockage
C_ANALYTICS = "#d0bfff"  # catalogue / requêtes
C_OBS = "#a5d8ff"      # observabilité
C_SEC = "#ffc9c9"      # IAM / sécurité
C_AGENT = "#ffec99"    # agent
C_HUMAN = "#c3fae8"    # humains / front
C_IAC = "#eebefa"      # terraform / CI

FONT_HAND, FONT_NORMAL, FONT_MONO = 1, 2, 3

elements: list[dict] = []
boxes: dict[str, dict] = {}
_ids = 0


def nid(prefix: str) -> str:
    global _ids
    _ids += 1
    return f"{prefix}-{_ids:03d}"


def seed() -> int:
    return random.randint(1, 2**31 - 1)


def base(kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
    el = {
        "type": kind,
        "id": kw.pop("id", nid(kind)),
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": kw.pop("strokeColor", "#1e1e1e"),
        "backgroundColor": kw.pop("backgroundColor", "transparent"),
        "fillStyle": kw.pop("fillStyle", "solid"),
        "strokeWidth": kw.pop("strokeWidth", 2),
        "strokeStyle": kw.pop("strokeStyle", "solid"),
        "roughness": kw.pop("roughness", 1),
        "opacity": kw.pop("opacity", 100),
        "groupIds": kw.pop("groupIds", []),
        "frameId": None,
        "roundness": kw.pop("roundness", {"type": 3}),
        "seed": seed(),
        "version": 1,
        "versionNonce": seed(),
        "isDeleted": False,
        "boundElements": kw.pop("boundElements", []),
        "updated": NOW,
        "link": None,
        "locked": kw.pop("locked", False),
    }
    el.update(kw)
    return el


def wrap(text: str, width_px: float, font_size: int, font: int) -> list[str]:
    char_w = (0.60 if font == FONT_MONO else 0.62) * font_size
    max_chars = max(8, int(width_px / char_w))
    out: list[str] = []
    for para in text.split("\n"):
        if not para:
            out.append("")
            continue
        out.extend(textwrap.wrap(para, max_chars, break_long_words=False, break_on_hyphens=False) or [""])
    return out


def text_el(
    x: float,
    y: float,
    w: float,
    text: str,
    font_size: int = 16,
    font: int = FONT_HAND,
    align: str = "center",
    valign: str = "middle",
    container: str | None = None,
    color: str = "#1e1e1e",
    h: float | None = None,
) -> dict:
    lines = wrap(text, w, font_size, font)
    th = len(lines) * font_size * 1.25
    el = base(
        "text",
        x,
        y,
        w,
        h if h is not None else th,
        strokeColor=color,
        roundness=None,
        text="\n".join(lines),
        originalText=text,
        fontSize=font_size,
        fontFamily=font,
        textAlign=align,
        verticalAlign=valign,
        containerId=container,
        lineHeight=1.25,
        autoResize=True,
        baseline=th - font_size * 0.25,
    )
    return el


def box(
    key: str,
    x: float,
    y: float,
    w: float,
    label: str,
    bg: str,
    h: float | None = None,
    font_size: int = 16,
    font: int = FONT_HAND,
    stroke: str = "#1e1e1e",
    dashed: bool = False,
    align: str = "center",
) -> dict:
    lines = wrap(label, w - 24, font_size, font)
    th = len(lines) * font_size * 1.25
    bh = h if h is not None else max(44, th + 24)
    rect = base(
        "rectangle",
        x,
        y,
        w,
        bh,
        id=key,
        backgroundColor=bg,
        strokeColor=stroke,
        strokeStyle="dashed" if dashed else "solid",
    )
    txt = text_el(x + 12, y + (bh - th) / 2, w - 24, label, font_size, font, align=align, container=key, h=th)
    rect["boundElements"].append({"id": txt["id"], "type": "text"})
    elements.append(rect)
    elements.append(txt)
    boxes[key] = rect
    return rect


def zone(key: str, x: float, y: float, w: float, h: float, title: str, bg: str = "#f8f9fa", stroke: str = "#868e96") -> dict:
    rect = base(
        "rectangle",
        x,
        y,
        w,
        h,
        id=key,
        backgroundColor=bg,
        strokeColor=stroke,
        strokeStyle="dashed",
        roughness=0,
        strokeWidth=1,
        opacity=100,
    )
    elements.append(rect)
    elements.append(text_el(x + 16, y + 10, w - 32, title, 20, FONT_HAND, align="left", valign="top", color=stroke))
    boxes[key] = rect
    return rect


def note(x: float, y: float, w: float, text: str, font_size: int = 13, font: int = FONT_NORMAL, color: str = "#495057") -> dict:
    el = text_el(x, y, w, text, font_size, font, align="left", valign="top", color=color)
    elements.append(el)
    return el


def _clip(cx: float, cy: float, tx: float, ty: float, r: dict) -> tuple[float, float]:
    """Point d'intersection du segment centre→cible avec le bord du rectangle r."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = r["width"] / 2, r["height"] / 2
    sx = hw / abs(dx) if dx else math.inf
    sy = hh / abs(dy) if dy else math.inf
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def center(r: dict) -> tuple[float, float]:
    return r["x"] + r["width"] / 2, r["y"] + r["height"] / 2


def arrow(
    src: str,
    dst: str,
    label: str | None = None,
    via: list[tuple[float, float]] | None = None,
    color: str = "#1e1e1e",
    dashed: bool = False,
    width: int = 2,
    label_w: float = 150,
) -> dict:
    a, b = boxes[src], boxes[dst]
    acx, acy = center(a)
    bcx, bcy = center(b)
    first_target = via[0] if via else (bcx, bcy)
    last_source = via[-1] if via else (acx, acy)
    sx, sy = _clip(acx, acy, *first_target, a)
    ex, ey = _clip(bcx, bcy, *last_source, b)
    pts = [(sx, sy), *(via or []), (ex, ey)]
    rel = [[px - sx, py - sy] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    el = base(
        "arrow",
        sx,
        sy,
        max(xs) - min(xs),
        max(ys) - min(ys),
        strokeColor=color,
        strokeStyle="dashed" if dashed else "solid",
        strokeWidth=width,
        roundness={"type": 2},
        points=rel,
        lastCommittedPoint=None,
        startBinding={"elementId": src, "focus": 0, "gap": 4},
        endBinding={"elementId": dst, "focus": 0, "gap": 4},
        startArrowhead=None,
        endArrowhead="arrow",
        elbowed=False,
    )
    a["boundElements"].append({"id": el["id"], "type": "arrow"})
    b["boundElements"].append({"id": el["id"], "type": "arrow"})
    elements.append(el)
    if label:
        # étiquette liée : placée au milieu du tracé
        mid_i = len(pts) // 2
        if len(pts) % 2 == 0:
            (x1, y1), (x2, y2) = pts[mid_i - 1], pts[mid_i]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        else:
            mx, my = pts[mid_i]
        lines = wrap(label, label_w, 12, FONT_NORMAL)
        th = len(lines) * 12 * 1.25
        t = text_el(mx - label_w / 2, my - th / 2, label_w, label, 12, FONT_NORMAL, container=el["id"], color=color, h=th)
        el["boundElements"].append({"id": t["id"], "type": "text"})
        elements.append(t)
    return el


# =====================================================================
# LAYOUT v2 — lisible : 4 bandes, peu de mots, flux gauche → droite
# =====================================================================
FS = 18          # texte des boîtes
FZ = 26          # titres de zones

elements.append(text_el(40, 10, 1600, "data-platform — vue d'ensemble", 40, FONT_HAND, align="left", valign="top"))
note(40, 66, 1900, "Chaque matin : BODACC → S3 → Spark → table events. Surveillé par CloudWatch. Un agent lit tout, ne modifie rien sans ton accord.", 18, FONT_HAND)

# ---------- 1. Pipeline ----------
zone("z1", 40, 120, 1920, 420, "1 · Pipeline quotidien", bg="#fff4e6", stroke="#e8590c")
box("scheduler", 80, 175, 230, "EventBridge\n06:30", C_ORCH, font_size=FS)
box("sfn", 380, 175, 760, "Step Functions · daily-pipeline\ningest → normalize → validate → publish → notify", C_ORCH, font_size=FS)
box("bodacc", 80, 360, 230, "API BODACC\n(annonces J-1)", C_EXT, font_size=FS)
box("ingest", 380, 360, 230, "Lambda\ningest", C_COMPUTE, font_size=FS)
box("raw", 680, 360, 200, "S3 raw\njsonl.gz · 90 j", C_STORE, font_size=FS)
box("emr", 950, 345, 400, "EMR Serverless (PySpark)\nnormalize · validate · publish", C_COMPUTE, font_size=FS)
box("events", 1420, 360, 230, "Iceberg events\nGlue + Athena", C_ANALYTICS, font_size=FS)
box("quarantine", 950, 460, 190, "S3 quarantine\n(rejets)", C_STORE, font_size=14)
box("out", 1160, 460, 190, "S3 out\n_RUN.json", C_STORE, font_size=14)
note(1690, 360, 250, "SIREN · type d'annonce · date · tribunal · dirigeants\nsans doublon (MERGE)", 14, FONT_HAND)
note(1690, 175, 250, "Rejeu : make replay FROM TO\n(même jour 2× = même résultat)", 14, FONT_HAND)

# ---------- 2. Observabilité ----------
zone("z2", 40, 580, 1920, 200, "2 · Observabilité & coûts", bg="#e7f5ff", stroke="#1971c2")
box("runs", 80, 640, 300, "DynamoDB pipeline_runs\n1 ligne par exécution", C_OBS, font_size=FS)
box("cw", 450, 640, 340, "CloudWatch\nlogs · métriques · alarmes", C_OBS, font_size=FS)
box("sns", 860, 640, 230, "SNS\nalerts", C_OBS, font_size=FS)
box("email", 1160, 640, 230, "Email\n(toi)", C_HUMAN, font_size=FS)
box("budget", 1460, 640, 230, "Budget AWS\n30 € / mois", C_OBS, font_size=FS)

# ---------- 3. Agent ----------
zone("z3", 40, 820, 1920, 300, "3 · Agent — surveille, enquête, propose (jamais n'exécute seul)", bg="#fff9db", stroke="#e67700")
box("sqs", 80, 880, 230, "SQS\n1 alarme = 1 enquête", C_AGENT, font_size=FS)
box("agent", 380, 880, 340, "Agent · Lambda + Bedrock\nClaude, tool use, budget borné", C_AGENT, font_size=FS)
box("tools", 380, 1000, 340, "9 outils LECTURE SEULE\nruns · logs · EMR · Athena · S3 · Git", C_AGENT, font_size=14)
box("report", 80, 1000, 230, "Rapport 07:00\n+ hebdo", C_AGENT, font_size=14)
box("pending", 790, 880, 300, "Action proposée\n(pending_actions)", C_AGENT, font_size=FS)
box("human", 1160, 880, 300, "Validation humaine\nemail · Slack · CLI", C_HUMAN, font_size=FS)
box("exec", 1530, 880, 300, "Exécution\nreplay · pause · rollback", C_AGENT, font_size=FS)
note(790, 1000, 1040, "Traces JSONL (90 j) · évals avec juge IA · module Terraform installable dans un autre compte (S7)", 14, FONT_HAND)

# ---------- 4. Sécurité & IaC ----------
zone("z4", 40, 1160, 1920, 180, "4 · Sécurité & infra as code", bg="#fff5f5", stroke="#c92a2a")
box("tf", 80, 1220, 300, "Terraform · make up / down\nétat S3 + verrou", C_IAC, font_size=14)
box("kms", 400, 1220, 240, "KMS\ntous les buckets", C_SEC, font_size=14)
box("r1", 660, 1220, 300, "Rôle Lambda\nlit BODACC · écrit raw", C_SEC, font_size=14)
box("r2", 980, 1220, 300, "Rôle EMR\nlit raw · écrit processed, events", C_SEC, font_size=14)
box("r3", 1300, 1220, 300, "Rôle Step Functions\ninvoke Lambda · start EMR", C_SEC, font_size=14)
box("r4", 1620, 1220, 300, "Rôle agent\nlecture seule + actions listées", C_SEC, font_size=14)

# =====================================================================
# FLÈCHES (peu, courtes, 1-2 mots)
# =====================================================================
arrow("scheduler", "sfn", width=3)
arrow("sfn", "ingest", "1", label_w=30, width=3)
arrow("sfn", "emr", "2 · 3 · 4", label_w=70, width=3)
arrow("bodacc", "ingest", width=3)
arrow("ingest", "raw", width=3)
arrow("raw", "emr", width=3)
arrow("emr", "events", "MERGE", label_w=60, width=3)
arrow("emr", "quarantine")
arrow("emr", "out")

arrow("sfn", "runs", "notify", via=[(345, 320), (345, 600)], label_w=60, color="#1971c2")
arrow("emr", "cw", "logs + métriques", via=[(620, 560), (620, 620)], label_w=130, color="#1971c2")
arrow("sfn", "sns", "échec", via=[(1385, 320), (1385, 625), (975, 625)], label_w=50, color="#1971c2")
arrow("cw", "sns", "alarme", label_w=60, color="#1971c2")
arrow("budget", "email", "50 % · 90 %", label_w=90, color="#1971c2")
arrow("sns", "email", color="#1971c2")

arrow("sns", "sqs", "alarme", via=[(975, 800), (195, 800)], label_w=60, color="#e67700")
arrow("sqs", "agent", color="#e67700")
arrow("agent", "tools", "lit", label_w=30, color="#e67700")
arrow("agent", "report", color="#e67700")
arrow("report", "email", "07:00", via=[(50, 1030), (50, 560), (1275, 560)], label_w=50, color="#0ca678", dashed=True)
arrow("agent", "pending", "propose", label_w=70, color="#e67700")
arrow("pending", "human", "tu valides", label_w=90, color="#0ca678")
arrow("human", "exec", "OK", label_w=30, color="#0ca678")
arrow("exec", "sfn", "replay_day", via=[(1900, 920), (1900, 100), (760, 100)], label_w=90, color="#0ca678")
arrow("tools", "z1", "lecture seule", via=[(1980, 1040), (1980, 330)], label_w=100, color="#e67700", dashed=True)

# =====================================================================
# SORTIE
# =====================================================================
scene = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"gridSize": 20, "viewBackgroundColor": "#ffffff"},
    "files": {},
}
out = Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(scene, ensure_ascii=False, indent=1))

# ---------- aperçu SVG (approximatif : rectangles, textes, flèches) ----------
svg_path = Path(sys.argv[2])
def _extent(e):
    if e["type"] == "arrow":
        xs = [e["x"] + p[0] for p in e["points"]]
        ys = [e["y"] + p[1] for p in e["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    return e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"]
ext = [_extent(e) for e in elements]
minx = min(x[0] for x in ext) - 40
miny = min(x[1] for x in ext) - 40
maxx = max(x[2] for x in ext) + 40
maxy = max(x[3] for x in ext) + 40
parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx} {miny} {maxx - minx} {maxy - miny}" width="{maxx - minx:.0f}" height="{maxy - miny:.0f}" font-family="Helvetica, Arial, sans-serif"><rect x="{minx}" y="{miny}" width="{maxx - minx}" height="{maxy - miny}" fill="white"/>']
from xml.sax.saxutils import escape

for e in elements:
    if e["type"] == "rectangle":
        dash = ' stroke-dasharray="8 6"' if e["strokeStyle"] == "dashed" else ""
        parts.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["width"]}" height="{e["height"]}" rx="6" fill="{e["backgroundColor"] if e["backgroundColor"] != "transparent" else "none"}" stroke="{e["strokeColor"]}" stroke-width="{e["strokeWidth"]}"{dash}/>')
for e in elements:
    if e["type"] == "arrow":
        pts = " ".join(f"{e['x'] + px},{e['y'] + py}" for px, py in e["points"])
        dash = ' stroke-dasharray="8 6"' if e["strokeStyle"] == "dashed" else ""
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{e["strokeColor"]}" stroke-width="{e["strokeWidth"]}"{dash}/>')
        (x1, y1), (x2, y2) = e["points"][-2], e["points"][-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        tx, ty = e["x"] + x2, e["y"] + y2
        a1 = (tx - 14 * math.cos(ang - 0.4), ty - 14 * math.sin(ang - 0.4))
        a2 = (tx - 14 * math.cos(ang + 0.4), ty - 14 * math.sin(ang + 0.4))
        parts.append(f'<polyline points="{a1[0]},{a1[1]} {tx},{ty} {a2[0]},{a2[1]}" fill="none" stroke="{e["strokeColor"]}" stroke-width="{e["strokeWidth"]}"/>')
for e in elements:
    if e["type"] == "text":
        fs = e["fontSize"]
        lines = e["text"].split("\n")
        anchor = {"left": "start", "center": "middle", "right": "end"}[e["textAlign"]]
        x = e["x"] + (e["width"] / 2 if anchor == "middle" else 0)
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x}" y="{e["y"] + fs * 1.25 * i + fs}" font-size="{fs}" text-anchor="{anchor}" fill="{e["strokeColor"]}"{" font-family=\"Menlo, monospace\"" if e["fontFamily"] == 3 else ""}>{escape(line)}</text>')
parts.append("</svg>")
svg_path.write_text("\n".join(parts))
print(f"elements={len(elements)} boxes={len(boxes)} bbox=({minx:.0f},{miny:.0f})-({maxx:.0f},{maxy:.0f})")
