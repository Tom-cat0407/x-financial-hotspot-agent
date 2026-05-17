import React, { MouseEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Database,
  ExternalLink,
  FileText,
  Gauge,
  GitBranch,
  Play,
  RefreshCw,
  Settings2,
  ShieldCheck
} from "lucide-react";
import "./styles.css";

type PageKey = "overview" | "hotspots" | "review" | "memory";

type Score = {
  cluster_id: string;
  hot_score: number;
  score_breakdown: Record<string, number>;
};

type Cluster = {
  cluster_id: string;
  main_title: string;
  summary: string;
  event_type: string;
  entities: string[];
  source_count: number;
  independent_source_count: number;
  confidence_score: number;
  emergency?: {
    emergency_level: string;
    emergency_reason: string;
    emergency_boost: number;
  };
};

type ReviewItem = {
  review_id: string;
  content_id: string;
  cluster_id: string;
  tweet_text: string;
  zh_tweet_text?: string;
  risk_level: string;
  review_status: string;
};

type PublishRecord = {
  publish_id: string;
  mock_post_id: string;
  mock_post_url: string;
  tweet_text: string;
  content_id: string;
  cluster_id: string;
  compliance_report_id: string;
  card_path: string;
  ok: boolean;
};

type RunEvent = {
  state: string;
  message: string;
  created_at: string;
};

type PerformanceMetric = {
  performance_metric_id: string;
  publish_id: string;
  mock_post_id: string;
  engagement_rate: number;
  view_count: number;
};

type PlatformDispatch = {
  dispatch_id: string;
  platform: string;
  ok: boolean;
  skipped?: boolean;
  reason?: string;
};

type ABVariant = {
  variant_id: string;
  experiment_id: string;
  variant_name: string;
  cluster_id: string;
  style: string;
  engagement_rate?: number;
  is_winner?: boolean;
};

type State = {
  raw_posts?: unknown[];
  event_clusters?: Cluster[];
  hot_scores?: Score[];
  review_queue?: ReviewItem[];
  publish_records?: PublishRecord[];
  performance_metrics?: PerformanceMetric[];
  platform_dispatches?: PlatformDispatch[];
  ab_test_variants?: ABVariant[];
  run_events?: RunEvent[];
  llm_enabled?: boolean;
  strategy_memory?: {
    style_weight?: Record<string, number>;
    source_weight?: Record<string, number>;
    hashtag_weight?: Record<string, number>;
  };
};

type Health = {
  ok: boolean;
  app: string;
  mode: string;
  memory_backend: string;
  scheduler_enabled?: boolean;
  scheduler_running?: boolean;
};

type RunOptions = {
  publishCount: number;
  autoApprove: boolean;
};

const routes: Array<{ key: PageKey; path: string; label: string; icon: React.ReactNode }> = [
  { key: "overview", path: "/overview", label: "总览", icon: <Gauge size={18} /> },
  { key: "hotspots", path: "/hotspots", label: "热点", icon: <BarChart3 size={18} /> },
  { key: "review", path: "/review", label: "审核", icon: <ShieldCheck size={18} /> },
  { key: "memory", path: "/memory", label: "记忆", icon: <Database size={18} /> }
];

const routeByPath = new Map(routes.map((route) => [route.path, route.key]));

const api = {
  async health(): Promise<Health> {
    return fetch("/health").then((response) => response.json());
  },
  async state(): Promise<State> {
    return fetch("/api/state").then((response) => response.json());
  },
  async run(options: RunOptions): Promise<State> {
    const params = new URLSearchParams({
      auto_approve: String(options.autoApprove),
      publish_count: String(options.publishCount)
    });
    return fetch(`/api/demo/run?${params.toString()}`, { method: "POST" }).then((response) => {
      if (!response.ok) throw new Error("Demo run failed");
      return response.json();
    });
  },
  async refreshPerformance(): Promise<{ items: PerformanceMetric[] }> {
    return fetch("/api/performance/refresh", { method: "POST" }).then((response) => {
      if (!response.ok) throw new Error("Performance refresh failed");
      return response.json();
    });
  }
};

function pageFromLocation(): PageKey {
  return routeByPath.get(window.location.pathname) || "overview";
}

