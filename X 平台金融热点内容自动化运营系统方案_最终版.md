# X 平台金融热点内容自动化运营系统方案（最终实现版）

## 一、题目理解与交付边界

本项目面向 `AI_Agent_测试题_X金融热点系统.docx` 中的 X 平台金融热点运营场景，目标是构建一个端到端 AI Agent 系统，完成金融信息采集、热点筛选、同事件聚类、关键词与 Hashtag 增强、原创内容生成、配图生成、合规审核、自动发布/人工审核、互动反馈和策略优化。

题目明确要求“模拟使用 X API，不得使用爬虫违反 ToS”。因此本项目默认使用 `MockXClient` 完成可复现演示，同时保留 `RealXClient` 接口边界，便于获得真实 X API 凭证后切换真实发布。

最终交付边界如下：

1. 默认使用 Mock X API 跑通端到端流程，不使用爬虫。
2. 生成至少 3 条由 Agent 自动生成、审核、配图并发布的 mock 样例链接。
3. 推文必须包含金融免责声明，不生成投资建议、收益承诺或未经证实的结论。
4. 支持人工审核开关；可关闭后进入自动审核发布流程。
5. 支持发布频控、失败重试、异常告警、A/B 测试、多平台分发和反馈闭环。
6. 支持 DeepSeek/OpenAI-compatible Chat Completion 形式的 LLM；未配置 API Key 时保留规则兜底，保证 Demo 可离线运行。

## 二、系统定位

系统名称：

X 平台金融热点内容自动化运营 Agent

系统不是单次文案生成器，而是一个带状态机编排、业务记忆、合规审计、内容实验和反馈优化能力的运营型 Agent 系统。它的价值不只是“写一条推文”，而是把金融热点运营拆成可审计、可复现、可扩展的自动化流水线。

## 三、总体架构

系统采用 FastAPI 后端、React 前端、Mock X API、LLM Client、PostgreSQL/pgvector 可选记忆层和本地 JSON 快照组成。

核心数据流：

```text
Mock X API / Real X API
-> Source Collector
-> Normalizer
-> Entity Extractor
-> Event Clusterer
-> Emergency Priority Agent
-> Hotness Scorer
-> Fact Check RAG
-> Hashtag Enhancer
-> Tweet Generator
-> Compliance Guard
-> Image Card Generator
-> Review Queue
-> Mock/Real Publisher
-> Multi-platform Dispatcher
-> Performance Tracker
-> Strategy Memory
```

当前 Agent 模块：

```text
backend/app/agents/collector_agent.py
backend/app/agents/normalizer_agent.py
backend/app/agents/entity_extractor_agent.py
backend/app/agents/clusterer_agent.py
backend/app/agents/emergency_priority_agent.py
backend/app/agents/rag_fact_check_agent.py
backend/app/agents/hashtag_agent.py
backend/app/agents/tweet_generator_agent.py
backend/app/agents/compliance_guard_agent.py
backend/app/agents/image_card_agent.py
```

共享工具位于：

```text
backend/app/agents/agent_utils.py
backend/app/agents/card_utils.py
```

`basic_agents.py` 仅作为旧导入路径兼容门面，不再保存重复业务逻辑。

Agent 编排声明文件：

```text
backend/app/agents/agent_manifest.yaml
```

## 四、核心能力实现

### 1. 数据采集

配置文件：

```text
configs/media_accounts.yaml
configs/kol_accounts.yaml
configs/keywords.yaml
data/mock_x_posts.json
data/mock_trending_topics.json
```

当前账号配置包含 8 个财经媒体账号和 16 个金融 KOL 账号，KOL 数量满足题目建议的 15-30 个范围。Mock 数据覆盖宏观、加密资产、ETF、科技股、能源、黄金、监管等事件类型。

系统支持账号采集、关键词采集和 Trending Topics 获取。`collector_agent.py` 会返回账号流、关键词流、趋势流和合并流，Pipeline 会真实使用这些数据进入后续处理。

### 2. 热点筛选与聚类

聚类不依赖 mock 数据预置 `cluster_key`。当前使用四因子相似度：

1. 实体 Jaccard 相似度。
2. 文本 token Jaccard 相似度。
3. 轻量词袋向量余弦相似度。
4. 事件类型一致性。

同时加入 6 小时时间窗口约束，避免把相隔太久的相似内容误合并为同一热点。

热度评分由 8 个因子组成：

```text
HotScore =
EngagementVelocity
+ SourceAuthority
+ CrossSourceConfirmation
+ MarketRelevance
+ KeywordMatch
+ TrendBoost
+ TimeDecay
+ EmergencyBoost
```

输出包括：

```text
hot_scores
score_breakdown
event_clusters
Top 热点排序
原始帖子依据
```

前端控制台会展示 Top 热点、热度分数和评分拆解。

