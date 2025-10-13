# DocuChat — Step 2 (Multi-tenant, Agent, Hybrid Retrieval) — Keycloak Bypass

This package is a drop-in runnable Step-2 version with multi-tenant isolation, hybrid retrieval (TF-IDF+BM25), a simple agent that streams step updates over WebSockets, and basic caching — without Keycloak (bypass via X-Tenant header).

## Run
1. `cp .env.sample .env` and optionally set `GEMINI_API_KEY` to use Gemini (if blank, Fake LLM is used).
2. `docker compose up --build`
3. Open http://localhost:8080. Tenant defaults to `demo`. A small seed dataset is auto-created on first run.

## API (quick)
- `GET /api/health` → `{ "ok": true }`
- `POST /api/uploads/upload` (multipart) — headers: `X-Tenant`
- `GET /api/uploads/list` — headers: `X-Tenant`
- `DELETE /api/uploads/<id>` — headers: `X-Tenant`
- `POST /api/chat/ask` — body: `{ "q": "your question" }`, headers: `X-Tenant`
- `POST /api/agent/tasks` — body: `{ "topic": "..." }`, headers: `X-Tenant`
- `GET /api/agent/tasks/<id>` — headers: `X-Tenant`
- WebSocket: `ws://localhost:8080/ws/agent/<group>/`

## Notes
- No Keycloak/OIDC here. Replace TenantMiddleware with real OIDC verification when needed.
- `init_demo` seeds two tiny docs (including python.md with python version=3.11.x).
