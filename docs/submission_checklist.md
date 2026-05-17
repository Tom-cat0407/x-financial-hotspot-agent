# Submission Checklist

本文档按 `AI_Agent_测试题_X金融热点系统.docx` 的功能点核对当前提交状态。

## 核心功能

| 题目要求 | 状态 | 证据位置 |
|---|---|---|
| 监控财经媒体、KOL、关键词和趋势话题 | 已完成 | `configs/*.yaml`, `data/mock_x_posts.json`, `outputs/state.json` |
| 5-10 分钟实时采集能力 | 已完成 | `backend/app/main.py`, APScheduler 配置 |
| 热度模型包含互动、来源权重、时间衰减、关键词匹配 | 已完成 | `backend/app/services/scoring_service.py` |
| 同事件去重聚类 | 已完成 | `backend/app/agents/clusterer_agent.py` |
| 输出 Top N、热度分数和原始依据 | 已完成 | `outputs/state.json`, `outputs/result_showcase.html` |
| 实体抽取与 Hashtag 增强 | 已完成 | `backend/app/agents/entity_extractor_agent.py`, `backend/app/agents/hashtag_agent.py` |
| 中英文双语内容 | 已完成 | `outputs/state.json` |
| LLM 原创推文生成与规则兜底 | 已完成 | `backend/app/clients/llm_client.py`, `backend/app/agents/tweet_generator_agent.py` |
| 280 字符限制、免责声明、金融合规 | 已完成 | `backend/app/agents/compliance_guard_agent.py`, `outputs/reports/` |
| 风格可配置 | 已完成 | `configs/brand_voice.yaml`, `tweet_generator_agent.py` |
| 动态配图模板 | 已完成 | `backend/app/agents/card_utils.py`, `outputs/cards/` |
| 16:9 与 1:1 图片规格 | 已完成 | `outputs/cards/` |
| 自动发布与人工审核 | 已完成 | `backend/app/workflows/hotspot_pipeline.py`, React 控制台 |
| 频率控制、失败重试、异常告警接口 | 已完成 | `hotspot_pipeline.py`, `alert_client.py`, `mock_x_client.py` |

## 扩展能力

| 能力 | 状态 | 证据位置 |
|---|---|---|
| Agent 编排 | 已完成 | `backend/app/agents/`, `backend/app/agents/agent_manifest.yaml` |
| 反馈闭环 | 已完成 | `performance_metrics`, `strategy_memory` |
| 多平台分发 | 已完成 | `telegram_client.py`, `threads_client.py`, `platform_dispatches` |
| A/B 测试 | 已完成 | `ab_test_variants`, `hotspot_pipeline.py` |
| 突发事件优先级 | 已完成 | `emergency_priority_agent.py` |
| 外部事实源校验 | 已完成 | `finance_data_client.py`, `rag_fact_check_agent.py` |

## 交付物

| 交付物 | 状态 | 位置 |
|---|---|---|
| 完整代码仓库 | 已完成 | 项目根目录 |
| 系统架构图 | 已完成 | `docs/architecture.md` |
| README | 已完成 | `README.md` |
| Demo 视频 3-5 分钟 | 已完成 | `outputs/demo/x_financial_agent_product_demo_3_5min.mp4` |
| 设计思路文档 | 已完成 | `docs/scoring_algorithm.md`, `docs/prompt_design.md`, `docs/agent_framework.md`, `docs/compliance_policy.md` |
| 至少 3 条推文样例链接 | 已完成 | `outputs/state.json`, `outputs/result_showcase.html` |

## 提交前检查

```bash
python scripts/check_submission.py
pytest -q
cd frontend && npm run build
```
