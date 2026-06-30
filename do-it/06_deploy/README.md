# Step 6 — Deploy Do-It (Vayu ML Service)

**Do-It** › **Vayu ML Service (Realtime Inference)** · `06_deploy/`

| | |
|---|---|
| **⬅ Previous** | [Step 5 — Build Docker image](../05_build_app/) |
| **🏁 Next** | — (journey complete) |
| **🏠 Overview** | [Do-It overview](../README.md) |

This step takes the **Streamlit Agent UI** you built in [Step 5](../05_build_app/) and runs it on the **Vayu platform** as an **ML Service**. Unlike a simple RAG app, your deployed agent is "stateful" — it actively interacts with **Vayu Managed PostgreSQL** for traces and **Vayu Vector DB** for task management. After deployment, you get a **hosted endpoint URL** so judges can interact with your agent via the web.

---

## What you are deploying

| Piece | Where it lives |
|-------|----------------|
| **Agent UI + Runtime** | Docker image (`do-it-agent:latest`) from [`05_build_app/Dockerfile`](../05_build_app/Dockerfile) |
| **Task Queue** | **Vayu Vector DB** — same `QDRANT_URL` / `QDRANT_API_KEY` as [Step 1](../01_vayu_vector_databases/) |
| **Agent Memory & HITL** | **Vayu Managed PostgreSQL** — same `DATABASE_URL` as [Step 2](../02_vayu_postgres/) |
| **Reasoning Engine** | **Vayu Model as a Service** — same keys/models as [Step 3](../03_vayu_model_as_a_service/) |

**Note:** The container relies heavily on its environment variables to reach your databases. If these are not configured correctly in the ML Service wizard, the agent will fail to start or won't be able to remember tasks.

---

## Prerequisites

| Step | Folder | You need |
|------|--------|----------|
| 0 | [`00_vayu_workspace/`](../00_vayu_workspace/) | Vayu AI Studio workspace (Docker enabled) |
| 1 | [`01_vayu_vector_databases/`](../01_vayu_vector_databases/) | `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME` |
| 2 | [`02_vayu_postgres/`](../02_vayu_postgres/) | `DATABASE_URL` |
| 3 | [`03_vayu_model_as_a_service/`](../03_vayu_model_as_a_service/) | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CHAT_MODEL` |
| 4 | [`04_starter_kit/`](../04_starter_kit/) | Agent modules tested and working locally |
| 5 | [`05_build_app/`](../05_build_app/) | Image built and pushed to **Vayu Hackathon Container Registry** |

**Before Step 6:** Ensure your agent can complete a full loop locally (Task → Tool → Postgres Log → UI) using your local `do-it/.env`.

---

## Step 1 — Build and push the Docker image

Build context **must** be `do-it/` (not `05_build_app/`). Full details: [`05_build_app/README.md`](../05_build_app/README.md#build-and-push-docker-image).

```bash
cd do-it
docker login <YOUR_CONTAINER_REGISTRY_HOST>

