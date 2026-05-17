from __future__ import annotations

from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.clients.mock_x_client import MockXClient, MockXRateLimitError
from backend.app.core.config import CARDS_DIR, OUTPUTS_DIR, ROOT_DIR, settings
from backend.app.db.session import DatabaseSessionManager
from backend.app.services.database_memory_service import DatabaseMemoryService
from backend.app.services.memory_service import MemoryService
from backend.app.workflows.hotspot_pipeline import HotspotPipeline

app = FastAPI(title=settings.app_name)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)

mock_x_client = MockXClient()
memory_backend = "json"
try:
    if settings.use_database:
        memory = DatabaseMemoryService(DatabaseSessionManager())
        memory_backend = "postgresql"
    else:
        memory = MemoryService()
except Exception:
    if not settings.db_fallback_to_json:
        raise
    memory = MemoryService()
    memory_backend = "json_fallback"
pipeline = HotspotPipeline(mock_x_client, memory)
scheduler = BackgroundScheduler(timezone="UTC")

static_dir = Path(__file__).parent / "static"
frontend_dist_dir = ROOT_DIR / "frontend" / "dist"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
if frontend_dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist_dir / "assets")), name="frontend_assets")


@app.on_event("startup")
def start_scheduler() -> None:
    if settings.enable_scheduler and not scheduler.running:
        scheduler.add_job(
            lambda: pipeline.run(auto_approve=False, publish_count=0, reset_state=False),
            "interval",
            minutes=settings.collection_interval_minutes,
            id="collect_hotspots",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()


@app.on_event("shutdown")
def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    if frontend_dist_dir.exists():
        return (frontend_dist_dir / "index.html").read_text(encoding="utf-8")
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "app": settings.app_name,
        "mode": settings.x_mode,
        "memory_backend": memory_backend,
        "scheduler_enabled": settings.enable_scheduler,
        "scheduler_running": scheduler.running,
    }


@app.post("/api/demo/run")
def run_demo(top_n: int = 10, publish_count: int = 3, auto_approve: bool = True) -> dict:
    try:
        return pipeline.run(top_n=top_n, publish_count=publish_count, auto_approve=auto_approve, reset_state=True)
    except MockXRateLimitError as exc:
        raise HTTPException(status_code=429, detail={"endpoint": exc.endpoint, "reset_time": exc.reset_time}) from exc


@app.get("/api/state")
def get_state() -> dict:
    return memory.load()


@app.get("/api/hotspots")
def get_hotspots() -> dict:
    state = memory.load()
    scores = {s["cluster_id"]: s for s in state.get("hot_scores", [])}
    hotspots = []
    for cluster in state.get("event_clusters", []):
        score = scores.get(cluster["cluster_id"], {"hot_score": 0, "score_breakdown": {}})
        hotspots.append({**cluster, **score})
    hotspots.sort(key=lambda item: item.get("hot_score", 0), reverse=True)
    return {"items": hotspots}


@app.get("/api/review-queue")
def get_review_queue() -> dict:
    return {"items": memory.load().get("review_queue", [])}


@app.post("/api/review/{content_id}/approve")
def approve(content_id: str) -> dict:
    try:
        return pipeline.approve_and_publish(content_id)
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail="Content not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/published")
def get_published() -> dict:
    return {"items": memory.load().get("publish_records", [])}


@app.get("/api/platform-dispatches")
def get_platform_dispatches() -> dict:
    return {"items": memory.load().get("platform_dispatches", [])}


@app.get("/api/ab-tests")
def get_ab_tests() -> dict:
    return {"items": memory.load().get("ab_test_variants", [])}


@app.post("/api/performance/refresh")
def refresh_performance() -> dict:
    return {"items": pipeline.refresh_performance_metrics()}


@app.post("/api/mock/simulate-429")
def simulate_429(endpoint: str = "create_post") -> dict:
    return mock_x_client.simulate_429(endpoint)


@app.get("/api/scheduler")
def scheduler_status() -> dict:
    return {
        "enabled": settings.enable_scheduler,
        "running": scheduler.running,
        "jobs": [{"id": job.id, "next_run_time": str(job.next_run_time)} for job in scheduler.get_jobs()],
    }


@app.get("/mock_x/posts/{mock_post_id}", response_class=HTMLResponse)
def mock_post(mock_post_id: str) -> str:
    record = mock_x_client.get_mock_post(mock_post_id)
    if record is None:
        state = memory.load()
        record = next((r for r in state.get("publish_records", []) if r.get("mock_post_id") == mock_post_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Mock post not found")
    media = ""
    if record.get("card_path"):
        path = Path(record["card_path"])
        if path.exists():
            relative = path.relative_to(OUTPUTS_DIR).as_posix()
            media = f'<img src="/outputs/{relative}" alt="Generated financial card" />'
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>{mock_post_id}</title>
      <style>
        body {{ margin: 0; background: #f8fafc; font-family: Arial, sans-serif; color: #0f172a; }}
        main {{ max-width: 760px; margin: 40px auto; background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 28px; }}
        .handle {{ color: #475569; margin-bottom: 16px; }}
        .text {{ font-size: 20px; line-height: 1.5; white-space: pre-wrap; }}
        img {{ width: 100%; border-radius: 8px; margin-top: 20px; border: 1px solid #e2e8f0; }}
        .meta {{ margin-top: 20px; color: #64748b; font-size: 14px; }}
      </style>
    </head>
    <body>
      <main>
        <div class="handle">@MockFinancialAgent · Mock X API</div>
        <div class="text">{record.get("tweet_text", "")}</div>
        {media}
        <div class="meta">Published via local mock endpoint. No real X post was created.</div>
      </main>
    </body>
    </html>
    """


@app.get("/{page_path:path}", response_class=HTMLResponse)
def frontend_route(page_path: str) -> str:
    if page_path in {"overview", "hotspots", "review", "memory"}:
        return index()
    raise HTTPException(status_code=404, detail="Not found")
