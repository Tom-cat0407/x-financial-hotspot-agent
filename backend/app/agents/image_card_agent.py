from __future__ import annotations

from typing import Any, Dict

from backend.app.agents.card_utils import CARDS_DIR, CARD_DIMENSIONS, _card_html, _render_html_card, _render_pillow_card


def generate_image_card(cluster: Dict[str, Any], score: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    variant = f"_{content['variant_name'].lower()}" if content.get("variant_name") else ""
    rendered_cards = []
    for aspect_ratio in ("16x9", "1x1"):
        width, height = CARD_DIMENSIONS[aspect_ratio]
        html_path = CARDS_DIR / f"{cluster['cluster_id']}_{content.get('language', 'en')}{variant}_{aspect_ratio}.html"
        png_path = CARDS_DIR / f"{cluster['cluster_id']}_{content.get('language', 'en')}{variant}_{aspect_ratio}.png"
        html_path.write_text(_card_html(cluster, score, content, aspect_ratio=aspect_ratio), encoding="utf-8")
        rendered = _render_html_card(html_path, png_path, aspect_ratio=aspect_ratio)
        if not rendered:
            _render_pillow_card(cluster, score, content, png_path, aspect_ratio=aspect_ratio)
        rendered_cards.append(
            {
                "aspect_ratio": aspect_ratio,
                "card_path": str(png_path),
                "html_template_path": str(html_path),
                "size": f"{width}x{height}",
                "renderer": "playwright" if rendered else "pillow_fallback",
            }
        )
    primary = rendered_cards[0]
    return {
        "content_id": content["content_id"],
        "cluster_id": cluster["cluster_id"],
        "card_path": primary["card_path"],
        "html_template_path": primary["html_template_path"],
        "size": primary["size"],
        "aspect_ratio": primary["aspect_ratio"],
        "renderer": primary["renderer"],
        "alternate_cards": rendered_cards[1:],
    }

__all__ = ["generate_image_card"]
