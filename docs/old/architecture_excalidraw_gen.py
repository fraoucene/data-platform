#!/usr/bin/env python3
"""Génère docs/architecture.excalidraw (scène Excalidraw) + un aperçu SVG.

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
# LAYOUT
# =====================================================================

# ---------- Titre ----------
elements.append(text_el(40, 10, 1400, "data-platform — architecture cible (S1 → S7)", 36, FONT_HAND, align="left", valign="top"))
note(40, 62, 2400, "Plateforme data BODACC sur AWS (Python, PySpark, Terraform) + agent de surveillance / enquête (Bedrock). "
     "Couleurs : gris = externe · rose = orchestration · orange = compute · vert = S3 · violet = catalogue/requêtes · "
     "bleu = observabilité · rouge = IAM/KMS · mauve = IaC/CI · jaune = agent · turquoise = humains/front. "
     "Flèches pleines = données/appels · pointillées = déploiement ou lecture seule.", 14)

# ---------- Colonne gauche : hors AWS ----------
zone("z-ext", 40, 150, 520, 640, "Hors AWS — sources, code, poste dev", bg="#f1f3f5")
box("bodacc", 70, 200, 460, "API BODACC (data.gouv / OpenDataSoft)\nannonces quotidiennes JSON : créations, procédures collectives, radiations\npagination · filtres par date · limites de débit", C_EXT, font_size=14)
box("github", 70, 330, 460, "GitHub\nrepo data-platform (monorepo uv) · repo agent-platform (le produit)\nPR par ticket · lu par l'agent via git_log (API GitHub)", C_EXT, font_size=14)
box("ci", 70, 440, 460, "GitHub Actions (S3-07)\nlint ruff · pytest (Spark local) · terraform fmt/validate/plan sur PR\nbuild packages · deploy dev au merge main (apply avec approbation)\nauth AWS via OIDC (rôle dédié, pas de clé)", C_IAC, font_size=13)
box("dev", 70, 580, 460, "Poste dev\nuv workspace (packages/ lambdas/ jobs/ infra/ steps/ evals/)\nmake up · make down · make check · make replay · make package · make pin-sync\nprofil AWS CLI (SSO) · terraform ≥ 1.9 · Docker", C_IAC, font_size=13)

# ---------- Colonne gauche bas : humains / front ----------
zone("z-human", 40, 830, 520, 560, "Humains & front (validation)", bg="#f1f3f5")
box("email", 70, 880, 460, "Email (SES / SNS)\nrapport quotidien 07:00 · rapport hebdo lundi (Markdown + HTML)\nalertes budget & alarmes · lien d'approbation", C_HUMAN, font_size=13)
box("slack", 70, 990, 460, "Slack / Teams (S7-03)\nwebhook · message court : statut, cause, preuve, action proposée\nboutons Approuver / Refuser (Slack interactivity)", C_HUMAN, font_size=13)
box("cli", 70, 1100, 460, "CLI & page d'approbation (S4-06, S5-05)\nagent status --date … · agent approve <id> · make runs\npage minimale : actions proposées, contexte, preuves, commentaire", C_HUMAN, font_size=13)
box("mcp", 70, 1215, 460, "Claude Code ⇄ serveur MCP stdio (S4-07)\nexpose les outils de lecture (get_pipeline_runs, …) en local", C_HUMAN, font_size=13)
box("human", 70, 1300, 460, "Toi (opérateur) — seule autorité d'exécution des actions", C_HUMAN, font_size=14)

# ---------- Zone compte AWS dev ----------
AWS_X, AWS_Y, AWS_W, AWS_H = 620, 150, 1900, 1480
zone("z-aws", AWS_X, AWS_Y, AWS_W, AWS_H, "Compte AWS dev — data-platform · région eu-west-3 (Paris) · tout tagué project=data-platform, environment=dev", bg="#fffdf5", stroke="#e67700")

# Ligne 1 : orchestration
zone("z-orch", 650, 200, 1840, 230, "Orchestration (S1-08, S2-06)", bg="#fff0f6", stroke="#c2255c")
box("scheduler", 680, 250, 280, "EventBridge Scheduler\n06:30 Europe/Paris → daily-pipeline\n07:00 → agent_daily", C_ORCH, font_size=14)
box("sfn", 1050, 245, 1100, "Step Functions · state machine daily-pipeline\ningest (Lambda) → wait manifest (Lambda) → normalize (EMR) → validate (EMR) → publish (EMR) → notify (Lambda)\nRetry 3× backoff · Catch → SNS alerts · définition Terraform templatefile()", C_ORCH, font_size=14)
box("sns-alerts", 2180, 250, 280, "SNS data-platform-alerts\nabonnements : email, SQS agent", C_OBS, font_size=14)
note(1050, 372, 1100, "Rejeu : make replay FROM=… TO=… lance une exécution par jour (S1-08, S2-08). Idempotent : même date = mêmes fichiers, MERGE sans doublon.", 12)

# Ligne 2 : compute
zone("z-compute", 650, 450, 1840, 300, "Compute (S1-07, S2-04, S2-05, S3-02)", bg="#fff4e6", stroke="#e8590c")
box("l-util", 680, 500, 300, "Lambdas wait_manifest · notify\nlisent _MANIFEST, écrivent pipeline_runs (DynamoDB), coût EMR via GetJobRun", C_COMPUTE, font_size=12)
box("l-ingest", 680, 590, 360, "Lambda ingest_bodacc (uv + layer / image)\ndate (défaut J-1) → client BODACC (httpx, pagination, retries, timeout)\nécrit raw/bodacc/date=YYYY-MM-DD/part-0001.jsonl.gz + _MANIFEST.json\nrôle : data-platform-dev-lambda", C_COMPUTE, font_size=12)
box("emr", 1090, 500, 760, "EMR Serverless · application Spark 3.5 · auto-stop 5 min · capacité max bornée\njob normalize : raw/jour → events_staging (Iceberg)\njob validate : règles platform-validation → processed/quarantine/date=… · bloque si rejets > 1 %\njob publish : MERGE INTO events USING events_staging (upsert source_id) → vide staging · _RUN.json → out\nrôle d'exécution : data-platform-dev-emr · logs + métriques EMF → CloudWatch", C_COMPUTE, font_size=13)
box("steps", 1900, 500, 560, "steps/*.json (normalize, validate, publish)\nentrée, sortie, version du package (pin), args spark-submit\nmake package JOB=… → archive uv → s3://artifacts/ · make pin-sync met à jour pyproject + steps", C_COMPUTE, font_size=13)
note(1090, 668, 760, "Métriques EMF émises par lambdas et jobs : rows_in, rows_out, rejects, duration_s, emr_cost_usd (S3-04).", 12)

# Ligne 3 : stockage + catalogue
zone("z-store", 650, 770, 1200, 300, "Stockage S3 (S1-04) — chiffrement KMS (bucket key), versioning, accès public bloqué", bg="#ebfbee", stroke="#2b8a3e")
box("s3-raw", 760, 820, 145, "S3 raw\nbodacc/date=…/*.jsonl.gz + _MANIFEST\nlifecycle 90 j", C_STORE, font_size=11)
box("s3-processed", 930, 820, 130, "S3 processed\nquarantine/date=… (rejets + raison)", C_STORE, font_size=11)
box("s3-out", 1095, 820, 140, "S3 out\n_RUN.json (compteurs insérés / mis à jour)", C_STORE, font_size=11)
box("s3-artifacts", 1255, 820, 140, "S3 artifacts\narchives uv des jobs (versionnées)", C_STORE, font_size=11)
box("s3-logs", 1415, 820, 140, "S3 logs\naccess logs S3 · expiration 30 j", C_STORE, font_size=11)
box("kms", 1580, 820, 220, "KMS alias/data-platform-dev\nchiffre les 5 buckets (bucket key) · rotation annuelle · suppression différée 7 j", C_SEC, font_size=11)
box("s3-tfstate", 760, 960, 470, "S3 tfstate (bootstrap, état local séparé)\ndev/terraform.tfstate · versionné · AES256 · verrou (DynamoDB ou use_lockfile)", C_SEC, font_size=12)
box("s3-warehouse", 1255, 960, 545, "S3 warehouse (S2-03)\ndonnées + métadonnées des tables Iceberg events / events_staging", C_STORE, font_size=12)

zone("z-cat", 1870, 770, 620, 300, "Catalogue & requêtes (S2-03)", bg="#f3f0ff", stroke="#6741d9")
box("glue", 1900, 820, 270, "Glue Data Catalog · base platform\ntables Iceberg events (partition mois event_date) · events_staging", C_ANALYTICS, font_size=12)
box("athena", 2190, 820, 270, "Athena\nmigrations/iceberg/V001__create_events.sql (job rejouable)\nSELECT count(*) FROM platform.events", C_ANALYTICS, font_size=12)
box("events", 1900, 960, 560, "Table events (SIREN, type, date, tribunal, dirigeants, source_id) — livrable S2 · lue par l'agent via query_athena (lecture seule, 1 000 lignes, 30 s)", C_ANALYTICS, font_size=12)

# Ligne 4 : observabilité
zone("z-obs", 650, 1090, 1840, 230, "Observabilité & garde-fous de coût (S1-02, S2-07, S3-04)", bg="#e7f5ff", stroke="#1971c2")
box("cw-logs", 680, 1140, 300, "CloudWatch Logs\nlambdas · EMR (stderr/stdout) · Logs Insights", C_OBS, font_size=12)
box("ddb-runs", 1000, 1140, 340, "DynamoDB pipeline_runs (clé run_date)\nstatut par étape, durées, compteurs, coût EMR estimé", C_OBS, font_size=12)
box("cw-metrics", 1360, 1140, 330, "CloudWatch Metrics (EMF) + Dashboard 6 graphes\nrows_in · rows_out · rejects · duration_s · emr_cost_usd", C_OBS, font_size=12)
box("alarms", 1710, 1140, 380, "Alarmes CloudWatch\néchec pipeline · rejets > 1 % · durée > 2× médiane · coût/jour > 2 € · échec Lambda ingest", C_OBS, font_size=12)
box("budget", 2110, 1140, 350, "AWS Budgets data-platform-monthly\nCOST mensuel ~30 € · ACTUAL 50 % / 90 % → SNS budget-alerts → email", C_OBS, font_size=12)
note(680, 1248, 1780, "Chaque exécution laisse une ligne complète dans pipeline_runs (make runs l'affiche). Chaque alarme est testée une fois. Les alarmes publient sur SNS → humains ET agent (S5-02).", 12)

# Ligne 5 : IAM + Terraform
zone("z-iam", 650, 1340, 1840, 270, "IAM — un rôle par service, moindre privilège, aucun « * » sur Resource (S1-04, S7-05)", bg="#fff5f5", stroke="#c92a2a")
box("r-lambda", 680, 1390, 440, "data-platform-dev-lambda (trust lambda.amazonaws.com)\n• logs:CreateLogStream/PutLogEvents (AWSLambdaBasicExecutionRole)\n• s3:ListBucket raw · s3:GetObject/PutObject raw/bodacc/*\n• dynamodb:PutItem/UpdateItem pipeline_runs · emr-serverless:GetJobRun\n• kms:Encrypt/Decrypt/GenerateDataKey sur la clé · cloudwatch:PutMetricData", C_SEC, font_size=11, font=FONT_NORMAL, align="left")
box("r-emr", 1140, 1390, 440, "data-platform-dev-emr (trust emr-serverless.amazonaws.com)\n• s3:GetObject raw/*, artifacts/* · s3:ListBucket (5 buckets)\n• s3:PutObject/DeleteObject processed/*, out/*, warehouse/*, logs/*\n• glue:Get*/CreateTable/UpdateTable/BatchCreatePartition sur db platform\n• kms data-key sur la clé · logs:* vers le log group EMR", C_SEC, font_size=11, font=FONT_NORMAL, align="left")
box("r-sfn", 1600, 1390, 430, "data-platform-dev-sfn (trust states.amazonaws.com)\n• lambda:InvokeFunction arn:…:function:data-platform-dev-*\n• emr-serverless:StartJobRun/GetJobRun/CancelJobRun sur l'application\n• iam:PassRole data-platform-dev-emr (condition PassedToService)\n• sns:Publish data-platform-alerts · xray/logs pour les traces", C_SEC, font_size=11, font=FONT_NORMAL, align="left")
box("r-misc", 2050, 1390, 410, "Rôles annexes\n• scheduler : states:StartExecution daily-pipeline · lambda:InvokeFunction agent_daily\n• github-oidc (CI) : terraform plan/apply dev, s3:PutObject artifacts/* — trust token.actions.githubusercontent.com, repo:fraoucene/data-platform:*\n• terraform (poste dev) : profil SSO admin dev", C_SEC, font_size=11, font=FONT_NORMAL, align="left")

# ---------- Colonne droite : agent ----------
AG_X = 2580
L, R, W = AG_X + 30, AG_X + 490, 420
zone("z-agent", AG_X, 150, 940, 1480, "Agent — repo agent-platform · module Terraform réutilisable (S4 → S7)", bg="#fff9db", stroke="#e67700")
box("a-sqs", L, 200, W, "SQS agent-investigations (dédup)\nreçoit SNS alarmes avec contexte (alarme, heure, run) · 2 alarmes liées = 1 enquête", C_AGENT, font_size=13)
box("a-daily", R, 200, W, "Lambda agent_daily (conteneur) · 07:00 après le pipeline\nagent status --date J-1 → rapport S3 agent/reports/ + email SES\nhebdo le lundi : tendances coût / durée / rejets (S7-04)", C_AGENT, font_size=13)
box("a-invest", L, 320, W, "Lambda agent_investigate (S5)\nstratégie d'enquête sur 10 pannes cataloguées · idempotent (même alarme = même run_id)\ncircuit breaker si Bedrock indisponible → rapport « alarmes brutes »", C_AGENT, font_size=13)
box("bedrock", R, 320, W, "Amazon Bedrock · Claude (Paris ou Francfort)\nConverse API + tool use · budget par run : 15 appels d'outils, 60 s, 50 k tokens\nmodèles Pydantic · schéma de sortie structuré (S4-04) · coût tagué (Cost Explorer)", C_AGENT, font_size=13)
box("a-tools", L, 470, 880, "agent/tools/ — LECTURE SEULE (S4-03) · schéma JSON + docstring · résultats tronqués\nget_pipeline_runs(days) → DynamoDB · get_step_function_execution(id) → historique SFN · get_lambda_logs(name, since, filter) → Logs Insights\nget_emr_job(run_id) → statut/stderr · query_athena(sql) → lecture seule, 1 000 lignes, 30 s · get_metrics(name, period) → CloudWatch\nget_quarantine_sample(date, n) → S3 processed · get_raw_manifest(date) → S3 raw · git_log(repo, since) → API GitHub\nDécouverte par agent.yaml + tag monitored-by=agent (S7-01) : aucun nom de ressource en dur", C_AGENT, font_size=12, font=FONT_NORMAL, align="left")
box("a-actions", L, 640, W, "agent/actions/ — PROPOSÉES, jamais exécutées directement (S5-04)\nreplay_day(date) · rollback_package(job, version) · pause_schedule() · resume_schedule() · open_github_issue(title, body)\ntest : l'agent n'appelle jamais une action en direct", C_AGENT, font_size=12, font=FONT_NORMAL, align="left")
box("a-pending", R, 640, W, "DynamoDB pending_actions\naction proposée + contexte + preuves + lien d'approbation · statut approuvé / refusé + commentaire · résultat tracé", C_AGENT, font_size=12)
box("a-traces", L, 770, W, "S3 agent-traces (JSONL, 90 j) + agent/reports/\ntrace complète : prompts, outils appelés, coût, latence (S4-05)", C_AGENT, font_size=12)
box("a-exec", R, 770, W, "Exécuteur (après approbation uniquement)\nreplay_day → states:StartExecution daily-pipeline · pause/resume → scheduler:UpdateSchedule\nrollback → PR de pin · issue → GitHub", C_AGENT, font_size=12)
box("a-notif", L, 900, W, "Notifications (S7-03) : Slack (webhook + interactivity), Teams (webhook), email SES\naucune donnée personnelle dans les messages (S7-05)", C_AGENT, font_size=12)
box("a-evals", R, 900, W, "evals/ (S6) : harnais data-driven · suites « diagnostic » et « trajectoire » · juge IA · comparaisons · CI des évals · score dans le README", C_AGENT, font_size=12)
box("r-agent", L, 990, 880, "Rôle IAM agent (module Terraform S7-02) — lecture seule + actions explicitement listées, revue : aucun « * » sur Resource\n• bedrock:InvokeModel, InvokeModelWithResponseStream sur l'ARN du modèle uniquement\n• dynamodb:Query/GetItem pipeline_runs · dynamodb:PutItem/UpdateItem/Query pending_actions\n• states:DescribeExecution/GetExecutionHistory/ListExecutions daily-pipeline · states:StartExecution (exécuteur seulement)\n• logs:StartQuery/GetQueryResults/FilterLogEvents sur les log groups surveillés · emr-serverless:GetJobRun/ListJobRuns\n• athena:StartQueryExecution/GetQueryExecution/GetQueryResults (workgroup agent, lecture) · glue:GetTable/GetDatabase · s3 résultats Athena\n• cloudwatch:GetMetricData/DescribeAlarms · s3:GetObject processed/quarantine/*, raw/*/_MANIFEST.json · s3:PutObject agent-traces/*, agent/reports/*\n• sqs:ReceiveMessage/DeleteMessage · ses:SendEmail (identité vérifiée) · scheduler:UpdateSchedule (exécuteur) · kms:Decrypt sur la clé data", C_SEC, font_size=11, font=FONT_NORMAL, align="left")
box("acct2", L, 1200, 880, "Compte AWS n° 2 ou région n° 2 (S7-02, S7-06)\nterraform apply examples/minimal → agent installé en < 10 min · variables : pipelines à surveiller, canal de notification, budget · alarme coût dédiée", C_IAC, font_size=13)
note(L, 1300, 880, "Durcissement S7-05 : idempotence des enquêtes, timeouts, circuit breaker Bedrock, rotation des traces 90 j, aucune donnée personnelle. Livrables : S4 email « état du pipeline », S5 diagnostic de 10 pannes, S6 score d'évals, S7 apply dans un compte vierge, S8 vidéo + article + offre.", 12)

# =====================================================================
# FLÈCHES (couloirs : y=142 au-dessus d'AWS · y=440 entre orch/compute · y=760 entre compute/S3 ·
#          y=1080 entre S3/obs · y=1330 entre obs/IAM · x=700 et x=1075 verticaux · x=2535..2567 entre AWS et agent ·
#          y=1650/1690 sous les zones)
# =====================================================================
# Externe → ingestion
arrow("bodacc", "l-ingest", via=[(600, 285), (600, 640)])
# Orchestration
arrow("scheduler", "sfn", "06:30", label_w=50)
arrow("sfn", "l-util", via=[(860, 440)])
arrow("sfn", "l-ingest", "ingest", via=[(1010, 440), (1010, 575)], label_w=55)
arrow("sfn", "emr", "StartJobRun normalize → validate → publish (PassRole emr)", label_w=300)
arrow("sfn", "sns-alerts")
# Ingestion → stockage
arrow("l-ingest", "s3-raw", "jsonl.gz + _MANIFEST", label_w=110)
arrow("s3-raw", "emr", via=[(1000, 775)])
# EMR ↔ stockage / catalogue
arrow("emr", "s3-processed")
arrow("emr", "s3-out")
arrow("s3-artifacts", "emr")
arrow("steps", "emr", "args spark-submit, pin package", label_w=120)
arrow("emr", "s3-warehouse", via=[(1405, 700), (1405, 945)])
arrow("emr", "glue", "MERGE INTO events", via=[(1870, 700)], label_w=100)
arrow("glue", "s3-warehouse", "métadonnées Iceberg → données", color="#6741d9", label_w=130)
arrow("athena", "glue", "SQL", color="#6741d9", label_w=40)
arrow("kms", "s3-logs", color="#c92a2a", dashed=True)
# Observabilité
arrow("l-ingest", "cw-logs", "logs + EMF", via=[(700, 760), (700, 1120)], color="#1971c2", label_w=80)
arrow("emr", "cw-metrics", "EMF", via=[(1075, 640), (1075, 1125)], color="#1971c2", label_w=40)
arrow("cw-metrics", "alarms", color="#1971c2")
arrow("alarms", "sns-alerts", "ALARM", via=[(2500, 1170), (2500, 420)], color="#1971c2", label_w=60)
arrow("budget", "email", via=[(2290, 1330), (610, 1330), (610, 930)], color="#1971c2", dashed=True)
# Terraform / CI
arrow("dev", "s3-tfstate", via=[(610, 790), (917, 790), (917, 950)], color="#9c36b5", dashed=True)
arrow("ci", "s3-tfstate", "CI : plan sur PR, apply au merge", via=[(590, 440), (640, 440), (640, 940)], color="#9c36b5", dashed=True, label_w=190)
arrow("dev", "s3-artifacts", "make package → push", via=[(600, 760), (1325, 760)], color="#9c36b5", dashed=True, label_w=120)
# Agent
arrow("scheduler", "a-daily", "07:00 agent_daily", via=[(635, 300), (635, 142), (3280, 142)], color="#e67700", label_w=135)
arrow("sns-alerts", "a-sqs", "alarmes + contexte", color="#e67700", label_w=100)
arrow("a-sqs", "a-invest", "1 enquête par panne", color="#e67700", label_w=150)
arrow("a-daily", "bedrock", color="#e67700")
arrow("a-invest", "bedrock", color="#e67700")
arrow("bedrock", "a-tools", "max 15 appels d'outils", color="#e67700", label_w=175)
arrow("a-tools", "z-aws", "lecture seule", color="#e67700", dashed=True, label_w=70)
arrow("a-invest", "a-actions", "propose", via=[(2592, 380), (2592, 690)], color="#e67700", label_w=58)
arrow("a-actions", "a-pending", "écrit", color="#e67700", label_w=40)
arrow("a-pending", "a-exec", "approuvé", color="#e67700", label_w=60)
arrow("a-exec", "sfn", "replay_day → StartExecution", via=[(3280, 862), (2535, 862), (2535, 440), (1700, 440)], color="#e67700", label_w=140)
arrow("a-notif", "email", via=[(2567, 920), (2567, 1076), (600, 1076), (600, 905)], color="#0ca678")
arrow("a-notif", "slack", "Slack / Teams / SES", via=[(2563, 935), (2563, 1086), (590, 1086), (590, 1040)], color="#0ca678", label_w=140)
arrow("human", "a-pending", "agent approve <id> / bouton Slack", via=[(300, 1650), (3530, 1650), (3530, 680)], color="#0ca678", label_w=180)
arrow("mcp", "a-tools", "MCP stdio (local)", via=[(590, 1240), (590, 1690), (3545, 1690), (3545, 540)], color="#0ca678", dashed=True, label_w=100)

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
