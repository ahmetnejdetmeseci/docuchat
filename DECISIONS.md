# ⚙️ Design & Technical Decisions — DocuChat (Step 1)

This file documents **key technical and architectural decisions** for the Step-1 version of the DocuChat project.

---

## 1. RAG Architecture Simplification
We chose a **TF-IDF based retriever** instead of vector embeddings (FAISS / pgvector) to:
- Avoid heavy dependencies and GPU requirements at this stage
- Keep the pipeline transparent for educational and debugging purposes
- Prepare the structure for a future “embedding swap” without breaking logic

---

## 2. LLM Choice: Gemini 2.5 Flash
- We use Google’s **Gemini 2.5 Flash** due to its speed and low latency.
- The model is configured with `temperature=0.2` and `max_output_tokens=1024`.
- The prompt enforces **context-only** answers — if not found, it must say *“I don’t know.”*

**Prompt Strategy:**
- Strict factuality: answers *only* from provided context  
- If not found → reply exactly `"I don't know."`  
- Encourages concise, citation-grounded responses


## 🔐 Authentication & Login

DocuChat includes a **fully integrated Keycloak authentication system**, but for this version (Step 1), it is **not enforced**.  
The frontend currently runs on a **mock login mode** for easier local testing and faster iteration.

### 🔸 Keycloak Integration
- Keycloak is configured as a standalone container in Docker Compose (`docu_keycloak`).
- Default admin credentials: `admin / admin`
- Realm configuration is automatically imported from `realm-export.json`.
- The service runs at **http://localhost:8081**.
- Frontend and backend are already compatible with Keycloak-based OIDC flow.

### 🔸 Mock Login (Active in Step 1)
- During Step 1 development, the app uses a *mock login provider* instead of real authentication.
- This allows full functionality (upload, chat, citations) **without requiring a Keycloak session**.
- The login page still reflects the actual flow but bypasses Keycloak for simplicity.


> **In summary:**  
> Keycloak is fully integrated but disabled by default.  
> A mock login simulates authentication so the project remains easy to run and test locally.
