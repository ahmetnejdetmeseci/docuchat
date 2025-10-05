Run:
```bash
cp .env.sample .env
docker compose up --build
```
Open http://localhost:8080/

# 🧠 DocuChat – Document-Based Q&A (Step 1)

DocuChat is a **Retrieval-Augmented Generation (RAG)** app: upload documents, ask questions, get concise answers **with citations**.  
This Step-1 MVP uses **Django + React + Docker** and integrates **Gemini 2.5 Flash** for answer generation.

---

## ✨ Features

- 📤 **Upload & index** PDFs/TXT into chunked storage (page-aware)
- 🔎 **TF-IDF retrieval** (simple, fast; embeddings planned for Step 2)
- 🤖 **Gemini 2.5 Flash** answers strictly from provided context
- 📑 **Citations**: `doc`, `page`, `chunk_id`, `quote`, `snippet`
- 🧩 **Dockerized stack**: Postgres, Redis, NGINX, Backend, Frontend
- 🔐 **Auth mocked** for Step 1 (Keycloak container prepared)

---

## 🏗 Tech Stack

- **Frontend**: React + TypeScript + Ant Design  
- **Backend**: Django REST Framework (Channels-ready)  
- **Search**: TF-IDF (scikit-learn) → (Step 2: embeddings)  
- **DB**: PostgreSQL 15-alpine  
- **Cache/Broker**: Redis 7  
- **LLM**: Google **Gemini 2.5 Flash**  
- **Infra**: Docker Compose + **NGINX** reverse proxy

---

Compose, NGINX, scaffolds.
Upload/index + progress.
Chat API + FE pages + docs.


# Architecture
- NGINX reverse-proxies `/`→frontend, `/api`→django, `/ws`→ASGI websockets.
- Frontend: Vite+React+TS, Ant Design + Tailwind.
- Backend: Django+DRF, Channels (WS).
- Retrieval: TF-IDF stub.
- Auth: Mock in Step1; Keycloak realm provided.



# API
- POST /api/upload  (multipart) → {status, files}
- POST /api/chat/ask → {answer, citations[]}
- GET  /api/health
WS: /ws/progress

## 📦 Repository Structure
.
├── backend/
│ ├── apps/
│ │ ├── uploads/ # upload + chunk models/APIs
│ │ └── rag/ # retrieval + LLM glue
│ ├── manage.py
│ └── settings.py
├── frontend/
│ └── src/ # pages (Uploads/Chat), lib/api
├── infra/
│ └── nginx/nginx.conf
├── docker-compose.yml
├── .env.sample
├── README.md
└── DECISIONS.md


> Prereq: **Docker** & **Docker Compose** installed.

1. **Clone**
   ```bash
   git clone https://github.com/<your-username>/docuchat.git
   cd docuchat



   cp .env.sample .env
