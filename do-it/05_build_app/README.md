# Step 5 — Build App & Docker Image

**Revvive** › **Vayu Container Registry & Realtime Inference** · `05_build_app/`

| | |
|---|---|
| **Previous** | [Step 4 — Agent starter kit](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |

This step builds the **Revvive** Streamlit app, packages it in Docker, and documents the runtime architecture for local and cloud deployment.

---

## Folder structure

```text
05_build_app/
├── Dockerfile
├── README.md
├── app.py
├── ui/
│   ├── __init__.py
│   ├── page_views.py
│   └── ui_helpers.py
├── agent_tools.py
├── external_services.py
├── llm_agent.py
├── postgres_db.py
├── qdrant_tasks.py
├── revive_llm_agent.py
├── revive_postgres.py
├── revive_qdrant.py
├── revive_tools.py
└── .dockerignore
```

- `app.py` — Streamlit entrypoint and sidebar orchestration.
- `ui/` — UI package containing page rendering and shared styling.
- `ui/page_views.py` — page tab logic for onboarding, assist, approvals, and history.
- `ui/ui_helpers.py` — shared components, CSS injection, and helper renderers.
- `Dockerfile` — runtime image build definition.
- `revive_*` / `qdrant_tasks.py` / `postgres_db.py` — backend integration layers.

---

## What changed

- Moved UI rendering into `ui/page_views.py` and `ui/ui_helpers.py`.
- Kept `app.py` as a lightweight Streamlit entrypoint.
- Added package-level `ui/__init__.py` exports.
- Updated README to document the new layout and usage.

---

## Run locally

```powershell
cd do-it
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# Edit .env with your Qdrant, Postgres, and MaaS values.

cd 05_build_app
streamlit run app.py
```

- Open **http://localhost:8501**.
- In Vayu or managed workspaces, use the provided proxy URL.
- The app exposes four main tabs: `Onboarding`, `Assist`, `Approvals`, and `History`.

---

## Docker build

Build from the `do-it/` root because the image copies files from the parent folder.

```powershell
cd do-it
docker build -f 05_build_app/Dockerfile -t <YOUR_CONTAINER_REGISTRY_HOST>/revvive-app:latest . --push
```

| Item | Detail |
|---|---|
| Build context | `do-it/` |
| Dockerfile | `05_build_app/Dockerfile` |
| Exposed port | `8501` |

---

## Required environment variables

| Variable | Required | Used by | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgres_db.py` | Postgres connection string |
| `QDRANT_URL` | Yes | `qdrant_tasks.py` | Qdrant endpoint |
| `QDRANT_API_KEY` | Yes | `qdrant_tasks.py` | Qdrant auth |
| `OPENAI_API_KEY` | Yes | `llm_agent.py` | Model API key |
| `OPENAI_BASE_URL` | Yes | `llm_agent.py` | Model service base URL |
| `CHAT_MODEL` | Yes | `llm_agent.py` | Chat model identifier |
| `COLLECTION_NAME` | No | `qdrant_tasks.py` | Vector collection name |

---

## Troubleshooting

- **Streamlit fails to start**: confirm `python` environment and `streamlit` installation.
- **Database connection errors**: verify `DATABASE_URL`, network access, and TLS settings.
- **Qdrant errors**: verify `QDRANT_URL`, `QDRANT_API_KEY`, and collection availability.
- **Model issues**: verify `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `CHAT_MODEL`.
- **Docker build fails**: build from `do-it/` root, not `do-it/05_build_app/`.

---

## Notes

- The Streamlit UI now uses a dedicated `ui` package for rendering and styling.
- `app.py` remains the single entrypoint for both local development and Docker deployment.
- Existing backend modules remain unchanged and are imported at runtime.

---

## Navigation

| | |
|---|---|
| **Previous** | [Step 4 — Agent starter kit](../04_starter_kit/) |
| **Next** | [Step 6 — Deploy ML Service →](../06_deploy/) |
