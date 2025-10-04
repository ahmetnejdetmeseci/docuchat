Run:
```bash
cp .env.sample .env
docker compose up --build
```
Open http://localhost:8080/


Compose, NGINX, scaffolds.
Upload/index + progress.
Chat API + FE pages + docs.


# Architecture
- NGINX reverse-proxies `/`→frontend, `/api`→django, `/ws`→ASGI websockets.
- Frontend: Vite+React+TS, Ant Design + Tailwind.
- Backend: Django+DRF, Channels (WS).
- Retrieval: TF-IDF stub.
- Auth: Mock in Step1; Keycloak realm provided.
