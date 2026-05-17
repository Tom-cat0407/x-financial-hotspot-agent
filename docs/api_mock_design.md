# Mock X API Design

Mock X API 由 `MockXClient` 提供，与真实 X 接口保持同一抽象：

```text
fetch_posts_by_accounts
fetch_posts_by_keywords
fetch_trending_topics
fetch_post_metrics
upload_media
create_post
get_publish_status
```

发布后的表现回收通过 `fetch_post_metrics(mock_post_id)` 完成；`/api/performance/refresh` 会重新拉取已发布 mock 帖子的互动数据，并把 engagement_rate 写入 `performance_metrics` 与策略记忆。

Mock 能力：

1. 从 `data/mock_x_posts.json` 读取 KOL 和财经媒体内容。
2. 从 `data/mock_trending_topics.json` 读取趋势话题。
3. 模拟媒体上传并返回 `mock_media_id`。
4. 模拟发布并返回本地可打开的 `mock_post_url`。
5. 模拟重复内容拒绝。
6. 支持 `/api/mock/simulate-429` 注入 429 状态。
7. 支持对已发布 mock 帖子生成动态互动指标，用于反馈闭环和策略权重更新。
8. 支持 A/B 文案变体分别发布并回收互动指标，按 engagement_rate 标记 winner。
9. 支持 Telegram/Threads 分发适配器；Telegram 可在提供 Bot 凭证后真实发送，Threads 默认使用 mock 分发记录。

当前 mock 数据集包含 30 条帖子，覆盖财经媒体与 16 个 KOL 账号，并通过实体/文本相似度聚类；mock 帖子不再包含 `cluster_key` 字段，避免把聚类结果预写进数据。