function App() {
  const [state, setState] = useState<State>({});
  const [health, setHealth] = useState<Health | null>(null);
  const [currentPage, setCurrentPage] = useState<PageKey>(() => pageFromLocation());
  const [busy, setBusy] = useState(false);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [error, setError] = useState("");
  const [publishCount, setPublishCount] = useState(3);
  const [autoApprove, setAutoApprove] = useState(true);

  const scores = useMemo(
    () => new Map((state.hot_scores || []).map((score) => [score.cluster_id, score])),
    [state.hot_scores]
  );
  const hotspots = useMemo(() => {
    return [...(state.event_clusters || [])].sort(
      (a, b) => (scores.get(b.cluster_id)?.hot_score || 0) - (scores.get(a.cluster_id)?.hot_score || 0)
    );
  }, [scores, state.event_clusters]);

  async function refresh() {
    setError("");
    const [healthData, stateData] = await Promise.all([api.health(), api.state()]);
    setHealth(healthData);
    setState(stateData);
  }

  async function runDemo() {
    setBusy(true);
    setError("");
    try {
      const stateData = await api.run({ publishCount, autoApprove });
      setState(stateData);
      setHealth(await api.health());
    } catch (err) {
      setError(err instanceof Error ? err.message : "运行失败，请确认后端服务已启动");
    } finally {
      setBusy(false);
    }
  }

  async function refreshFeedback() {
    setFeedbackBusy(true);
    setError("");
    try {
      await api.refreshPerformance();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "反馈指标刷新失败");
    } finally {
      setFeedbackBusy(false);
    }
  }

  function navigate(event: MouseEvent<HTMLAnchorElement>, path: string, page: PageKey) {
    event.preventDefault();
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    setCurrentPage(page);
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }

  useEffect(() => {
    const onPopState = () => {
      setCurrentPage(pageFromLocation());
      window.setTimeout(() => window.scrollTo({ top: 0, left: 0, behavior: "auto" }), 0);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (window.location.pathname === "/") {
      window.history.replaceState({}, "", "/overview");
      setCurrentPage("overview");
    }
    refresh().catch(() => setError("无法连接后端服务"));
  }, []);

  const commonProps = {
    state,
    health,
    hotspots,
    scores,
    error,
    busy,
    feedbackBusy,
    publishCount,
    autoApprove,
    setPublishCount,
    setAutoApprove,
    runDemo,
    refresh,
    refreshFeedback
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">X</div>
          <div>
            <strong>Financial Hotspot Agent</strong>
            <span>Mock X API / PostgreSQL ready</span>
          </div>
        </div>
        <nav aria-label="主导航">
          {routes.map((route) => (
            <a
              aria-current={currentPage === route.key ? "page" : undefined}
              className={currentPage === route.key ? "active" : ""}
              href={route.path}
              key={route.key}
              onClick={(event) => navigate(event, route.path, route.key)}
            >
              {route.icon}
              {route.label}
            </a>
          ))}
        </nav>
      </aside>

      <main>
        {currentPage === "overview" && <OverviewPage {...commonProps} />}
        {currentPage === "hotspots" && <HotspotsPage state={state} hotspots={hotspots} scores={scores} />}
        {currentPage === "review" && <ReviewPage state={state} />}
        {currentPage === "memory" && <MemoryPage state={state} feedbackBusy={feedbackBusy} refreshFeedback={refreshFeedback} />}
      </main>
    </div>
  );
}

