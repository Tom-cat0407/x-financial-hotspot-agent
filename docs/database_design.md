# Database Design

生产级形态使用 PostgreSQL + pgvector。

启动数据库：

```bash
docker compose up postgres
```

完整建表 SQL：

```text
backend/app/db/schema.sql
```

运行时后端会优先使用 SQLAlchemy 初始化核心表：

1. `pipeline_state`：保存完整运行快照，便于控制台快速读取。
2. `raw_posts`：保存 Mock/Real X 原始帖子。
3. `event_clusters`：保存事件簇、热点分数、置信度和聚类 payload。
4. `artifact_records`：保存评分、事实校验、生成内容、合规报告、配图、审核、发布等流水线产物。
5. `run_events`：保存状态机事件日志。

`schema.sql` 额外定义了更细粒度的生产表，包括：

```text
source_accounts
cluster_posts
atomic_claims
fact_checks
hot_scores
generated_contents
compliance_reports
image_cards
review_queue
publish_records
performance_metrics
strategy_memory
policy_rules
memory_change_log
emergency_events
ab_test_variants
platform_publish_records
```

pgvector 用于：

1. 同事件聚类的语义相似度。
2. 历史事件召回。
3. 生成内容去重。
4. 事实证据和业务记忆检索。
