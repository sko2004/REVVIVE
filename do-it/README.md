# Do-It — Starter Template

## Problem statement and outcome

**Problem:** Users often have multi‑step errands that require opening several tabs, copying data, and stitching results together (e.g., planning a weekend trip, gathering vendor quotes, reviewing a bank statement). Choose a real user (such as a busy professional, a small‑business owner, or a student) and a specific errand they currently perform manually. Build an end‑to‑end agent workflow **using the Vayu platform**: keep tasks in **Vayu Vector DB (Qdrant)**, traces in **Vayu Managed PostgreSQL**, call tools via **Vayu Model as a Service**, and deploy via **Vayu Hackathon Container Registry** and **Vayu ML Service** with human‑in‑the‑loop (HITL) approval for risky actions.

**Outcome:** This starter demonstrates an agent graph with at least three tools (HTTP, SQL, Search, Email, Calculator), a planner LLM from the **Vayu Model as a Service** catalog, Postgres trace storage, HITL in a **Streamlit** UI, and a containerised deploy path for judges.

---

## Project layout (steps)

```text
do-it/
├── README.md
├── requirements.txt
├── .env.example                  # Template — copy to .env and fill in values
│
├── 00_vayu_workspace/            # Vayu AI Studio workspace
├── 01_vayu_vector_databases/     # Vayu Vector DB (Qdrant)
├── 02_vayu_postgres/             # Vayu Managed PostgreSQL
├── 03_vayu_model_as_a_service/   # Vayu Model as a Service
├── 04_starter_kit/               # Agent modules + schema
│   ├── agent_tools.py
│   ├── llm_agent.py
│   ├── postgres_db.py
│   ├── qdrant_tasks.py
│   └── db/schema.sql
├── 05_build_app/                 # Streamlit UI + Dockerfile
│   ├── app.py
│   ├── Dockerfile
│   └── .dockerignore
└── 06_deploy/                    # Push image + Vayu ML Service endpoint
```

| Step | Vayu service | Folder | What to open |
|------|--------------|--------|--------------|
| 0 | **Vayu AI Studio Workspace** | `00_vayu_workspace/` | `README.md` — workspace + dependencies |
| 1 | **Vayu Vector DB** | `01_vayu_vector_databases/` | `README.md` — `QDRANT_URL` / `QDRANT_API_KEY` |
| 2 | **Vayu Managed PostgreSQL** | `02_vayu_postgres/` | `README.md` — `DATABASE_URL` |
| 3 | **Vayu Model as a Service** | `03_vayu_model_as_a_service/` | `README.md` — API keys & model IDs |
| 4 | **Agent starter kit** | `04_starter_kit/` | Agent + DB modules |
| 5 | **Vayu chat app (build)** | `05_build_app/` | `app.py`; build/push Docker image |
| 6 | **Vayu ML Service (deploy)** | `06_deploy/` | Deploy image to **Vayu ML Service** — hosted Streamlit endpoint |

---

## Mapping to the Vayu “Do-It — Guided Journey”

| Journey step | How to leverage Vayu ecosystem (detailed) |
|--------------|------------------------------------------|
| **Vayu AI Studio Workspace** | Create your workspace with **Enable Docker in the Workspace** turned on, then clone this repo ([`00_vayu_workspace/`](00_vayu_workspace/)). |
| **Vayu Vector DB** | Task payloads in Qdrant (`do_it_tasks`); set `QDRANT_URL` and `QDRANT_API_KEY` in `do-it/.env`. See [Creating Qdrant guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant). |
| **Vayu Managed PostgreSQL** | Traces + HITL queue via `DATABASE_URL`; `postgres_db.ensure_tables()` on startup. Provision from [Vayu PostgreSQL console](https://ipcloud.tatacommunications.com/cloud/console/vks/#/ms/list/postgres) — click **Create a New PostgreSQL Instance**. |
| **Vayu Model as a Service** | `agent_tools.py` + `llm_agent.py` — `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CHAT_MODEL`. |
| **Agent runtime** | **Tasks** tab (Qdrant only); **Agent** tab (planner + tools); **Approvals** (HITL deletes). |
| **Vayu ML Service (deploy)** | Push image from Step 5, create **ML Service** in AI Studio (port **8501**, Streamlit); set Vector DB + Postgres + MaaS env vars — see [`06_deploy/README.md`](06_deploy/README.md). |

---

## Tech direction / tools (Vayu ecosystem)

| Layer | Vayu / stack choice |
|--------|---------------------|
| UI | **Streamlit** (`05_build_app/app.py`) |
| Task data | **Vayu Vector DB** (Qdrant) |
| Agent memory / audit | **Vayu Managed PostgreSQL** (`DATABASE_URL`) |
| Reasoning | **Vayu Model as a Service** (OpenAI-compatible tools API) |
| Optional upgrade | LangGraph (same Qdrant + Postgres) |
| Container | **`05_build_app/Dockerfile`** → registry → **`06_deploy/`** ML Service |

---

## Quick start

### What this code does

1. **Tasks** — CRUD on **Vayu Vector DB** points (no LLM).
2. **Agent** — **Vayu Model as a Service** tools; each step logged to Postgres.
3. **Approvals** — (HITL) Human-in-the-loop for pending deletes.

### Minimal run

1. **Set up the environment**

   ```bash
   cd do-it
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** in the project root (`do-it/.env`) with your Vayu credentials:

   ```bash
   # Vayu Vector DB (Qdrant) — Step 1
   QDRANT_URL=<your-qdrant-url>
   QDRANT_API_KEY=<your-qdrant-api-key>
   COLLECTION_NAME=do_it_tasks

   # Vayu Managed PostgreSQL — Step 2
   DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME

   # Vayu Model as a Service — Step 3
   OPENAI_API_KEY=<your-maas-api-key>
   OPENAI_BASE_URL=<your-maas-base-url>
   CHAT_MODEL=<your-chat-model>
   ```

   Python scripts load this file automatically via `load_dotenv`. Do not commit `.env` to git.

3. **Launch the agent UI** (`05_build_app/`)

   ```bash
   streamlit run 05_build_app/app.py
   ```

   Open **http://localhost:8501** (or the Studio proxy URL, e.g. `https://<your-workspace-host>/proxy/8501`). Use **Tasks** | **Agent** | **Approvals**.

   **Or build the Docker image** for Step 6 — see [`05_build_app/README.md`](05_build_app/README.md).

---

## Environment variables

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | **Yes** | **Vayu Managed PostgreSQL** |
| `QDRANT_URL` / `QDRANT_API_KEY` | Yes (hosted) | Or `QDRANT_PATH` for local dev |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | Agent tab | **Vayu Model as a Service** |
| `CHAT_MODEL` | Agent tab | From **Vayu Model as a Service** catalog |
| `COLLECTION_NAME` | No | Default task collection name |

---

## Tips

- **`DATABASE_URL` is mandatory** — copy the exact URL from the Vayu PostgreSQL console.
- **Demo HITL** — Ask the agent to delete a task; approve in **Approvals**.
- **Docker networking** — Use external DB/Qdrant hostnames inside the container.
- **Trace storytelling** — Expand the Agent trace for judges.

---

## License

Use and modify for the **Vayu Hackathon** submission unless your team repo specifies otherwise.