function OverviewPage({
  state,
  health,
  error,
  busy,
  feedbackBusy,
  publishCount,
  autoApprove,
  setPublishCount,
  setAutoApprove,
  runDemo,
  refresh,
  refreshFeedback
}: {
  state: State;
  health: Health | null;
  hotspots: Cluster[];
  scores: Map<string, Score>;
  error: string;
  busy: boolean;
  feedbackBusy: boolean;
  publishCount: number;
  autoApprove: boolean;
  setPublishCount: (value: number) => void;
  setAutoApprove: (value: boolean) => void;
  runDemo: () => void;
  refresh: () => void;
  refreshFeedback: () => void;
}) {
  return (
    <>
      <section className="page-header">
        <div>
          <h1>X 平台金融热点内容自动化运营系统</h1>
          <p>端到端运行：采集、聚类、评分、事实校验、合规、配图、审核、Mock 发布与策略记忆更新。</p>
        </div>
        <div className="actions">
          <div className="run-options" aria-label="Demo 参数">
            <label className="field">
              <span>发布数</span>
              <input
                min={0}
                max={6}
                type="number"
                value={publishCount}
                onChange={(event) => setPublishCount(clampNumber(event.target.value, 0, 6))}
              />
            </label>
            <label className="check-field">
              <input
                checked={autoApprove}
                type="checkbox"
                onChange={(event) => setAutoApprove(event.target.checked)}
              />
              自动审核发布
            </label>
          </div>
          <button onClick={runDemo} disabled={busy}>
            {busy ? <RefreshCw className="spin" size={18} /> : <Play size={18} />}
            {busy ? "运行中" : "运行 Demo"}
          </button>
          <button className="secondary" onClick={refresh}>
            <RefreshCw size={18} />刷新
          </button>
          <button className="secondary" onClick={refreshFeedback} disabled={feedbackBusy || !(state.publish_records || []).length}>
            {feedbackBusy ? <RefreshCw className="spin" size={18} /> : <Activity size={18} />}
            刷新反馈
          </button>
        </div>
      </section>

      {error && <div className="notice"><AlertTriangle size={18} />{error}</div>}

      <section className="metrics">
        <Metric icon={<Activity />} label="采集内容" value={state.raw_posts?.length || 0} />
        <Metric icon={<GitBranch />} label="事件簇" value={state.event_clusters?.length || 0} />
        <Metric icon={<CheckCircle2 />} label="Mock 发布" value={state.publish_records?.length || 0} />
        <Metric icon={<Activity />} label="反馈指标" value={state.performance_metrics?.length || 0} />
        <Metric icon={<GitBranch />} label="A/B 变体" value={state.ab_test_variants?.length || 0} />
        <Metric icon={<ExternalLink />} label="多平台分发" value={state.platform_dispatches?.length || 0} />
        <Metric icon={<Database />} label="记忆后端" value={health?.memory_backend || "loading"} compact />
        <Metric icon={<Settings2 />} label="调度状态" value={health?.scheduler_running ? "running" : "off"} compact />
      </section>

      <section className="layout">
        <Panel title="运行事件" icon={<FileText size={18} />}>
          <RunEvents events={state.run_events || []} />
        </Panel>
        <Panel title="最近发布" icon={<ExternalLink size={18} />}>
          <PublishList records={(state.publish_records || []).slice(0, 3)} />
        </Panel>
      </section>
    </>
  );
}

function HotspotsPage({
  state,
  hotspots,
  scores
}: {
  state: State;
  hotspots: Cluster[];
  scores: Map<string, Score>;
}) {
  return (
    <>
      <PageTitle title="热点" description="展示 Top 热点、HotScore 拆解、原始事件依据和 Mock 发布链接。" />
      <section className="layout">
        <Panel title="Top 热点" icon={<BarChart3 size={18} />}>
          <div className="hotspot-list">
            {hotspots.length ? hotspots.map((cluster) => (
              <HotspotRow key={cluster.cluster_id} cluster={cluster} score={scores.get(cluster.cluster_id)} />
            )) : <Empty text="点击运行 Demo 后展示热点列表。" />}
          </div>
        </Panel>

        <Panel title="Mock 发布链接" icon={<ExternalLink size={18} />}>
          <PublishList records={state.publish_records || []} />
        </Panel>
      </section>
    </>
  );
}

function ReviewPage({ state }: { state: State }) {
  return (
    <>
      <PageTitle title="审核" description="查看合规风险、审核状态、中英文内容和最近状态机事件。" />
      <section className="layout">
        <Panel title="审核队列" icon={<ShieldCheck size={18} />}>
          <div className="review-list">
            {(state.review_queue || []).length ? state.review_queue!.map((item) => (
              <article className="review-row" key={item.review_id}>
                <div>
                  <strong>{item.review_status}</strong>
                  <span>{item.risk_level}</span>
                </div>
                <p>{item.tweet_text}</p>
                {item.zh_tweet_text && <p>{item.zh_tweet_text}</p>}
              </article>
            )) : <Empty text="暂无审核项。" />}
          </div>
        </Panel>

        <Panel title="运行事件" icon={<FileText size={18} />}>
          <RunEvents events={state.run_events || []} />
        </Panel>
      </section>
    </>
  );
}

