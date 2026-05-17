# Prompt Design

当前实现已经加入 兼容 Chat Completion 的 LLM 客户端：

```text
backend/app/clients/llm_client.py
```

可通过 `.env` 配置 DeepSeek 或兼容网关：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_API_KEY=your_key_here
LLM_REASONING_EFFORT=
LLM_THINKING_ENABLED=false
```

如果未配置 `LLM_API_KEY`，系统会降级到规则生成器，保证 Demo 可离线运行；配置后，推文生成与合规复核会真实调用 LLM。

Prompt 拆成以下几类：

1. 事实摘要 Prompt：只允许使用输入中的事实和事实校验结果。
2. 推文生成 Prompt：限制 280 字符、必须包含免责声明、必须包含 3-5 个 Hashtag。
3. 合规复核 Prompt：检查投资建议、收益承诺、价格预测、夸大措辞和未证实事实。
4. NER Prompt：抽取公司、股票代码、加密资产、ETF/基金、人物、机构、国家/地区、宏观指标、产品、事件和大宗商品，并返回事件类型。
5. 重写 Prompt：只根据合规报告修复风险措辞，不新增事实。

关键围栏：

```text
Do not provide investment advice.
Do not promise returns.
Do not make price predictions.
Do not present unverified claims as confirmed facts.
Always include: Not investment advice.
```

## Actual Tweet Prompt

```text
You are a financial social media editor. Generate original X posts that are concise, factual, compliant, and never investment advice.

Create one X post from this JSON payload.
Return only the post text, no markdown.

Rules:
- 280 characters or fewer.
- Include 3 to 5 provided hashtags.
- Include "Not investment advice." for English or "不构成投资建议。" for Chinese.
- Do not promise returns, give buy/sell instructions, or make price predictions.
- If verification_status is unverified or partially_verified, attribute cautiously.
```

## Actual Compliance Prompt

```text
You are a strict financial compliance reviewer for public X posts.

Review the content for financial compliance.
Return strict JSON with keys:
pass(boolean), risk_level(low|medium|high|blocked), issues(array), revision_instruction(string).

Rules:
- Block investment advice, return promises, price predictions, hype, or confirmed wording for unverified claims.
- Medium or above requires human review.
```

## Actual NER Prompt

```text
You extract structured financial entities and event types from short X posts.

Return strict JSON for this financial post.

Schema:
{
  "entities": ["canonical entity names"],
  "event_type": "crypto_etf|central_bank|earnings|regulation|macro_data|commodity|market_move",
  "entity_types": {"entity": "company|ticker|crypto_asset|etf|person|institution|country_region|macro_indicator|product|event|commodity|other"}
}

Rules:
- Use canonical names when obvious, e.g. BTC -> Bitcoin, NVDA -> Nvidia.
- Include companies, tickers, crypto assets, ETFs/funds, people, institutions, countries/regions, macro indicators, products, events, and commodities.
- Return JSON only.
```

`ENABLE_LLM_NER=false` by default. When enabled with an LLM key, the rule-based extractor is augmented by this NER prompt; when disabled or when the LLM fails, the local rule extractor remains the fallback.
