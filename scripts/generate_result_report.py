from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "outputs" / "state.json"
DEFAULT_OUTPUT = ROOT / "outputs" / "submission_report.html"


CORE_CHECKS = [
    ("数据采集", "KOL、财经媒体、关键词与趋势话题采集，保留原始数据依据。", "raw_posts"),
    ("热点筛选", "同事件聚类，输出 Top N、热度分数与 score_breakdown。", "hot_scores"),
    ("关键词与 Hashtag", "实体抽取、Trending Topics 融合、3-5 个中英文 Hashtag。", "generated_contents"),
    ("内容生成", "DeepSeek/规则兜底生成原创推文，满足 280 字符、核心信息、Hashtag 与免责声明。", "generated_contents"),
    ("配图生成", "HTML/CSS 动态卡片模板生成 16:9 图片，包含标题、数据指标与品牌标识。", "image_cards"),
    ("审核与发布", "合规审核、人工审核队列、Mock X 发布链接、失败与频率控制。", "publish_records"),
]

BONUS_CHECKS = [
    ("Agent 框架", "10 个独立 Agent 模块、状态机编排、agent_manifest.yaml。", "event_clusters"),
    ("反馈闭环", "发布后回收互动指标，更新 style/source/hashtag 策略权重。", "performance_metrics"),
    ("多平台分发", "Telegram Bot API 适配器 + Threads mock 适配器。", "platform_dispatches"),
    ("A/B 测试", "A/B 变体分别发布、回收指标并标记 winner。", "ab_test_variants"),
    ("突发优先级", "重大金融事件触发 emergency boost 与人工审核。", "hot_scores"),
    ("RAG 事实校验", "MockFinanceDataClient，可选 CoinGecko/Yahoo Finance 外部事实源。", "fact_checks"),
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def h(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def state_items(state: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = state.get(key, [])
    return value if isinstance(value, list) else []


def count_for(state: dict[str, Any], key: str) -> int:
    return len(state_items(state, key))


def pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "0.00%"


def badge(ok: bool, text: str | None = None) -> str:
    label = text or ("已完成" if ok else "待补充")
    cls = "ok" if ok else "warn"
    return f'<span class="badge {cls}">{h(label)}</span>'


def metric_cards(state: dict[str, Any]) -> str:
    generated_by = Counter(item.get("generated_by", "unknown") for item in state_items(state, "generated_contents"))
    reviewed_by = Counter(item.get("reviewed_by", "unknown") for item in state_items(state, "compliance_reports"))
    metrics = [
        ("原始帖子", count_for(state, "raw_posts")),
        ("事件簇", count_for(state, "event_clusters")),
        ("热度分数", count_for(state, "hot_scores")),
        ("生成内容", count_for(state, "generated_contents")),
        ("LLM 文案", generated_by.get("llm", 0)),
        ("LLM 合规", reviewed_by.get("llm+rules", 0)),
        ("Mock 发布", count_for(state, "publish_records")),
        ("A/B 变体", count_for(state, "ab_test_variants")),
        ("反馈指标", count_for(state, "performance_metrics")),
        ("平台分发", count_for(state, "platform_dispatches")),
    ]
    return "".join(
        f"""
        <article class="metric">
          <strong>{h(value)}</strong>
          <span>{h(label)}</span>
        </article>
        """
        for label, value in metrics
    )


def checklist_section(title: str, rows: list[tuple[str, str, str]], state: dict[str, Any]) -> str:
    body = []
    for name, desc, key in rows:
        count = count_for(state, key)
        body.append(
            f"""
            <article class="check-card">
              <div>
                <h3>{h(name)}</h3>
                <p>{h(desc)}</p>
              </div>
              <div class="check-right">
                {badge(count > 0)}
                <span class="count">{h(count)} 条证据</span>
              </div>
            </article>
            """
        )
    return f"""
    <section id="{h(title)}" class="section">
      <div class="section-head">
        <p class="eyebrow">Assessment Mapping</p>
        <h2>{h(title)}</h2>
      </div>
      <div class="check-grid">{"".join(body)}</div>
    </section>
    """


def llm_section(state: dict[str, Any]) -> str:
    contents = state_items(state, "generated_contents")
    reports = state_items(state, "compliance_reports")
    generated_by = Counter(item.get("generated_by", "unknown") for item in contents)
    reviewed_by = Counter(item.get("reviewed_by", "unknown") for item in reports)
    errors = [item.get("llm_error") for item in contents + reports if item.get("llm_error")]
    error_rows = "".join(f"<li>{h(err)}</li>" for err in Counter(errors).elements())
    return f"""
    <section id="llm" class="section">
      <div class="section-head">
        <div>
          <p class="eyebrow">DeepSeek Evidence</p>
          <h2>LLM 调用结果</h2>
        </div>
      </div>
      <div class="two-col">
        <article class="mini-card">
          <h3>文案生成</h3>
          <ul>
            <li><span>DeepSeek 生成</span><b>{h(generated_by.get("llm", 0))}</b></li>
            <li><span>规则兜底</span><b>{h(generated_by.get("rules_fallback", 0))}</b></li>
          </ul>
        </article>
        <article class="mini-card">
          <h3>合规复核</h3>
          <ul>
            <li><span>LLM + 规则</span><b>{h(reviewed_by.get("llm+rules", 0))}</b></li>
            <li><span>纯规则</span><b>{h(reviewed_by.get("rules", 0))}</b></li>
          </ul>
        </article>
      </div>
      <div class="mini-card">
        <h3>LLM 错误</h3>
        <ul>{error_rows or "<li>本次运行未记录 LLM 错误。</li>"}</ul>
      </div>
    </section>
    """


def top_hotspots(state: dict[str, Any]) -> str:
    clusters = {cluster.get("cluster_id"): cluster for cluster in state_items(state, "event_clusters")}
    scores = sorted(state_items(state, "hot_scores"), key=lambda item: item.get("hot_score", 0), reverse=True)[:8]
    if not scores:
        return '<div class="empty">暂无热度评分，请先运行 Demo。</div>'
    rows = []
    for index, score in enumerate(scores, 1):
        cluster = clusters.get(score.get("cluster_id"), {})
        breakdown = score.get("score_breakdown", {})
        breakdown_html = "".join(f"<span><b>{h(key)}</b>{h(value)}</span>" for key, value in breakdown.items())
        entities = ", ".join(cluster.get("entities", [])[:8])
        rows.append(
            f"""
            <article class="hotspot">
              <div class="rank">#{index}</div>
              <div class="hotspot-main">
                <div class="hotspot-title">
                  <h3>{h(cluster.get("main_title") or score.get("cluster_id"))}</h3>
                  <strong>{h(score.get("hot_score", 0))}</strong>
                </div>
                <p>{h(cluster.get("summary", ""))}</p>
                <div class="chips">
                  <span>{h(cluster.get("event_type", "unknown"))}</span>
                  <span>{h(cluster.get("source_count", 0))} sources</span>
                  <span>{h(cluster.get("emergency", {}).get("emergency_level", "low"))} priority</span>
                </div>
                <div class="entities">{h(entities)}</div>
                <div class="breakdown">{breakdown_html}</div>
              </div>
            </article>
            """
        )
    return "".join(rows)


def content_section(state: dict[str, Any]) -> str:
    cards_by_content = {item.get("content_id"): item for item in state_items(state, "image_cards")}
    body = []
    for item in state_items(state, "generated_contents"):
        if item.get("language") not in {"en", "zh"}:
            continue
        card = cards_by_content.get(item.get("content_id"), {})
        card_path = Path(card.get("card_path", "")) if card.get("card_path") else None
        rel_card = ""
        if card_path and card_path.exists():
            rel_card = card_path.relative_to(DEFAULT_OUTPUT.parent).as_posix()
        body.append(
            f"""
            <article class="content-card">
              {f'<img src="{h(rel_card)}" alt="card" />' if rel_card else ''}
              <div>
                <div class="chips">
                  <span>{h(item.get("language"))}</span>
                  <span>{h(item.get("style"))}</span>
                  <span>{h(item.get("generated_by"))}</span>
                  {badge(not item.get("llm_error"), item.get("llm_error") or "ok")}
                </div>
                <p>{h(item.get("tweet_text", ""))}</p>
              </div>
            </article>
            """
        )
    return "".join(body) or '<div class="empty">暂无生成内容。</div>'


def publishing_section(state: dict[str, Any]) -> str:
    records = state_items(state, "publish_records")
    if not records:
        return '<div class="empty">暂无发布记录，请先运行完整 Demo。</div>'
    body = []
    for record in records[:8]:
        url = record.get("mock_post_url") or ""
        body.append(
            f"""
            <article class="publish">
              <div class="publish-top">
                <strong>{h(record.get("mock_post_id"))}</strong>
                {badge(bool(record.get("ok")), "published" if record.get("ok") else "failed")}
              </div>
              <p>{h(record.get("tweet_text", ""))}</p>
              <div class="chips">
                <span>{h(record.get("variant_name"))}</span>
                <span>{h(record.get("style"))}</span>
                <span>{h(record.get("content_id"))}</span>
              </div>
              {f'<a href="{h(url)}">打开 Mock 链接</a>' if url else ''}
            </article>
            """
        )
    return "".join(body)


def ab_section(state: dict[str, Any]) -> str:
    variants = state_items(state, "ab_test_variants")
    if not variants:
        return '<div class="empty">暂无 A/B 变体。</div>'
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for variant in variants:
        grouped[variant.get("experiment_id", "")].append(variant)
    blocks = []
    for experiment_id, group in grouped.items():
        rows = "".join(
            f"""
            <li>
              <span>{h(item.get("variant_name"))} / {h(item.get("style"))}</span>
              <b>{h(pct(item.get("engagement_rate", 0)))} {'winner' if item.get("is_winner") else ''}</b>
            </li>
            """
            for item in group
        )
        blocks.append(f"<article class='mini-card'><h3>{h(experiment_id)}</h3><ul>{rows}</ul></article>")
    return "".join(blocks)


def feedback_section(state: dict[str, Any]) -> str:
    memory = state.get("strategy_memory", {}) if isinstance(state.get("strategy_memory"), dict) else {}
    blocks = []
    for title, key in [("Style Weight", "style_weight"), ("Source Weight", "source_weight"), ("Hashtag Weight", "hashtag_weight")]:
        weights = memory.get(key, {}) if isinstance(memory.get(key), dict) else {}
        rows = "".join(
            f"<li><span>{h(name)}</span><b>{h(round(value, 4) if isinstance(value, float) else value)}</b></li>"
            for name, value in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:6]
        )
        blocks.append(f"<article class='mini-card'><h3>{h(title)}</h3><ul>{rows or '<li>暂无记录</li>'}</ul></article>")
    return f"<p class='muted'>已回收 {count_for(state, 'performance_metrics')} 条互动指标。</p><div class='mini-grid'>{''.join(blocks)}</div>"


def artifact_links() -> str:
    artifacts = [
        ("状态快照", "state.json"),
        ("卡片目录", "cards/"),
        ("合规报告目录", "reports/"),
        ("架构文档", "../docs/architecture.md"),
        ("Prompt 设计", "../docs/prompt_design.md"),
        ("Agent Manifest", "../backend/app/agents/agent_manifest.yaml"),
    ]
    return "".join(f"<a class='artifact' href='{h(path)}'><strong>{h(label)}</strong><span>{h(path)}</span></a>" for label, path in artifacts)


def render(state: dict[str, Any], source_path: Path) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    complete_publish = count_for(state, "publish_records") > 0
    title = "完整验收结果" if complete_publish else "待运行完整 Demo"
    note = (
        "本报告由 outputs/state.json 自动生成，覆盖测试题核心能力、扩展能力、发布证据、A/B 实验和反馈闭环。"
        if complete_publish
        else "当前 state.json 尚未包含完整发布证据，请先运行完整 Demo。"
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>X 平台金融热点系统验收报告</title>
  <style>
    :root {{
      --bg: #f7f4ef;
      --surface: #fffaf3;
      --ink: #1f2933;
      --muted: #657282;
      --line: #e7dccc;
      --accent: #0f766e;
      --accent-2: #b45309;
      --ok: #047857;
      --warn: #b45309;
      --shadow: 0 18px 40px rgba(31, 41, 51, .08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top left, #e4f7f3 0, transparent 32rem), var(--bg);
      color: var(--ink);
      font-family: Inter, "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
      line-height: 1.55;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    .shell {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 100vh; }}
    aside {{ background: #17202b; color: white; padding: 28px 22px; position: sticky; top: 0; height: 100vh; }}
    aside h1 {{ font-size: 20px; line-height: 1.2; margin: 0 0 8px; }}
    aside p {{ color: #b7c2cf; font-size: 13px; margin: 0 0 24px; }}
    nav {{ display: grid; gap: 8px; }}
    nav a {{ border-radius: 10px; color: #e5e7eb; padding: 10px 12px; }}
    nav a:hover {{ background: rgba(255,255,255,.08); }}
    main {{ padding: 34px; }}
    .hero {{
      background: linear-gradient(135deg, #0f766e 0%, #12343b 100%);
      border-radius: 22px;
      color: white;
      box-shadow: var(--shadow);
      padding: 36px;
      margin-bottom: 24px;
    }}
    .hero h2 {{ font-size: 34px; margin: 0 0 10px; max-width: 880px; }}
    .hero p {{ color: #d7fffa; margin: 0; max-width: 760px; }}
    .hero-meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
    .hero-meta span {{ background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.18); border-radius: 999px; padding: 7px 11px; font-size: 13px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 14px; margin-bottom: 24px; }}
    .metric, .section, .hotspot, .publish, .mini-card, .check-card, .content-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
    }}
    .metric {{ padding: 18px; }}
    .metric strong {{ display: block; color: var(--accent); font-size: 30px; line-height: 1; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .section {{ padding: 24px; margin-bottom: 24px; }}
    .section-head {{ align-items: end; display: flex; justify-content: space-between; gap: 20px; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--accent-2); font-size: 12px; font-weight: 800; letter-spacing: .08em; margin: 0 0 4px; text-transform: uppercase; }}
    h2 {{ font-size: 24px; margin: 0; }}
    h3 {{ margin: 0 0 8px; }}
    .check-grid, .two-col {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .check-card {{ align-items: center; display: flex; justify-content: space-between; gap: 14px; padding: 16px; box-shadow: none; }}
    .check-card p, .muted {{ color: var(--muted); margin: 0; }}
    .check-right {{ display: grid; gap: 8px; justify-items: end; min-width: 150px; }}
    .count {{ color: var(--muted); font-size: 12px; }}
    .badge {{ border-radius: 999px; font-size: 12px; font-weight: 800; padding: 5px 9px; white-space: nowrap; }}
    .badge.ok {{ background: #d1fae5; color: var(--ok); }}
    .badge.warn {{ background: #ffedd5; color: var(--warn); }}
    .hotspot {{ display: grid; grid-template-columns: 56px minmax(0, 1fr); gap: 16px; margin-bottom: 12px; padding: 16px; box-shadow: none; }}
    .rank {{ align-items: center; background: #e7f8f5; border-radius: 14px; color: var(--accent); display: flex; font-weight: 900; justify-content: center; }}
    .hotspot-title {{ align-items: center; display: flex; justify-content: space-between; gap: 14px; }}
    .hotspot-title strong {{ color: var(--accent); font-size: 28px; }}
    .hotspot p {{ color: var(--muted); }}
    .chips, .breakdown {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 10px; }}
    .chips span, .breakdown span {{ background: #f1f5f9; border-radius: 999px; color: #475569; font-size: 12px; padding: 5px 9px; }}
    .breakdown span {{ background: #fff7ed; color: #9a3412; }}
    .breakdown b {{ margin-right: 6px; }}
    .entities {{ color: var(--accent); font-size: 13px; font-weight: 700; margin-top: 8px; }}
    .publish, .mini-card {{ padding: 16px; box-shadow: none; margin-bottom: 12px; }}
    .publish-top {{ align-items: center; display: flex; justify-content: space-between; gap: 10px; }}
    .mini-grid, .artifacts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .mini-card ul {{ list-style: none; margin: 0; padding: 0; }}
    .mini-card li {{ display: flex; justify-content: space-between; gap: 10px; padding: 6px 0; }}
    .content-card {{ display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 14px; padding: 14px; margin-bottom: 12px; box-shadow: none; }}
    .content-card img {{ width: 220px; aspect-ratio: 16/9; object-fit: cover; border-radius: 12px; border: 1px solid var(--line); }}
    .artifact {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 14px; display: grid; padding: 14px; }}
    .artifact span {{ color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .empty {{ background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 16px; color: var(--muted); padding: 18px; }}
    @media (max-width: 1080px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ height: auto; position: static; }}
      main {{ padding: 18px; }}
      .metrics, .check-grid, .two-col, .mini-grid, .artifacts, .content-card {{ grid-template-columns: 1fr; }}
      .content-card img {{ width: 100%; }}
    }}
    @media print {{
      aside {{ display: none; }}
      .shell {{ display: block; }}
      main {{ padding: 0; }}
      .section, .hero {{ break-inside: avoid; box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>X 金融热点系统<br/>验收报告</h1>
      <p>由 outputs/state.json 自动生成，按测试题能力项组织。</p>
      <nav>
        <a href="#summary">结果摘要</a>
        <a href="#core">核心能力</a>
        <a href="#bonus">扩展能力</a>
        <a href="#llm">LLM 证据</a>
        <a href="#hotspots">Top 热点</a>
        <a href="#contents">内容与配图</a>
        <a href="#publishing">发布与反馈</a>
        <a href="#artifacts">交付物</a>
      </nav>
    </aside>
    <main>
      <section id="summary" class="hero">
        <p class="eyebrow">Submission Result</p>
        <h2>X 平台金融热点内容自动化运营系统</h2>
        <p>{h(note)}</p>
        <div class="hero-meta">
          <span>报告类型：{h(title)}</span>
          <span>生成时间：{h(generated_at)}</span>
          <span>数据源：{h(source_path.relative_to(ROOT).as_posix())}</span>
        </div>
      </section>
      <section class="metrics">{metric_cards(state)}</section>
      {checklist_section("core", CORE_CHECKS, state)}
      {checklist_section("bonus", BONUS_CHECKS, state)}
      {llm_section(state)}
      <section id="hotspots" class="section">
        <div class="section-head"><div><p class="eyebrow">Hotspot Ranking</p><h2>Top 热点与评分依据</h2></div></div>
        {top_hotspots(state)}
      </section>
      <section id="contents" class="section">
        <div class="section-head"><div><p class="eyebrow">Generated Posts</p><h2>生成文案与配图</h2></div></div>
        {content_section(state)}
      </section>
      <section id="publishing" class="section">
        <div class="section-head"><div><p class="eyebrow">Publishing Evidence</p><h2>发布、A/B 与反馈闭环</h2></div></div>
        <div class="two-col">
          <div><h3>Mock 发布记录</h3>{publishing_section(state)}</div>
          <div><h3>A/B 测试</h3>{ab_section(state)}</div>
        </div>
        <h3>策略记忆与反馈指标</h3>
        {feedback_section(state)}
      </section>
      <section id="artifacts" class="section">
        <div class="section-head"><div><p class="eyebrow">Artifacts</p><h2>交付物入口</h2></div></div>
        <div class="artifacts">{artifact_links()}</div>
      </section>
    </main>
  </div>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a polished HTML assessment report from outputs/state.json.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="Path to state.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Output HTML path")
    args = parser.parse_args()

    state = load_json(args.state)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(state, args.state.resolve()), encoding="utf-8")
    print(f"Generated {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
