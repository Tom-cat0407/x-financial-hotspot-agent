# X 平台金融热点内容自动化运营系统 - 提交说明

本文档用于随代码仓库一起提交，说明最终交付物位置和本次运行结果。

## 交付物清单

| 交付物 | 文件位置 | 说明 |
|---|---|---|
| 完整代码仓库 | 项目根目录 | FastAPI 后端、React/Vite 前端、Agent 模块、配置、测试与脚本 |
| README | `README.md` | 启动方式、配置说明、API 列表、验收点对应 |
| 系统架构文档 | `docs/architecture.md` | 数据流、Agent 编排、记忆层和发布链路 |
| 设计文档 | `docs/scoring_algorithm.md`, `docs/prompt_design.md`, `docs/agent_framework.md`, `docs/compliance_policy.md`, `docs/memory_design.md` | 热度算法、Prompt、Agent 编排、合规与记忆设计 |
| Demo 视频 | `outputs/demo/x_financial_agent_product_demo_3_5min.mp4` | 约 4 分 11 秒，符合 3-5 分钟要求 |
| HTML 验收报告 | `outputs/submission_report.html` | 从 `outputs/state.json` 自动生成 |
| 结果展示页 | `outputs/result_showcase.html` | 展示本次运行的热点、内容、发布、A/B 和反馈指标 |
| 运行结果 JSON | `outputs/state.json` | 完整端到端运行状态与证据 |
| 动态配图 | `outputs/cards/` | 16:9 与 1:1 卡片图片 |
| 合规报告 | `outputs/reports/` | 每条内容的合规审核结果 |

## 本次运行结果

| 指标 | 结果 |
|---|---:|
| 原始采集帖子 | 30 |
| 事件簇 | 11 |
| 生成内容 | 8 |
| Mock 发布记录 | 6 |
| A/B 变体 | 8 |
| 图片卡片 | 8 组 |
| 多平台分发记录 | 12 |
| 互动反馈指标 | 6 |
| 自动化测试 | 30 passed |

## 能力覆盖

系统覆盖测试题要求的核心链路：

1. 数据采集：媒体账号、KOL 账号、关键词和趋势话题采集，保留原始依据。
2. 热点筛选：同事件聚类，输出 Top N、热度分数和 `score_breakdown`。
3. Hashtag 增强：实体、事件类型和 Trending Topics 融合，支持中英文标签。
4. 内容生成：LLM 原创生成与规则兜底，包含 280 字符限制、免责声明和风格配置。
5. 配图生成：动态卡片模板输出 16:9 与 1:1 图片，包含标题、关键数据、评分图表和品牌标识。
6. 审核与发布：审核队列、自动审批开关、Mock X 发布链接、频控、失败重试和告警接口。
7. 运营闭环：回收互动指标，更新文案风格、来源和 Hashtag 的策略权重。
8. 扩展能力：A/B 对比、多平台分发、突发事件优先级、外部事实源校验和 Agent Manifest。

## 建议评审顺序

1. 打开 `README.md` 查看启动和配置说明。
2. 打开 `outputs/result_showcase.html` 查看本次运行结果。
3. 打开 `outputs/demo/x_financial_agent_product_demo_3_5min.mp4` 查看产品演示视频。
4. 查看 `docs/architecture.md` 和 `docs/scoring_algorithm.md` 理解架构与热度模型。
5. 运行 `pytest -q` 和前端 `npm run build` 复核工程质量。

## 复现命令

启动后端：

```bash
uvicorn backend.app.main:app --reload --port 8000
```

命令行运行完整 Demo：

```bash
python -c "from backend.app.clients.mock_x_client import MockXClient; from backend.app.services.memory_service import MemoryService; from backend.app.workflows.hotspot_pipeline import HotspotPipeline; state=HotspotPipeline(MockXClient(), MemoryService()).run(top_n=10, publish_count=2, auto_approve=True, reset_state=True); print(len(state['generated_contents']), len(state['publish_records']))"
```

重新生成 HTML 验收报告：

```bash
python scripts/generate_result_report.py
```

验证：

```bash
pytest -q
cd frontend && npm run build
```
