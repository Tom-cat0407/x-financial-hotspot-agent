# X 平台金融热点内容自动化运营系统

这是一个面向 `AI_Agent_测试题_X金融热点系统.docx` 的端到端 AI Agent Demo。系统模拟 X 平台金融热点运营流程，从数据采集、热点聚类、热度评分、事实校验、Hashtag 增强、LLM 推文生成、金融合规审核、动态配图、审核发布，到 A/B 测试、多平台分发和反馈闭环，形成一条可运行、可审计、可演示的完整链路。

默认使用 Mock X API，不爬虫、不绕过平台规则。系统保留 `RealXClient`、Telegram、Threads、CoinGecko、Yahoo Finance 等适配接口，拿到真实凭证后可以按配置切换。

## 一、快速启动

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

打开：

```text
http://localhost:8000
```

点击前端控制台中的“运行 Demo”，系统会执行端到端流程，并生成：

- `outputs/state.json`
- `outputs/submission_report.html`
- `outputs/cards/*.png`
- `outputs/reports/*.json`

## 二、DeepSeek / LLM 配置

系统使用兼容 Chat Completion 的接口，已适配 DeepSeek：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_RETRY_BASE_SECONDS=1.5
LLM_REASONING_EFFORT=
LLM_THINKING_ENABLED=false
ENABLE_LLM_NER=false
LLM_NER_MAX_POSTS_PER_RUN=8
```

说明：

- 配置 API Key 后，推文生成和合规复核会真实调用 LLM。
- 未配置 API Key 时，系统会自动降级为规则生成、规则合规和规则实体抽取，保证离线 Demo 可运行。
- `ENABLE_LLM_NER=true` 可启用 LLM 增强实体抽取，用于识别人名、机构、国家地区等规则难覆盖实体。
- 批量 Demo 不建议默认开启 thinking 模式，否则运行时间会明显变长。

## 三、生产级启动

启动 PostgreSQL/pgvector 与后端：

```bash
docker compose up --build
```

前端开发模式：

```bash
cd frontend
npm install
npm run dev
```

React/Vite 开发服务会代理 `/api`、`/outputs`、`/mock_x` 到 `http://127.0.0.1:8000`。

## 四、核心 API

```text
GET  /health
POST /api/demo/run
GET  /api/state
GET  /api/hotspots
GET  /api/review-queue
GET  /api/published
POST /api/review/{content_id}/approve
GET  /api/platform-dispatches
GET  /api/ab-tests
POST /api/performance/refresh
POST /api/mock/simulate-429
GET  /mock_x/posts/{mock_post_id}
```

命令行运行 Demo：

```bash
curl -X POST "http://localhost:8000/api/demo/run?auto_approve=true&publish_count=3"
```

## 五、目录结构

```text
backend/app/
  agents/                  10 个业务 Agent
  agents/agent_manifest.yaml
  clients/                 MockXClient、RealXClient、LLM、Telegram、Threads、FinanceData
  core/                    配置与路径
  db/                      SQLAlchemy 模型与 pgvector schema
  services/                记忆服务、数据库记忆、热度评分
  workflows/               HotspotPipeline 状态机编排
frontend/                  React/Vite 运营控制台
configs/                   关键词、账号、平台配置
data/                      Mock X 帖子、趋势话题、市场数据
docs/                      架构、评分、Prompt、合规、记忆、Demo 文档
outputs/                   运行生成的 state、cards、reports、HTML 验收报告
tests/                     单元测试与端到端测试
```

## 六、测试题要求对应

1. 数据采集：`MockXClient` 从财经媒体、KOL、关键词和趋势话题采集 mock 数据。
2. 热点筛选：同事件聚类，输出 Top N、HotScore 和 `score_breakdown`。
3. Hashtag 增强：结合实体、事件类型和 Mock Trending Topics 生成 3-5 个标签，支持中英文。
4. 内容生成：支持 LLM 原创生成、规则兜底、中英文推文、280 字符限制和免责声明。
5. 合规审核：规则 + LLM 复核，拦截投资建议、收益承诺、价格预测和夸大表达。
6. 配图生成：HTML/CSS 动态卡片 + Playwright 截图，失败时 Pillow 兜底；支持 16:9 与 1:1。
7. 发布审核：审核队列、auto approve 开关、Mock X 发布记录、频控保护和失败重试。
8. 反馈闭环：回收 mock 互动指标，反向更新 style/source/hashtag 策略权重。
9. 多平台分发：Telegram Bot API 适配器 + Threads mock 适配器。
10. A/B 测试：英文 A/B + 中文 A/B 变体分别生成、发布、回收指标并标记 winner。
11. 突发事件优先级：重大监管、停牌、宏观事件触发 emergency boost。
12. RAG/事实校验：默认 MockFinanceDataClient，可选 CoinGecko/Yahoo Finance 外部源。

## 七、扩展能力覆盖

| 扩展能力 | 当前实现 |
|---|---|
| Agent 框架 / 多 Agent 协作 | 10 个独立 Agent 模块 + `agent_manifest.yaml` + 状态机编排 |
| 反馈闭环 | `fetch_post_metrics -> engagement_rate -> strategy_memory` |
| 多平台同步分发 | Telegram Bot API + Threads mock |
| A/B 测试机制 | 英文 A/B 与中文 A/B，按互动率标记 winner |
| 突发事件优先级 | `emergency_priority_agent.py` 注入评分加成和审核标记 |
| RAG 事实校验 | Mock 数据 + 可选 CoinGecko/Yahoo Finance |

## 八、测试与构建

```bash
pytest -q
cd frontend
npm run build
```

最近一次验证结果：

```text
30 passed
vite build passed
```

## 九、Demo 与报告

运行 Demo 后可查看：

```text
outputs/state.json
outputs/submission_report.html
outputs/result_showcase.html
outputs/cards/
outputs/reports/
outputs/demo/x_financial_agent_product_demo_3_5min.mp4
```

提交说明和核对清单：

```text
docs/final_demo_submission_script.md
docs/submission_checklist.md
```

## 十、提交安全检查

本地 `.env` 和 `deepseek.txt` 可能包含真实 DeepSeek API Key。提交代码仓库或压缩包前必须排除这两个文件，或者将真实 key 替换成占位符。

可提交：

```text
.env.example
```

不要提交：

```text
.env
deepseek.txt
```

提交前可运行：

```bash
python scripts/check_submission.py
```

如果脚本提示发现密钥，请删除或清空对应文件中的真实 Key。

## 十一、真实 X API 边界

默认配置：

```env
X_MODE=mock
ENABLE_REAL_PUBLISH=false
REVIEW_REQUIRED=true
MAX_POSTS_PER_HOUR=6
PUBLIC_BASE_URL=http://localhost:8000
```

真实发布不是默认交付项。若具备有效 X API 写权限，可通过 `.env` 设置 `X_MODE=real` 并开启 `ENABLE_REAL_PUBLISH=true`。金融内容真实发布仍建议保留人工审核。
