# Agent Framework Notes

The test asks for Claude Code / multi-agent understanding as a bonus item. This project implements that idea as scoped Agent modules coordinated by a deterministic state machine.

Why state-machine orchestration:

1. Financial content needs repeatable execution, not free-form agent chatter.
2. Every stage writes auditable artifacts into memory.
3. Compliance and review gates are explicit.
4. Individual Agent modules remain small enough to map to Claude Code worker responsibilities.

The machine-readable manifest is:

```text
backend/app/agents/agent_manifest.yaml
```

Current Agent roles:

```text
collector -> normalizer -> entity_extractor -> clusterer -> emergency_priority
-> rag_fact_check -> hashtag -> tweet_generator -> compliance_guard -> image_card
```

`HotspotPipeline` is the coordinator. It decides ordering, persistence, A/B publication, feedback refresh, and multi-platform dispatch. This keeps the implementation compatible with local/offline Demo requirements while still showing clear multi-agent decomposition.
