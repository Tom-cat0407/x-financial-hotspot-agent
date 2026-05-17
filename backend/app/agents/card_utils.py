from __future__ import annotations

import html
import subprocess
from pathlib import Path
from typing import Any, Dict

from PIL import Image, ImageDraw, ImageFont

from backend.app.core.config import CARDS_DIR, ROOT_DIR


CARD_DIMENSIONS = {
    "16x9": (1600, 900),
    "1x1": (1080, 1080),
}


def _card_html(cluster: Dict[str, Any], score: Dict[str, Any], content: Dict[str, Any], aspect_ratio: str = "16x9") -> str:
    width, height = CARD_DIMENSIONS.get(aspect_ratio, CARD_DIMENSIONS["16x9"])
    is_square = aspect_ratio == "1x1"
    entities = ", ".join(cluster["entities"][:4]) or "Markets"
    title = html.escape(cluster["main_title"])
    tweet = html.escape(content["tweet_text"])
    breakdown = score.get("score_breakdown", {})
    chart_rows = _score_bars_html(breakdown)
    frame_padding = "46px 52px" if is_square else "58px 68px"
    title_size = "52px" if is_square else "70px"
    tweet_size = "26px" if is_square else "31px"
    grid_template = "1fr" if is_square else "1fr 560px"
    content_margin = "30px" if is_square else "44px"
    metric_padding = "20px" if is_square else "28px"
    metric_value = "38px" if is_square else "54px"
    chart_display = "block" if is_square else "block"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ margin: 0; width: {width}px; height: {height}px; font-family: Arial, 'Microsoft YaHei', sans-serif; background: #f8fafc; color: #0f172a; }}
    .frame {{ position: relative; width: {width}px; height: {height}px; padding: {frame_padding}; background: linear-gradient(135deg, #f8fafc 0%, #ecfeff 100%); }}
    .brand {{ display: flex; justify-content: space-between; align-items: center; color: #475569; font-size: {24 if is_square else 30}px; }}
    .logo {{ background: #0f766e; color: white; border-radius: 8px; padding: 14px 18px; font-weight: 800; }}
    h1 {{ margin: {36 if is_square else 58}px 0 24px; max-width: {width - 140}px; font-size: {title_size}; line-height: 1.05; letter-spacing: 0; }}
    .tweet {{ max-width: {width - 140}px; color: #334155; font-size: {tweet_size}; line-height: 1.34; }}
    .content-grid {{ display: grid; grid-template-columns: {grid_template}; gap: 24px; margin-top: {content_margin}; align-items: stretch; }}
    .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .metric {{ background: rgba(255,255,255,.84); border: 1px solid #cbd5e1; border-radius: 8px; padding: {metric_padding}; }}
    .metric span {{ display: block; color: #64748b; font-size: {20 if is_square else 24}px; }}
    .metric strong {{ display: block; margin-top: 10px; color: #0f766e; font-size: {metric_value}; }}
    .metric.wide {{ grid-column: 1 / -1; }}
    .chart {{ display: {chart_display}; background: rgba(255,255,255,.88); border: 1px solid #cbd5e1; border-radius: 8px; padding: 22px; }}
    .chart h2 {{ margin: 0 0 18px; color: #0f172a; font-size: 28px; }}
    .bar-row {{ display: grid; grid-template-columns: 178px 1fr 54px; gap: 14px; align-items: center; margin: 12px 0; }}
    .bar-row span {{ color: #475569; font-size: 20px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bar-track {{ height: 18px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 18px; background: linear-gradient(90deg, #0f766e, #14b8a6); border-radius: 999px; }}
    .bar-value {{ color: #0f766e; font-size: 20px; font-weight: 800; text-align: right; }}
    .foot {{ position: absolute; left: {52 if is_square else 72}px; bottom: {30 if is_square else 38}px; color: #64748b; font-size: {20 if is_square else 24}px; }}
  </style>
</head>
<body>
  <div class="frame">
    <div class="brand"><div class="logo">X Financial Agent</div><div>{html.escape(cluster["event_type"])}</div></div>
    <h1>{title}</h1>
    <div class="tweet">{tweet}</div>
    <div class="content-grid">
      <div class="metrics">
        <div class="metric"><span>Hot Score</span><strong>{score["hot_score"]}</strong></div>
        <div class="metric"><span>Sources</span><strong>{cluster["source_count"]}</strong></div>
        <div class="metric"><span>Confidence</span><strong>{cluster.get("confidence_score", 0)}</strong></div>
        <div class="metric"><span>Priority</span><strong>{html.escape(cluster.get("emergency", {}).get("emergency_level", "low"))}</strong></div>
        <div class="metric wide"><span>Entities</span><strong>{html.escape(entities)}</strong></div>
      </div>
      <div class="chart">
        <h2>HotScore Factors</h2>
        {chart_rows}
      </div>
    </div>
    <div class="foot">Not investment advice. Mock X/API demo data for assessment.</div>
  </div>
</body>
</html>"""


def _score_bars_html(breakdown: Dict[str, Any]) -> str:
    if not breakdown:
        return '<div class="bar-row"><span>No factor data</span><div class="bar-track"><div class="bar-fill" style="width:0%"></div></div><b class="bar-value">0</b></div>'
    top_items = sorted(breakdown.items(), key=lambda item: float(item[1] or 0), reverse=True)[:7]
    max_value = max(float(value or 0) for _, value in top_items) or 1
    rows = []
    for name, value in top_items:
        numeric = float(value or 0)
        width = max(4, min(100, numeric / max_value * 100))
        rows.append(
            f'<div class="bar-row"><span>{html.escape(str(name))}</span><div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div><b class="bar-value">{numeric:g}</b></div>'
        )
    return "".join(rows)


def _render_html_card(html_path: Path, png_path: Path, aspect_ratio: str = "16x9") -> bool:
    script = ROOT_DIR / "scripts" / "render_card.mjs"
    if not script.exists():
        return False
    width, height = CARD_DIMENSIONS.get(aspect_ratio, CARD_DIMENSIONS["16x9"])
    try:
        subprocess.run(
            ["node", str(script), str(html_path), str(png_path), str(width), str(height)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return png_path.exists()
    except Exception:
        return False


def _render_pillow_card(cluster: Dict[str, Any], score: Dict[str, Any], content: Dict[str, Any], path: Path, aspect_ratio: str = "16x9") -> None:
    width, height = CARD_DIMENSIONS.get(aspect_ratio, CARD_DIMENSIONS["16x9"])
    is_square = aspect_ratio == "1x1"
    image = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(image)
    title_font = _font(44 if is_square else 68)
    body_font = _font(30 if is_square else 38)
    small_font = _font(23 if is_square else 28)
    header_h = 96 if is_square else 120
    margin = 52 if is_square else 70
    draw.rectangle((0, 0, width, header_h), fill=(15, 118, 110))
    draw.text((margin, 30 if is_square else 38), "X Financial Hotspot Agent", fill=(255, 255, 255), font=body_font)

    if is_square:
        draw.text((margin, 132), _wrap(cluster["main_title"], 30), fill=(15, 23, 42), font=title_font, spacing=10)
        draw.text((margin, 348), _wrap(content["tweet_text"], 58), fill=(51, 65, 85), font=small_font, spacing=8)
        metric_y, metric_h, gap = 570, 120, 26
        card_w = (width - margin * 2 - gap * 2) // 3
        metric_boxes = [
            (margin, metric_y, margin + card_w, metric_y + metric_h, "Hot Score", str(score["hot_score"]), (204, 251, 241), (15, 118, 110)),
            (margin + card_w + gap, metric_y, margin + card_w * 2 + gap, metric_y + metric_h, "Sources", str(cluster["source_count"]), (220, 252, 231), (6, 95, 70)),
            (margin + (card_w + gap) * 2, metric_y, width - margin, metric_y + metric_h, "Priority", cluster.get("emergency", {}).get("emergency_level", "low"), (254, 249, 195), (133, 77, 14)),
        ]
        for left, top, right, bottom, label, value, fill, color in metric_boxes:
            draw.rounded_rectangle((left, top, right, bottom), radius=8, fill=fill)
            draw.text((left + 24, top + 22), label, fill=color, font=small_font)
            draw.text((left + 24, top + 62), value, fill=color, font=body_font)
        draw.rounded_rectangle((margin, 720, width - margin, 812), radius=8, fill=(255, 247, 237))
        draw.text((margin + 24, 742), "Entities", fill=(154, 52, 18), font=small_font)
        draw.text((margin + 160, 742), _wrap(", ".join(cluster["entities"][:4]) or "Markets", 44), fill=(124, 45, 18), font=small_font)
        chart_x, chart_y = margin, 842
        bar_name_w, bar_w = 230, width - margin * 2 - 330
        footer_y = height - 46
    else:
        draw.text((margin, 190), _wrap(cluster["main_title"], 35), fill=(15, 23, 42), font=title_font, spacing=12)
        draw.text((margin, 430), _wrap(content["tweet_text"], 70), fill=(51, 65, 85), font=small_font, spacing=10)
        draw.rounded_rectangle((70, 620, 470, 760), radius=8, fill=(204, 251, 241))
        draw.text((105, 645), "Hot Score", fill=(15, 118, 110), font=body_font)
        draw.text((105, 695), str(score["hot_score"]), fill=(17, 94, 89), font=title_font)
        draw.rounded_rectangle((520, 620, 920, 760), radius=8, fill=(220, 252, 231))
        draw.text((555, 645), "Sources", fill=(6, 95, 70), font=body_font)
        draw.text((555, 695), str(cluster["source_count"]), fill=(6, 78, 59), font=title_font)
        draw.rounded_rectangle((970, 620, 1530, 760), radius=8, fill=(254, 249, 195))
        draw.text((1005, 645), "Entities", fill=(133, 77, 14), font=body_font)
        draw.text((1005, 705), ", ".join(cluster["entities"][:4]) or "Markets", fill=(113, 63, 18), font=small_font)
        chart_x, chart_y = 970, 455
        bar_name_w, bar_w = 250, 300
        footer_y = 820

    breakdown = score.get("score_breakdown", {})
    draw.text((chart_x, chart_y), "HotScore Factors", fill=(15, 23, 42), font=small_font)
    top_items = sorted(breakdown.items(), key=lambda item: float(item[1] or 0), reverse=True)[:4]
    max_value = max([float(value or 0) for _, value in top_items] or [1])
    for index, (name, value) in enumerate(top_items):
        y = chart_y + 45 + index * 38
        fill_width = int((float(value or 0) / max_value) * bar_w) if max_value else 0
        draw.text((chart_x, y), str(name)[:20], fill=(71, 85, 105), font=small_font)
        draw.rounded_rectangle((chart_x + bar_name_w, y + 4, chart_x + bar_name_w + bar_w, y + 22), radius=9, fill=(226, 232, 240))
        draw.rounded_rectangle((chart_x + bar_name_w, y + 4, chart_x + bar_name_w + fill_width, y + 22), radius=9, fill=(20, 184, 166))
    draw.text((margin, footer_y), "Not investment advice. Mock X/API demo data for assessment.", fill=(71, 85, 105), font=small_font)
    image.save(path)


def _wrap(text: str, max_chars: int) -> str:
    words = text.split()
    lines = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return "\n".join(lines[:4])


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()
