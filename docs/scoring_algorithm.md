# Scoring Algorithm

热度评分由 `backend/app/services/scoring_service.py` 实现，输出 `hot_score` 和 `score_breakdown`。

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

## Factors

1. `EngagementVelocity`：按点赞、转发、评论、引用、浏览量计算加权互动量，并除以帖子年龄，近似得到“每小时互动速度”。这比单纯使用总互动量更贴近题目要求的“互动量增长率”。
2. `SourceAuthority`：财经媒体和官方来源高于普通 KOL。
3. `CrossSourceConfirmation`：独立来源越多，分数越高。
4. `MarketRelevance`：按命中金融关键词数量连续加权，不再只有“命中/未命中”两档。
5. `KeywordMatch`：统计 Fed、CPI、ETF、Bitcoin、SEC、earnings 等金融关键词与实体命中数量。
6. `TrendBoost`：结合 Mock Trending Topics 的话题名称和 volume 计算趋势加成。
7. `TimeDecay`：使用 `5 / (1 + hours / 2)` 的连续倒数衰减，避免 5 小时后硬归零。
8. `EmergencyBoost`：重大金融事件最高额外加 15 分。

## Notes

Mock 数据只有单点互动快照，因此 `EngagementVelocity` 使用“加权互动量 / 内容年龄”近似增长速度。若未来接入真实 X API 的历史指标快照，可以替换为 `delta_engagement / delta_time`，评分接口无需改动。