### 3. 关键词与 Hashtag 增强

`entity_extractor_agent.py` 负责抽取金融实体，默认使用规则提取，配置 `ENABLE_LLM_NER=true` 后可调用 LLM 增强识别人名、地区、机构、产品等实体。

`hashtag_agent.py` 基于实体、事件类型和 Trending Topics 生成 3-5 个 Hashtag，并支持中英文双语：

```text
#Bitcoin #ETF #Fed #Macro
#比特币 #ETF #美联储 #宏观
```

### 4. 内容生成

`tweet_generator_agent.py` 支持三种风格：

1. 专业速报。
2. 观点评论。
3. 活泼科普。

LLM 通过 `backend/app/clients/llm_client.py` 接入，兼容 DeepSeek/OpenAI-compatible Chat Completion。推文生成会注入结构化事实、热点摘要、实体、Hashtag、语言、风格和合规要求。

强约束：

1. 推文不超过 280 字符。
2. 不复制原帖。
3. 不给出投资建议。
4. 不夸大、不预测收益、不传播未证实传闻。
5. 必须包含 `Not investment advice.` 或 `不构成投资建议。`

未配置 LLM API Key 时，系统降级到规则生成器，保证 Demo 仍可运行。正式演示建议配置 DeepSeek API，以展示更自然的原创文案。

### 5. 合规审核

`compliance_guard_agent.py` 同时支持规则审核和 LLM 合规复核。审核输出包括：

```text
pass / blocked
risk_level
issues
revision_instruction
compliance_report_id
report_path
```

合规报告会写入：

```text
outputs/reports/
```

### 6. 配图生成

`image_card_agent.py` 生成动态金融卡片，默认使用 HTML/CSS 模板 + Playwright 截图，失败时用 Pillow 兜底。

输出规格：

1. 16:9 主图，适合 X 信息流展示。
2. 1:1 方图，作为备选社媒卡片。

图片包含：

1. 热点标题。
2. 关键实体。
3. 来源数、热度分数、事件类型等关键数据。
4. 自定义品牌标识。
5. 中英文/A/B 变体独立文件，避免覆盖。

输出目录：

```text
outputs/cards/
```

### 7. 自动发布与人工审核

系统支持：

1. 人工审核队列。
2. `auto_approve=true` 自动审核发布。
3. `publish_count` 发布数量控制。
4. `max_posts_per_hour` 发布频控。
5. 失败重试。
6. 429 速率限制处理。
7. 异常告警记录。

Mock 发布输出：

```text
publish_records
mock_post_id
mock_post_url
publish_attempts
publish_retry_count
```

真实 X 发布通过 `RealXClient` 保留接口，默认不启用。

## 五、扩展能力实现

### 1. Agent 编排

系统将采集、清洗、实体抽取、聚类、突发事件判断、事实校验、Hashtag、生成、合规、配图拆为独立 Agent 模块，由 `HotspotPipeline` 状态机统一编排。这样比自由多 Agent 对话更适合金融场景，因为每一步都可复现、可审计、可调试。

### 2. 反馈闭环

发布后系统调用：

```text
x_client.fetch_post_metrics(mock_post_id)
```

回收互动数据，计算：

```text
engagement_count
engagement_rate
```

然后更新：

```text
style_weight
hashtag_weight
source_weight
```

当前数据来自 Mock X API，替换为 RealXClient 后可接入真实 X 指标，策略更新逻辑无需重写。

### 3. 多平台分发

系统支持：

1. X Mock 发布。
2. Telegram Bot API 适配器。
3. Threads mock 适配器。

默认 Telegram/Threads 关闭，避免无凭证时失败。配置相关环境变量后，Telegram 可真实发送。

### 4. A/B 测试

系统会为热点生成 A/B 变体，包含英文和中文变体。每个变体会独立完成：

```text
生成 -> 合规 -> 配图 -> 审核 -> 发布 -> 指标回收 -> winner 标记
```

系统按 `experiment_id` 和 `engagement_rate` 标记表现更好的变体。

### 5. 突发事件优先级

`emergency_priority_agent.py` 会识别重大金融事件关键词，例如 halt、SEC、DOJ、rate decision、lawsuit、crash 等，将 `emergency_boost` 注入热度评分，并控制是否需要人工复核。

### 6. RAG / 外部事实校验

默认使用：

```text
data/mock_market_data.json
```

配置：

```text
ENABLE_EXTERNAL_FACT_SOURCES=true
```

后，系统会额外查询 CoinGecko 与 Yahoo Finance，形成多源证据。外部接口失败时自动回退 mock 数据，不影响主流程。

## 六、记忆与数据存储

默认状态快照：

```text
outputs/state.json
```

可选数据库：

```text
PostgreSQL + pgvector
```

数据库设计：

```text
backend/app/db/schema.sql
backend/app/db/models.py
docs/database_design.md
```

