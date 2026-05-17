from __future__ import annotations

import json
import os
import base64
import subprocess
import urllib.error
import urllib.request
import uuid
import wave
import asyncio
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "outputs" / "demo"
STATE_PATH = ROOT / "outputs" / "state.json"
NARRATION_TEXT = DEMO_DIR / "product_narration.txt"
NARRATION_WAV = DEMO_DIR / "product_narration.wav"


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02},000"


def pct(value: float, maximum: float) -> int:
    if maximum <= 0:
        return 0
    return max(4, min(100, int(value / maximum * 100)))


def build_assets() -> None:
    state = load_state()
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        "raw_posts": len(state.get("raw_posts", [])),
        "clusters": len(state.get("event_clusters", [])),
        "contents": len(state.get("generated_contents", [])),
        "published": len(state.get("publish_records", [])),
        "ab": len(state.get("ab_test_variants", [])),
        "cards": len(state.get("image_cards", [])),
        "dispatches": len(state.get("platform_dispatches", [])),
        "metrics": len(state.get("performance_metrics", [])),
    }
    hotspots = state.get("top_hotspots", [])[:3]
    top_score = max([float(item.get("hot_score") or 0) for item in hotspots] or [1])
    top_rows = "\n".join(
        f"""
        <div class="rank-row">
          <div><strong>{index}. {item.get('main_title', 'N/A')}</strong><span>{item.get('source_count', 0)} sources · {item.get('event_type', 'event')}</span></div>
          <div class="meter"><i style="width:{pct(float(item.get('hot_score') or 0), top_score)}%"></i></div>
          <b>{item.get('hot_score', 0)}</b>
        </div>
        """
        for index, item in enumerate(hotspots, 1)
    )
    first_card = ""
    if state.get("image_cards"):
        first_card = "/outputs/cards/" + Path(state["image_cards"][0]["card_path"]).name
    links = "\n".join(
        f"<li>{record.get('mock_post_url', '')}</li>"
        for record in state.get("publish_records", [])[:3]
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X 金融热点 Agent 产品演示</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: Arial, "Microsoft YaHei", sans-serif; background:#07111f; color:#e5eefb; overflow:hidden; }}
.slide {{ display:none; width:100vw; height:100vh; padding:54px 68px; position:relative; background:linear-gradient(135deg,#07111f 0%,#0f172a 52%,#042f2e 100%); }}
.slide.active {{ display:flex; flex-direction:column; justify-content:center; }}
.eyebrow {{ color:#5eead4; font-size:22px; font-weight:800; letter-spacing:.08em; margin-bottom:18px; }}
h1 {{ margin:0 0 22px; font-size:60px; line-height:1.06; max-width:1160px; }}
h2 {{ margin:0 0 22px; font-size:48px; line-height:1.12; }}
p {{ font-size:28px; line-height:1.48; color:#cbd5e1; max-width:1160px; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px; margin-top:28px; }}
.card {{ background:rgba(15,23,42,.82); border:1px solid rgba(94,234,212,.32); border-radius:12px; padding:22px; min-height:145px; }}
.card strong {{ display:block; font-size:44px; color:#5eead4; margin-bottom:8px; }}
.card span {{ font-size:21px; color:#cbd5e1; }}
.two {{ display:grid; grid-template-columns:1.05fr .95fr; gap:34px; align-items:center; }}
ul {{ margin:0; padding-left:28px; }}
li {{ font-size:26px; line-height:1.45; margin:10px 0; color:#dbeafe; }}
.flow {{ display:flex; flex-wrap:wrap; gap:12px; margin-top:20px; }}
.flow span {{ padding:12px 15px; border-radius:8px; background:rgba(13,148,136,.22); border:1px solid rgba(94,234,212,.38); font-size:22px; }}
.caption {{ position:absolute; left:50%; bottom:30px; transform:translateX(-50%); width:calc(100% - 150px); padding:17px 24px; border-radius:10px; background:rgba(3,7,18,.88); border:1px solid rgba(94,234,212,.55); font-size:28px; line-height:1.4; font-weight:800; text-align:center; box-shadow:0 18px 45px rgba(0,0,0,.35); }}
.note {{ margin-top:22px; padding:20px 24px; border-left:5px solid #5eead4; background:rgba(15,23,42,.72); color:#dbeafe; font-size:24px; line-height:1.45; }}
.diagram {{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; }}
.node {{ padding:18px 14px; text-align:center; border-radius:10px; background:#102033; border:1px solid rgba(94,234,212,.36); font-size:22px; font-weight:800; }}
.rank {{ background:rgba(15,23,42,.72); border:1px solid rgba(148,163,184,.28); border-radius:12px; padding:18px; }}
.rank-row {{ display:grid; grid-template-columns:1.2fr 1fr 80px; gap:16px; align-items:center; padding:14px 0; border-bottom:1px solid rgba(148,163,184,.2); }}
.rank-row strong {{ display:block; font-size:21px; color:#e2e8f0; }}
.rank-row span {{ color:#94a3b8; font-size:18px; }}
.meter {{ height:18px; background:#1e293b; border-radius:999px; overflow:hidden; }}
.meter i {{ display:block; height:100%; background:linear-gradient(90deg,#0d9488,#5eead4); border-radius:999px; }}
.rank-row b {{ color:#5eead4; font-size:24px; text-align:right; }}
.shot {{ max-width:100%; border-radius:12px; border:1px solid rgba(148,163,184,.32); box-shadow:0 22px 70px rgba(0,0,0,.35); }}
.links li {{ font-size:21px; font-family:Consolas,monospace; color:#a7f3d0; word-break:break-all; }}
.footer {{ position:absolute; right:32px; top:24px; color:#94a3b8; font-size:18px; }}
</style>
</head>
<body>
<section id="s0" class="slide active">
  <div class="footer">Product Demo · 3-5 min</div>
  <div class="eyebrow">做了什么</div>
  <h1>X 平台金融热点内容自动化运营系统</h1>
  <p>一个面向金融内容运营的端到端 AI Agent：从热点发现、事实校验、文案生成、合规审核、动态配图，到发布、A/B 对比和反馈优化。</p>
  <div class="grid">
    <div class="card"><strong>{metrics["raw_posts"]}</strong><span>采集内容</span></div>
    <div class="card"><strong>{metrics["clusters"]}</strong><span>热点事件簇</span></div>
    <div class="card"><strong>{metrics["contents"]}</strong><span>中英文内容</span></div>
    <div class="card"><strong>{metrics["published"]}</strong><span>Mock 发布样例</span></div>
  </div>
  <div class="caption">这是一个产品级金融热点运营 Agent，目标是把“发现热点到合规发布”做成完整闭环。</div>
</section>
<section id="s1" class="slide">
  <div class="eyebrow">为什么这样做</div>
  <h2>金融内容运营有三件事不能妥协</h2>
  <div class="grid">
    <div class="card"><strong>快</strong><span>热点需要在 5-10 分钟内捕获和响应。</span></div>
    <div class="card"><strong>准</strong><span>同一事件要跨来源聚合，不能被重复信息淹没。</span></div>
    <div class="card"><strong>稳</strong><span>金融内容必须合规、可审计、可回放。</span></div>
    <div class="card"><strong>可优化</strong><span>发布后要用互动数据反向改进策略。</span></div>
  </div>
  <div class="note">因此系统不是“让 LLM 写一条推文”，而是设计成可追踪的运营流水线。</div>
  <div class="caption">为什么不是简单脚本？因为金融内容需要速度、准确性、合规审计和持续优化。</div>
</section>
<section id="s2" class="slide">
  <div class="eyebrow">为什么牛：架构</div>
  <h2>状态机式 Agent 编排，每一步都有证据</h2>
  <div class="diagram">
    <div class="node">采集</div><div class="node">清洗</div><div class="node">实体抽取</div><div class="node">聚类</div><div class="node">突发优先级</div>
    <div class="node">热度评分</div><div class="node">事实校验</div><div class="node">Hashtag</div><div class="node">LLM 生成</div><div class="node">合规审核</div>
    <div class="node">动态配图</div><div class="node">审核队列</div><div class="node">Mock 发布</div><div class="node">指标回收</div><div class="node">策略记忆</div>
  </div>
  <div class="note">自由对话式 Agent 很难审计；状态机式编排能保留每一步输入、输出、状态和失败路径。</div>
  <div class="caption">讲架构时画面就是架构：每个 Agent 负责一个明确阶段，流水线可复现、可审计。</div>
</section>
<section id="s3" class="slide">
  <div class="eyebrow">为什么牛：热点算法</div>
  <h2>不是看点赞数，而是看事件价值</h2>
  <div class="two">
    <div>
      <ul>
        <li>8 因子 HotScore：互动、来源权威、跨来源确认、市场相关性、关键词、趋势、时间衰减、突发加权。</li>
        <li>同事件聚类：实体 Jaccard、文本 token、轻量向量、事件类型和 6 小时时间窗。</li>
        <li>输出 Top N、分数拆解和原始依据。</li>
      </ul>
    </div>
    <div class="rank">{top_rows}</div>
  </div>
  <div class="caption">说结果时画面给出热点排序和评分依据：为什么它是热点，可以被解释。</div>
</section>
<section id="s4" class="slide">
  <div class="eyebrow">为什么牛：内容生产</div>
  <h2>LLM 生成被事实和合规约束住</h2>
  <div class="two">
    <ul>
      <li>DeepSeek LLM 生成原创推文。</li>
      <li>中英文双语、280 字符限制、3-5 个 Hashtag。</li>
      <li>规则合规 + LLM 复核，强制免责声明。</li>
      <li>动态卡片输出 16:9 主图和 1:1 方图。</li>
    </ul>
    <img class="shot" src="{first_card}" alt="Generated card">
  </div>
  <div class="caption">讲内容生产时画面展示真实生成卡片：文案、数据、品牌和合规信息同时呈现。</div>
</section>
<section id="s5" class="slide">
  <div class="eyebrow">为什么牛：运营闭环</div>
  <h2>发布不是终点，互动数据会反向优化策略</h2>
  <div class="grid">
    <div class="card"><strong>{metrics["ab"]}</strong><span>A/B 变体</span></div>
    <div class="card"><strong>{metrics["dispatches"]}</strong><span>多平台分发记录</span></div>
    <div class="card"><strong>{metrics["metrics"]}</strong><span>互动反馈指标</span></div>
    <div class="card"><strong>3 类</strong><span>Style / Source / Hashtag 记忆</span></div>
  </div>
  <div class="flow"><span>发布</span><span>回收 likes/reposts/replies/views</span><span>计算 engagement_rate</span><span>更新策略权重</span><span>下一轮生成更优</span></div>
  <div class="caption">讲闭环时画面展示闭环：发布后的互动指标会回到记忆系统，影响下一轮策略。</div>
</section>
<section id="s6" class="slide">
  <div class="eyebrow">最后实现的结果</div>
  <h2>可运行、可检查、可扩展的交付物</h2>
  <div class="two">
    <ul class="links">{links}</ul>
    <div>
      <div class="card"><strong>30 passed</strong><span>自动化测试通过</span></div>
      <div class="card" style="margin-top:16px"><strong>HTML 报告</strong><span>outputs/submission_report.html 可直接验收。</span></div>
      <div class="card" style="margin-top:16px"><strong>生产扩展</strong><span>可切换 PostgreSQL/pgvector、Telegram、Threads、外部事实源和真实 X API。</span></div>
    </div>
  </div>
  <div class="caption">最终交付不是截图，而是一套能运行、能验收、能扩展的金融内容运营系统。</div>
</section>
<script>
const params = new URLSearchParams(location.search);
const slide = params.get('slide') || 's0';
document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
const target = document.getElementById(slide);
if (target) target.classList.add('active');
</script>
</body>
</html>
"""
    (DEMO_DIR / "product_story.html").write_text(html, encoding="utf-8")

    segments = [
        {
            "slide": "s0",
            "seconds": 28,
            "voice": "大家好，这个项目是 X 平台金融热点内容自动化运营系统。它做的不是单点文案生成，而是把金融热点从发现、判断、生成、合规、配图、发布到反馈优化，串成一条完整的运营闭环。",
        },
        {
            "slide": "s1",
            "seconds": 34,
            "voice": "我为什么这样设计？金融内容运营有三个核心约束。第一要快，热点通常只有很短的响应窗口。第二要准，同一事件会被不同来源反复表达，必须聚合成一个热点。第三要稳，金融内容必须合规、可审计、可回放。所以这个项目不是让大模型直接写一句话，而是做成可追踪的产品流程。",
        },
        {
            "slide": "s2",
            "seconds": 38,
            "voice": "系统架构采用状态机式 Agent 编排。采集、清洗、实体抽取、聚类、突发优先级、热度评分、事实校验、标签生成、推文生成、合规审核、动态配图、审核队列、发布、指标回收和策略记忆，各自负责一个明确阶段。这样每一步都有输入输出和状态记录，适合金融场景的审计要求。",
        },
        {
            "slide": "s3",
            "seconds": 38,
            "voice": "热点算法不是简单看点赞数。系统使用八因子 HotScore，综合互动表现、来源权威、跨来源确认、市场相关性、关键词匹配、趋势话题、时间衰减和突发事件加权。聚类也不依赖预置标签，而是通过实体、文本、事件类型和时间窗合并同一事件。最终输出 Top 热点、分数和拆解依据。",
        },
        {
            "slide": "s4",
            "seconds": 38,
            "voice": "内容生产环节接入 DeepSeek 兼容的大模型，同时用事实校验和合规规则约束生成结果。系统支持中英文推文，限制二百八十字符，自动补充三到五个 Hashtag，并强制加入免责声明。配图使用动态卡片模板，生成十六比九主图和一比一方图，卡片里包含标题、关键数据、评分因子和品牌标识。",
        },
        {
            "slide": "s5",
            "seconds": 38,
            "voice": "这个系统最有价值的部分是运营闭环。发布不是终点，系统会回收点赞、转发、评论、引用和浏览量，计算互动率，再更新文案风格、来源和 Hashtag 的策略权重。同时支持英文和中文 A B 测试、多平台分发、突发事件优先级和外部事实源校验。",
        },
        {
            "slide": "s6",
            "seconds": 39,
            "voice": "最终结果是一套可运行、可检查、可扩展的交付物。当前运行采集了三十条内容，聚合出十一个事件簇，生成八条内容，发布六条 mock 样例，并产生十二条多平台分发记录和六条反馈指标。项目提供 React 控制台、HTML 验收报告、运行结果 JSON、架构文档和自动化测试。真实生产时，只需要替换 X、Telegram、Threads 和外部金融数据源凭证，主流程不用推倒重来。",
        },
    ]
    (DEMO_DIR / "product_segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    NARRATION_TEXT.write_text("\n\n".join(s["voice"] for s in segments), encoding="utf-8")
    cursor = 0
    blocks = []
    for index, segment in enumerate(segments, 1):
        start = cursor
        cursor += int(segment["seconds"])
        blocks.append(f"{index}\n{timestamp(start)} --> {timestamp(cursor)}\n{segment['voice']}\n")
    (DEMO_DIR / "product_subtitles.srt").write_text("\n".join(blocks), encoding="utf-8-sig")


def _decode_volcengine_audio_chunks(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    errors: list[str] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("data:"):
            text = text[5:].strip()
        if text == "[DONE]":
            continue
        try:
            item = json.loads(text)
        except json.JSONDecodeError:
            continue
        code = item.get("code")
        message = item.get("message")
        if code and code != 0:
            errors.append(f"{code}: {message or item}")
            continue
        data = item.get("data")
        if isinstance(data, str) and data:
            chunks.append(base64.b64decode(data))
    if errors:
        raise RuntimeError("; ".join(errors))
    return b"".join(chunks)


async def _synthesize_ark_realtime_voice_async() -> bool:
    try:
        import websockets
    except ImportError:
        print("Ark Realtime TTS failed: websockets package is not installed")
        return False

    api_key = (
        os.getenv("VOLCENGINE_ARK_API_KEY", "").strip()
        or os.getenv("ARK_API_KEY", "").strip()
        or os.getenv("ARK_TTS_API_KEY", "").strip()
    )
    if not api_key:
        return False

    model = os.getenv("VOLCENGINE_ARK_TTS_MODEL", "doubao-tts").strip()
    voice = os.getenv("VOLCENGINE_ARK_TTS_VOICE", "zh_female_kailangjiejie_moon_bigtts").strip()
    sample_rate = int(os.getenv("VOLCENGINE_ARK_TTS_SAMPLE_RATE", "16000"))
    url = os.getenv(
        "VOLCENGINE_ARK_TTS_URL",
        f"wss://ai-gateway.vei.volces.com/v1/realtime?model={model}",
    )
    text = NARRATION_TEXT.read_text(encoding="utf-8")
    headers = {"Authorization": f"Bearer {api_key}"}
    connect_kwargs = {"ping_interval": None}
    try:
        connect_kwargs["extra_headers"] = headers
        ws_context = websockets.connect(url, **connect_kwargs)
    except TypeError:
        connect_kwargs.pop("extra_headers", None)
        connect_kwargs["additional_headers"] = headers
        ws_context = websockets.connect(url, **connect_kwargs)

    chunks: list[bytes] = []
    try:
        async with ws_context as ws:
            await ws.send(json.dumps({
                "type": "tts_session.update",
                "session": {
                    "voice": voice,
                    "output_audio_format": "pcm",
                    "output_audio_sample_rate": sample_rate,
                },
            }, ensure_ascii=False))
            await ws.send(json.dumps({"type": "input_text.append", "text": text}, ensure_ascii=False))
            await ws.send(json.dumps({"type": "input_text.done"}, ensure_ascii=False))
            for _ in range(1200):
                message = await asyncio.wait_for(ws.recv(), timeout=90)
                event = json.loads(message)
                event_type = event.get("type", "")
                if event_type.endswith(".error") or event_type == "error":
                    raise RuntimeError(event.get("message") or event.get("error") or event)
                delta = event.get("delta") or event.get("audio") or event.get("data")
                if event_type in {"response.audio.delta", "audio.delta", "tts.audio.delta"} and isinstance(delta, str):
                    chunks.append(base64.b64decode(delta))
                if event_type in {"response.audio.done", "audio.done", "tts.audio.done", "response.done"}:
                    break
    except Exception as exc:
        print(f"Ark Realtime TTS failed: {exc}")
        return False

    if not chunks:
        print("Ark Realtime TTS failed: empty audio stream")
        return False

    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    with wave.open(str(NARRATION_WAV), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(chunks))
    (DEMO_DIR / "product_narration_audio_path.txt").write_text(str(NARRATION_WAV), encoding="utf-8")
    print(f"Ark Realtime TTS generated: {NARRATION_WAV}")
    return True


def synthesize_ark_realtime_voice() -> bool:
    load_env_file()
    return asyncio.run(_synthesize_ark_realtime_voice_async())


def synthesize_volcengine_voice() -> bool:
    load_env_file()
    api_key = os.getenv("VOLCENGINE_TTS_API_KEY", "").strip()
    app_id = os.getenv("VOLCENGINE_TTS_APPID", "").strip()
    access_key = os.getenv("VOLCENGINE_TTS_ACCESS_KEY", "").strip()
    app_key = os.getenv("VOLCENGINE_TTS_SECRET_KEY", "").strip()
    resource_id = os.getenv("VOLCENGINE_TTS_RESOURCE_ID", "seed-tts-2.0").strip()
    if not api_key and not (app_id and access_key):
        return False

    text = NARRATION_TEXT.read_text(encoding="utf-8")
    audio_format = os.getenv("VOLCENGINE_TTS_FORMAT", "mp3").strip()
    body = {
        "req_params": {
            "text": text,
            "speaker": os.getenv("VOLCENGINE_TTS_SPEAKER", "zh_female_cancan_uranus_bigtts"),
            "audio_params": {
                "format": audio_format,
                "sample_rate": int(os.getenv("VOLCENGINE_TTS_SAMPLE_RATE", "24000")),
            },
            "speech_rate": int(os.getenv("VOLCENGINE_TTS_SPEECH_RATE", "0")),
            "loudness_rate": int(os.getenv("VOLCENGINE_TTS_LOUDNESS_RATE", "0")),
        }
    }
    emotion = os.getenv("VOLCENGINE_TTS_EMOTION", "").strip()
    if emotion:
        body["req_params"]["emotion"] = emotion
        body["req_params"]["emotion_scale"] = int(os.getenv("VOLCENGINE_TTS_EMOTION_SCALE", "2"))
    headers = {
        "Content-Type": "application/json",
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }
    if api_key:
        headers["X-Api-Key"] = api_key
    else:
        headers["X-Api-App-Id"] = app_id
        headers["X-Api-Access-Key"] = access_key
        if app_key:
            headers["X-Api-App-Key"] = app_key
    request = urllib.request.Request(
        os.getenv("VOLCENGINE_TTS_URL", "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse"),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(os.getenv("VOLCENGINE_TTS_TIMEOUT_SECONDS", "120"))) as response:
            audio = _decode_volcengine_audio_chunks(response.read())
        if not audio:
            print("Volcengine TTS failed: empty audio stream")
            return False
        target = DEMO_DIR / f"product_narration.{audio_format}"
        target.write_bytes(audio)
        if target != NARRATION_WAV:
            (DEMO_DIR / "product_narration_audio_path.txt").write_text(str(target), encoding="utf-8")
        print(f"Volcengine TTS generated: {target}")
        return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Volcengine TTS failed: HTTP {exc.code} {detail}")
        return False
    except Exception as exc:
        print(f"Volcengine TTS failed: {exc}")
        return False


def synthesize_system_voice() -> None:
    script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Huihui Desktop')
$synth.Rate = -1
$synth.Volume = 100
$text = Get-Content -Path '{NARRATION_TEXT.as_posix()}' -Raw -Encoding UTF8
$synth.SetOutputToWaveFile('{NARRATION_WAV.as_posix()}')
$synth.Speak($text)
$synth.Dispose()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", script], cwd=ROOT, check=True)


def synthesize_voice() -> None:
    load_env_file()
    provider = os.getenv("DEMO_TTS_PROVIDER", "auto").strip().lower()
    if provider in {"auto", "ark", "volcark", "doubao", "volcengine"} and synthesize_ark_realtime_voice():
        return
    if provider in {"auto", "volcengine", "openspeech"} and synthesize_volcengine_voice():
        return
    if provider in {"volcengine", "volcark", "doubao", "ark", "openspeech"} and os.getenv("DEMO_TTS_STRICT", "").lower() in {"1", "true", "yes"}:
        raise RuntimeError("Requested remote TTS did not produce audio.")
    print("Using local Windows TTS fallback.")
    synthesize_system_voice()


if __name__ == "__main__":
    build_assets()
    synthesize_voice()
    print((DEMO_DIR / "product_story.html").resolve())
    audio_path_file = DEMO_DIR / "product_narration_audio_path.txt"
    if audio_path_file.exists():
        print(Path(audio_path_file.read_text(encoding="utf-8")).resolve())
    else:
        print(NARRATION_WAV.resolve())
