# Memory Design

Demo 使用 `outputs/state.json` 实现本地业务记忆，覆盖：

1. Evidence Memory：原始帖子、事实校验、图片生成记录、发布结果。
2. Atomic Memory：实体、事件类型、合规风险标签。
3. Event Memory：事件簇、是否已生成、是否已发布。
4. Strategy Memory：来源权重、风格权重和 Hashtag 权重。

生产化替换建议：

1. PostgreSQL 保存结构化业务表。
2. pgvector 保存语义相似度向量，用于同事件聚类和内容去重。
3. Redis 保存短期限流、任务锁和发布频控。