记忆内容包括：

1. 原始帖子。
2. 事件簇。
3. 热度分数。
4. 生成内容。
5. 审核队列。
6. 合规报告。
7. 图片卡片。
8. 发布记录。
9. 多平台分发记录。
10. A/B 测试变体。
11. 互动指标。
12. 策略权重。
13. 状态机运行事件。

`MemoryService` 使用线程锁和文件锁，降低并发运行时的 JSON 快照竞争风险。`DatabaseMemoryService.replace_state()` 会同步刷新 PostgreSQL 投影表，保证 JSON 快照和数据库查询结果一致。

## 七、前端控制台

React 前端位于：

```text
frontend/
```

主要页面：

1. 总览。
2. 热点。
3. 审核。
4. 记忆。

导航使用客户端路由，不再使用锚点滚动。页面切换会改变 URL 路径，并支持浏览器前进/后退。

控制台能力：

1. 运行 Demo。
2. 配置发布数量。
3. 打开/关闭自动审核发布。
4. 展示 Top 热点。
5. 展示审核队列。
6. 展示 Mock 发布记录。
7. 展示 A/B 测试结果。
8. 展示多平台分发结果。
9. 展示策略记忆。
10. 手动刷新反馈指标。

## 八、当前运行结果

当前 `outputs/state.json` 中的 Demo 结果如下：

```text
raw_posts: 30
event_clusters: 11
hot_scores: 11
generated_contents: 8
review_queue: 8
publish_records: 6
image_cards: 8
platform_dispatches: 12
ab_test_variants: 8
performance_metrics: 6
run_events: 36
```

可视化验收报告：

```text
outputs/submission_report.html
outputs/result_showcase.html
```

Demo 视频：

```text
outputs/demo/x_financial_agent_product_demo_3_5min.mp4
```

## 九、部署与运行

本地后端：

```bash
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

运行 Demo：

```bash
curl "http://127.0.0.1:8000/api/demo/run?auto_approve=true&publish_count=6"
```

前端：

```bash
cd frontend
npm install
npm run dev
```

生产级依赖：

```bash
docker compose up --build
```

## 十、提交说明

建议提交：

```text
backend/
frontend/
configs/
data/
docs/
outputs/
scripts/
tests/
Dockerfile
docker-compose.yml
README.md
requirements.txt
.env.example
```

不要提交：

```text
.env
deepseek.txt
火山方舟.txt
frontend/node_modules/
__pycache__/
.pytest_cache/
.venv/
.audit/
```

提交前运行：

```bash
python scripts/check_submission.py
```

如果脚本提示 `.env`、`deepseek.txt`、`火山方舟.txt`，说明本地仍保留密钥文件。它们可以用于本机调试，但不能进入 GitHub 或交付压缩包。

## 十一、与测试题要求的对应关系

| 测试题要求 | 当前实现 |
|---|---|
| 监控 KOL 和财经媒体 | 16 个 KOL + 8 个媒体账号配置，Mock X API 采集 |
| 热点筛选 | 8 因子 HotScore + 同事件聚类 + Top N 输出 |
| 关键词与 Hashtag | 实体抽取 + Trending Topics + 中英 Hashtag |
| LLM 原创推文 | DeepSeek/OpenAI-compatible LLM + 规则兜底 |
| 金融合规 | 免责声明强制加入 + 规则/LLM 合规审核 |
| 配图生成 | HTML/CSS + Playwright 卡片，输出 16:9 和 1:1 |
| 自动发布与人工审核 | 审核队列 + auto approve + Mock 发布 |
| 发布频控与重试 | max_posts_per_hour + retry + 429 处理 |
| 异常告警 | AlertClient + run_events + Webhook 可选 |
| Agent 框架理解 | 10 个 Agent 模块 + 状态机编排 + manifest |
| 反馈闭环 | fetch metrics -> engagement_rate -> strategy memory |
| 多平台分发 | Telegram adapter + Threads mock adapter |
| A/B 测试 | 中英文 A/B 变体 + 指标回收 + winner 标记 |
| 突发事件优先级 | emergency_boost 注入评分 |
| RAG 事实校验 | Mock market data + CoinGecko/Yahoo 可选 |

## 十二、当前限制

1. 默认发布链接为 Mock X API 链接，不是真实 X 链接；这是为了遵守题目“模拟使用 X API”的边界。
2. 外部事实源默认关闭，避免无网络或限流影响 Demo，可通过环境变量开启。
3. LLM 未配置时会降级到规则生成，正式演示建议配置 DeepSeek API。
4. Telegram 和 Threads 默认关闭；Telegram 需配置 Bot Token 与 Chat ID，Threads 当前为 mock 适配器。
5. Demo 视频语音由本地 TTS 生成；TTS 服务本身不是测试题评分项，重点在系统端到端流程和结果展示。
