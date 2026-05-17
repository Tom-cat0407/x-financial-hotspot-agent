# Design Notes

本项目把方案收敛为可在本地复现、可浏览器演示的端到端 Demo。核心边界如下：

1. 默认使用 Mock X API，不使用爬虫，不绕过 X 平台规则。
2. 保留 `RealXClient` 接口，但真实发布必须通过 `.env` 显式启用并提供凭证。
3. 使用状态机式流水线替代自由发散的多 Agent 对话，方便调试、审计和演示。
4. Demo 支持 PostgreSQL + pgvector 作为主记忆，也保留 JSON 快照兜底。
5. 金融合规优先，所有内容都强制包含 `Not investment advice.` 或 `不构成投资建议。`，并写入合规报告。
6. 推文生成和合规复核接入兼容 Chat Completion 的 LLM；未配置 API key 时降级为规则生成。
7. 聚类不依赖 mock 数据预置 key，而是综合实体重合、文本 token、轻量向量余弦和 6 小时时间窗口。

端到端状态流：

```text
collecting -> normalizing -> extracting_entities -> clustering -> emergency_classifying
-> scoring -> fact_checking -> hashtag_generating -> tweet_generating
-> compliance_checking -> image_generating -> waiting_review -> publishing
-> performance_tracking -> memory_updating
```

## Implemented Module Files

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

这些模块现在是流水线的实际导入口。共享规则、相似度工具和状态报告工具位于 `agent_utils.py`；卡片渲染工具位于 `card_utils.py`；`basic_agents.py` 仅作为向后兼容门面 re-export，不再保留重复业务实现。

## Feedback Loop

反馈闭环已经从固定模拟值升级为架构级闭环：

1. `MockXClient.create_post()` 生成本地 mock 发布记录。
2. `HotspotPipeline._performance_metric()` 调用 `x_client.fetch_post_metrics(mock_post_id)` 回收互动数据。
3. 系统计算 `engagement_count` 和 `engagement_rate`，并写入 `performance_metrics`。
4. `MemoryService.update_strategy_after_publish()` 使用 `engagement_rate` 更新 `style_weight`、`hashtag_weight` 和 `source_weight`。
5. `POST /api/performance/refresh` 可手动重新回收已发布内容表现，前端控制台提供“刷新反馈”按钮。

当前指标数据来自 `MockXClient`，用于满足测试题“模拟使用 X API”的边界。未来替换为 `RealXClient.fetch_post_metrics()` 后，策略更新逻辑无需改动即可使用真实 X 指标。

## Bonus Features

题目中的扩展能力当前对应如下：

1. Agent 协作理解：系统把采集、清洗、实体抽取、聚类、突发事件、事实校验、Hashtag、生成、合规、配图拆成独立 Agent 模块，并由 `HotspotPipeline` 状态机编排。
2. 反馈闭环：已实现发布后指标回收、`performance_metrics` 存储和策略权重更新。
3. 多平台同步分发：已实现 Telegram Bot API 适配器和 Threads mock 适配器。默认关闭；配置 `TELEGRAM_ENABLED=true`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 后会真实调用 Telegram；Threads 默认以 mock 链路展示分发结果。
4. A/B 测试：默认开启。每个入选热点会分别生成英文 A/B 与中文 A/B 变体，分别配图、审核、Mock 发布、回收互动指标，并按语言维度的 `experiment_id` 和 `engagement_rate` 标记 winner。
5. 突发事件优先级：`emergency_priority_agent.py` 识别重大金融事件关键词，将 `emergency_boost` 注入热度评分，并控制自动发布/人审标记。
6. RAG/事实校验：默认使用 mock market data；设置 `ENABLE_EXTERNAL_FACT_SOURCES=true` 后会额外查询 CoinGecko 和 Yahoo Finance，失败时自动回退 mock 数据。

## Engineering Hardening

本轮工程化补强包括：

1. `collector_agent.py` 返回账号流、关键词流和合并流，流水线真实使用 `keyword_posts`。
2. 事实校验通过 `MockFinanceDataClient` 查询 mock 市场数据，不再在 Pipeline 中直接读文件。
3. `MemoryService` 使用线程锁和可选 `filelock`，降低手动运行与调度并发写 JSON 快照时的数据竞争。
4. `approve_and_publish` 使用公共 `replace_state()` 接口，不再直接调用私有 `_write()`。
5. Mock 数据和测试数据已移除旧 `cluster_key` 字段，避免误导评审者。
6. 中文生成模块使用 ASCII-safe Unicode escape 编写中文字符串，避免 Windows 终端编码导致源码污染。
7. `DatabaseMemoryService.replace_state()` 会同步刷新 PostgreSQL 投影表，避免 JSON 快照与查询表不一致。
8. 边界测试覆盖空输入、单帖子聚类、LLM 超长输出截断、中文免责声明、发布表现指标回收。
9. `Settings` 使用 Pydantic `BaseModel` 与验证器，集中约束整数配置和 URL 规范化。
10. React 控制台支持发布数量、自动审核发布和反馈刷新参数，演示时不需要手写 curl。
11. 配图生成同时输出 16:9 主卡片和 1:1 方图备选卡片，满足 X 常见展示规格。
12. 发布链路已接入 `AlertClient`，在发布失败、触发 429 重试和频控拦截时记录流水线事件，并可通过 `ALERT_WEBHOOK_URL` 推送外部 Webhook 告警。
