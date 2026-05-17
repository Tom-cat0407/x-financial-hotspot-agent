# 提交清单

本清单按 `AI_Agent_测试题_X金融热点系统.docx` 的交付物要求整理，用于最终打包前核对。

## 必须提交

1. 完整代码仓库
   - `backend/`
   - `frontend/`
   - `configs/`
   - `data/`
   - `scripts/`
   - `tests/`
   - `Dockerfile`
   - `docker-compose.yml`
   - `requirements.txt`
   - `README.md`

2. 系统架构图与设计文档
   - `docs/architecture.md`
   - `docs/design_notes.md`
   - `docs/scoring_algorithm.md`
   - `docs/prompt_design.md`
   - `docs/agent_framework.md`
   - `docs/compliance_policy.md`
   - `docs/memory_design.md`
   - `docs/database_design.md`
   - `docs/api_mock_design.md`

3. 运行结果与真实样例
   - `outputs/state.json`
   - `outputs/submission_report.html`
   - `outputs/result_showcase.html`
   - `outputs/cards/`
   - `outputs/reports/`

4. Demo 视频
   - `outputs/demo/x_financial_agent_product_demo_3_5min.mp4`

5. 讲解稿与验收核对
   - `docs/final_demo_submission_script.md`
   - `docs/submission_checklist.md`
   - `docs/submission_package_manifest.md`

## 可以提交

- `frontend/dist/`：如果希望评审方不安装前端依赖也能查看构建产物，可以附带。
- `X 平台金融热点内容自动化运营系统方案_最终版.md`：最终方案说明，已与当前代码实现和运行结果保持一致。

## 不要提交

以下内容包含密钥、本地依赖或临时缓存，不应进入 GitHub 仓库或交付压缩包：

- `.env`
- `deepseek.txt`
- `火山方舟.txt`
- `frontend/node_modules/`
- `__pycache__/`
- `.pytest_cache/`
- `.venv/`
- `.audit/`

## 提交前检查

运行：

```bash
python scripts/check_submission.py
```

若脚本提示 `.env`、`deepseek.txt` 或 `火山方舟.txt`，说明当前本地仍保留密钥文件。它们可以留在本机继续调试，但不能进入最终提交包。
