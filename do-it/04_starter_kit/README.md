# Step 4 — Agent starter kit

**Do-It** › **Agent starter kit** · `04_starter_kit/`

| | |
|---|---|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡** | [Step 5 — Streamlit app & deploy](../05_build_app/) |

Python modules for **Vayu Vector DB** tasks, **Postgres** traces, **Vayu Model as a Service** tools, and the planner loop — used by `05_build_app/app.py`.

---

## Prerequisites

| Step | Vayu service / folder |
|------|------------------------|
| 0 | [Vayu AI Studio Workspace](../00_vayu_workspace/) |
| 1 | [Vayu Vector DB](../01_vayu_vector_databases/) — `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME` |
| 2 | [Vayu Managed PostgreSQL](../02_vayu_postgres/) — `DATABASE_URL` |
| 3 | [Vayu Model as a Service](../03_vayu_model_as_a_service/) — `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CHAT_MODEL` |

Install dependencies:

![Setting up venv and installing dependencies](../assets/install.png)

```bash
cd do-it
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with credentials from Steps 1–3
```

**Required environment variables** (set in `do-it/.env`):

```bash
# QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME,
# DATABASE_URL, OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL
```

---

## Folder Contents

| File | Role |
|------|------|
| `qdrant_tasks.py` | Task CRUD + search on **Vayu Vector DB** |
| `postgres_db.py` | Runs, steps, HITL pending queue |
| `agent_tools.py` | **Vayu Model as a Service** tool wrappers |
| `llm_agent.py` | Planning loop + trace logging |
| `db/schema.sql` | Optional DDL mirror for Postgres |

---

## How it fits together

| Tab (in app) | Backend |
|--------------|---------|
| **Tasks** | `qdrant_tasks` only (no LLM) |
| **Agent** | `llm_agent` + **Vayu Model as a Service** tools → each step in Postgres |
| **Approvals** | HITL: `queue_task_delete` → approve → delete in Qdrant |

Tools include: `list_tasks`, `add_task`, `set_done`, `search_tasks`, `queue_task_delete`, and related helpers (see `agent_tools.py`).

---

## Smoke test: run locally in your workspace

Before moving on to build and deploy, **smoke test your agent locally** to ensure all integrations (Qdrant, Postgres, Model API) are working.

**Environment variable example** — replace placeholders with your provisioned values (never commit real secrets):

```env
QDRANT_URL="your_qdrant_url"
QDRANT_API_KEY="your_qdrant_api_key"
COLLECTION_NAME="do_it_tasks"

DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"

OPENAI_API_KEY="your_openai_api_key"
OPENAI_BASE_URL="your_openai_base_url"
CHAT_MODEL="your_chat_model"
```

With your venv active and `.env` configured:

```bash
streamlit run 05_build_app/app.py
```

- Open the Streamlit UI (link appears in terminal; typically `http://localhost:8501`, or the workspace proxy URL `https://<your-workspace-host>/proxy/8501`).
- Try adding a task, marking it done, and queueing for delete/approval.
- Watch your terminal and app logs for errors — troubleshoot connection or API issues before proceeding.

Once the UI and backend logic are working as expected, continue to [Step 5](../05_build_app/) to containerize and deploy your agent.

---

## Pro tips

- Demo **HITL**: ask the agent to delete a task, then approve in the **Approvals** tab.
- Optional: replace `llm_agent.py` with **LangGraph** while keeping the same Qdrant + Postgres stores.

---

## Navigation

| | |
|---|---|
| **⬅ Previous** | [Step 3 — Vayu Model as a Service](../03_vayu_model_as_a_service/) |
| **Next ➡** | [Step 5 — Streamlit app & deploy](../05_build_app/) |
| **🏠 Overview** | [Do-It overview](../README.md) |
