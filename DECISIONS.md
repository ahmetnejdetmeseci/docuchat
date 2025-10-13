# DECISIONS
- Bypass auth via X-Tenant header; per-tenant isolation at DB level.
- Hybrid TF-IDF + BM25 retrieval; simple re-ranking via sentence scoring.
- Agent streams plan status via Channels/Redis WS. Report saved as Markdown.
- Single-file SPA to remove Node build requirements.