docker build -f 05_build_app/Dockerfile -t <YOUR_CONTAINER_REGISTRY_HOST>/do-it-agent:latest . --push
```

Note the full image reference you pushed (e.g. `<YOUR_CONTAINER_REGISTRY_HOST>/do-it-agent:latest`) — you will enter it in the ML Service wizard.

| Check | |
|-------|---|
| Port in image | **8501** (Streamlit; see `EXPOSE` in Dockerfile) |
| Secrets | **Not** baked into the image — only at runtime |

---

## Step 2 — Open Vayu ML Services

Go to [Vayu ML Services](https://ipcloud.tatacommunications.com/aistudio/#/deploy/mlops-service-list).

For the full create wizard (Start → Infrastructure → Configure Compute → Observability → Review), see the [Creating ML Service guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/ml-service/#creating-ml-service).

---

## Step 3 — Create the ML Service (wizard)

Follow the platform wizard. Map **Do-It** settings as below.

### 3.1 Start — image and runtime

| Field | Do-It value |
|-------|----------------|
| **Name** | e.g. `do-it-agent` or your team name |
| **Framework** | **Streamlit** (or **Python3** if Streamlit is not listed — app still runs via `streamlit run` in the image CMD) |
| **Private Registry → Registry URL** | `<YOUR_CONTAINER_REGISTRY_HOST>` |
| **Private Registry → Image** | Full image you pushed, e.g. `<YOUR_CONTAINER_REGISTRY_HOST>/do-it-agent:latest` |
| **Private Registry → Username / Password** | `<YOUR_REGISTRY_USERNAME>` / `<YOUR_REGISTRY_PASSWORD>` |
| **Port** | **8501** |
| **Public Expose** | Enable if you need a URL reachable outside the cluster (typical for demos) |

### 3.2 Environment variables (CRITICAL)

Add each key/value pair in the **Environment Variable** section. Use the **same values** as in your local `do-it/.env` (the `.env` file is for local dev only — it is not baked into the Docker image).

| Key | Required | Source |
|-----|----------|--------|
| `DATABASE_URL` | **Yes** | [Step 2](../02_vayu_postgres/) (Postgres connection string) |
| `QDRANT_URL` | **Yes** | [Step 1](../01_vayu_vector_databases/) |
| `QDRANT_API_KEY` | **Yes** | [Step 1](../01_vayu_vector_databases/) |
| `COLLECTION_NAME` | **Yes** | Your task collection name (e.g. `do_it_tasks`) |
| `OPENAI_API_KEY` | **Yes** | [Step 3](../03_vayu_model_as_a_service/) |
| `OPENAI_BASE_URL` | **Yes** | [Step 3](../03_vayu_model_as_a_service/) |
| `CHAT_MODEL` | **Yes** | [Step 3](../03_vayu_model_as_a_service/) |

Example values (replace secrets with yours):

```text
DATABASE_URL=postgresql://USER:***@HOST:PORT/DBNAME
QDRANT_URL=<YOUR_QDRANT_URL>
QDRANT_API_KEY=<YOUR_QDRANT_API_KEY>
COLLECTION_NAME=do_it_tasks
OPENAI_API_KEY=<YOUR_MAAS_API_KEY>
OPENAI_BASE_URL=<YOUR_MAAS_BASE_URL>
CHAT_MODEL=<YOUR_CHAT_MODEL>
```

### 3.3 Infrastructure

Select the **Datacenter**, **Business Unit**, and **Environment** assigned to your hackathon workspace (same as other Vayu resources).

### 3.4 Configure compute

| Field | Guidance |
|-------|----------|
| **Resources / flavor** | CPU is enough for Streamlit + API calls; add GPU only if your track requires it |
| **Replicas** | `1` for demo; increase for load testing |

### 3.5 Observability

Enable **Monitoring** and **Logging** if available — useful when debugging agent tool calls or MaaS errors during the demo.

### 3.6 Review and submit

Review name, image, port **8501**, and all environment variables. Click **Submit** and wait until status is **ready** (or equivalent) on the ML Services list.

---

## Step 4 — Get the endpoint and verify

1. Open **ML Services List** → click your service **Name**.
2. On **View ML Service**, check **Summary** and **Connect** for the public or internal URL.
3. Open the URL in a browser. You should see the **Do-It Agent UI**.
4. **Test the loop**:
   - Add a task via the **Tasks** tab.
   - Go to the **Agent** tab and ask it to perform that task.
   - Check if the agent's reasoning steps appear and if the task status updates.
   - **Test HITL**: Trigger an action that requires approval (e.g., a "delete" task) and verify it appears in the **Approvals** tab.

| Symptom | What to check |
|---------|----------------|
| Page does not load | Port **8501**, **Public Expose**, pod status **ready** |
| Agent fails to call tools | `OPENAI_BASE_URL` / `CHAT_MODEL` env vars |
| Agent can't see tasks | `QDRANT_URL` / `COLLECTION_NAME` env vars |
| Agent can't log traces | `DATABASE_URL` env vars |

---

## Environment variable reference

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | **Yes** | **Vayu Managed PostgreSQL** |
| `QDRANT_URL` / `QDRANT_API_KEY` | Yes (hosted) | From **Vayu Vector DB** |
| `QDRANT_PATH` | No | Local dev only — omit in ML Service |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | Yes | **Vayu Model as a Service** |
| `CHAT_MODEL` | Yes | Must match local dev |
| `COLLECTION_NAME` | No | Default task collection name |

---

## Demo checklist (submission-ready)

- [ ] Agent can successfully create/read tasks from Qdrant.
- [ ] Agent logs reasoning steps and tool calls to Postgres.
- [ ] Docker image built from `do-it/` and pushed to registry.
- [ ] ML Service **ready** with port **8501** and all env vars set.
- [ ] **HITL (Human-in-the-loop)**: You can approve/deny a risky action via the UI.
- [ ] Public/demo URL opens Do-It UI and works in a fresh browser session.

---

## Pro tips

- **Re-deploy after env changes** — Editing env vars in the ML Service usually requires a restart or new revision; confirm in the UI after saving.
- **Trace storytelling** — During your demo, show the **Agent Trace** (from Postgres) to prove the agent is "thinking" and not just hallucinating.
- **Never commit secrets** — Registry passwords, `DATABASE_URL`, and API keys only in the platform UI or secure env stores.

---

## Navigation

| | |
|---|---|
| **⬅ Previous** | [Step 5 — Build app & Docker image](../05_build_app/) |
| **Step 4** | [Agent starter kit](../04_starter_kit/) |
| **🏠 Overview** | [Do-It overview](../README.md) |