function MemoryPage({
  state,
  feedbackBusy,
  refreshFeedback
}: {
  state: State;
  feedbackBusy: boolean;
  refreshFeedback: () => void;
}) {
  return (
    <>
      <section className="page-header">
        <div>
          <h1>记忆</h1>
          <p>展示反馈闭环产生的策略记忆、A/B 测试结果和多平台分发记录。</p>
        </div>
        <div className="actions">
          <button className="secondary" onClick={refreshFeedback} disabled={feedbackBusy || !(state.publish_records || []).length}>
            {feedbackBusy ? <RefreshCw className="spin" size={18} /> : <Activity size={18} />}
            刷新反馈
          </button>
        </div>
      </section>

      <section className="memory-section">
        <Panel title="策略记忆" icon={<Database size={18} />}>
          <div className="memory-grid">
            <MemoryBlock title="Style Weight" data={state.strategy_memory?.style_weight} />
            <MemoryBlock title="Source Weight" data={state.strategy_memory?.source_weight} />
            <MemoryBlock title="Hashtag Weight" data={state.strategy_memory?.hashtag_weight} />
          </div>
        </Panel>
      </section>

      <section className="layout">
        <Panel title="A/B 测试" icon={<GitBranch size={18} />}>
          <div className="review-list">
            {(state.ab_test_variants || []).length ? state.ab_test_variants!.map((item) => (
              <article className="review-row" key={item.variant_id}>
                <div>
                  <strong>{item.variant_name} · {item.style}</strong>
                  <span>{item.is_winner ? "winner" : "variant"}</span>
                </div>
                <p>{item.cluster_id} / engagement_rate: {item.engagement_rate ?? 0}</p>
              </article>
            )) : <Empty text="暂无 A/B 测试记录。" />}
          </div>
        </Panel>

        <Panel title="多平台分发" icon={<ExternalLink size={18} />}>
          <div className="review-list">
            {(state.platform_dispatches || []).length ? state.platform_dispatches!.map((item) => (
              <article className="review-row" key={item.dispatch_id}>
                <div>
                  <strong>{item.platform}</strong>
                  <span>{item.ok ? "sent" : item.skipped ? "skipped" : "failed"}</span>
                </div>
                <p>{item.reason || item.dispatch_id}</p>
              </article>
            )) : <Empty text="暂无多平台分发记录。" />}
          </div>
        </Panel>
      </section>
    </>
  );
}

function PageTitle({ title, description }: { title: string; description: string }) {
  return (
    <section className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </section>
  );
}

function Metric({ icon, label, value, compact = false }: { icon: React.ReactNode; label: string; value: number | string; compact?: boolean }) {
  return (
    <article className="metric">
      <span className="metric-icon">{icon}</span>
      <div>
        <strong className={compact ? "compact-value" : ""}>{value}</strong>
        <span>{label}</span>
      </div>
    </article>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="panel">
      <header>
        <h2>{icon}{title}</h2>
      </header>
      {children}
    </section>
  );
}

function HotspotRow({ cluster, score }: { cluster: Cluster; score?: Score }) {
  return (
    <article className="hotspot-row">
      <div className="score-cell">
        <strong>{score?.hot_score || 0}</strong>
        <span>HotScore</span>
      </div>
      <div className="hotspot-body">
        <h3>{cluster.main_title}</h3>
        <p>{cluster.summary}</p>
        <div className="meta-line">
          <span>{cluster.event_type}</span>
          <span>{cluster.source_count} sources</span>
          <span>{cluster.emergency?.emergency_level || "low"} priority</span>
        </div>
        <div className="entity-line">
          {cluster.entities.map((entity) => <span key={entity}>{entity}</span>)}
        </div>
      </div>
      <pre>{JSON.stringify(score?.score_breakdown || {}, null, 2)}</pre>
    </article>
  );
}

function PublishList({ records }: { records: PublishRecord[] }) {
  return (
    <div className="publish-list">
      {records.length ? records.map((record) => (
        <article className="publish-item" key={record.publish_id}>
          <div className="publish-head">
            <strong>{record.mock_post_id}</strong>
            <span>{record.ok ? "published" : "failed"}</span>
          </div>
          <p>{record.tweet_text}</p>
          {record.mock_post_url && (
            <a href={record.mock_post_url} target="_blank" rel="noreferrer">
              打开 mock 链接 <ExternalLink size={14} />
            </a>
          )}
        </article>
      )) : <Empty text="暂无发布记录。" />}
    </div>
  );
}

function RunEvents({ events }: { events: RunEvent[] }) {
  return (
    <ol className="event-list">
      {events.length ? events.slice(-10).reverse().map((event, index) => (
        <li key={`${event.state}-${index}`}>
          <strong>{event.state}</strong>
          <span>{event.message}</span>
        </li>
      )) : <Empty text="暂无运行事件。" />}
    </ol>
  );
}

function MemoryBlock({ title, data }: { title: string; data?: Record<string, number> }) {
  const entries = Object.entries(data || {});
  return (
    <article className="memory-block">
      <h3>{title}</h3>
      {entries.length ? entries.map(([key, value]) => (
        <div className="weight-row" key={key}>
          <span>{key}</span>
          <strong>{value}</strong>
        </div>
      )) : <span className="muted">暂无记录</span>}
    </article>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

function clampNumber(value: string, min: number, max: number) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
}

createRoot(document.getElementById("root")!).render(<App />);
