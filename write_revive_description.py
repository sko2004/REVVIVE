from pathlib import Path

content = '''# Revvive — Complete Project Description (Built on the Vayu Do-It Template)

## 1. Project Overview

Revvive is a unified agentic AI assistant for Indian electric vehicles. It solves two primary owner problems:
- range confidence: “Can I make this trip on current battery charge?”
- service access: “Who can fix this issue, and should I approve a booking?”

Revvive reuses the Vayu Do-It template’s agentic scaffold while replacing the original task-management domain with EV-specific reasoning, provider search logic, range estimation, safety triage, pricing estimates, and booking approvals.

### What the Template Infrastructure Provides

The `do-it` repository already supplies a deployable agentic backend. Revive reuses this foundation:

- **Agent orchestration**
  - Template path: `do-it/05_build_app/llm_agent.py`
  - Active Revive path: `do-it/05_build_app/revive_llm_agent.py`
  - Role: orchestrates the chat + tool-calling loop using OpenAI-compatible tool definitions and logs every step.

- **Postgres audit and HITL queue**
  - Template path: `do-it/05_build_app/postgres_db.py`
  - Active Revive path: `do-it/05_build_app/revive_postgres.py`
  - Role: manages `agent_runs`, `agent_steps`, and `pending_actions`, with Revive extending booking approvals and pricing history.

- **Qdrant vector search**
  - Template path: `do-it/05_build_app/qdrant_tasks.py`
  - Active Revive path: `do-it/05_build_app/revive_qdrant.py`
  - Role: sets up Qdrant client and semantic search. The connection and search patterns stay the same; the stored collection changes from tasks to EV providers.

- **Tool dispatch**
  - Template path: `do-it/05_build_app/agent_tools.py`
  - Active Revive path: `do-it/05_build_app/revive_tools.py`
  - Role: defines the tool metadata and dispatch function. Revive keeps the same OpenAI tool-call architecture but replaces the tool set with EV-specific tools.

- **Streamlit UI**
  - Template path: `do-it/05_build_app/app.py`
  - Active Revive path: `do-it/05_build_app/app.py`
  - Role: renders the web UI, manages session state, and presents chat, approvals, and history.

- **Deployment**
  - Template path: `do-it/05_build_app/Dockerfile`
  - Active Revive path: `do-it/05_build_app/Dockerfile`
  - Role: builds a Python 3.11 slim image, installs dependencies from `do-it/requirements.txt`, and runs Streamlit.

- **Environment configuration**
  - Template path: `do-it/.env.example`
  - Active Revive path: `do-it/.env.example`
  - Role: configures Qdrant, Postgres, Vayu MaaS, and Revive external API keys.

- **Schema docs**
  - Template path: `do-it/04_starter_kit/db/schema.sql`
  - Active Revive path: `do-it/04_starter_kit/db/schema.sql`
  - Role: documents the PostgreSQL schema, including Revive’s added tables.

### What Revive Changes

Revvive changes the domain layer while preserving the template’s core agentic architecture:

- replaces the generic task tool set with eight EV-specific tools
- swaps the Qdrant collection from tasks to `ev_providers`
- adds route/weather/charger external API integrations
- extends Postgres with `pricing_history` and `bookings`
- reworks the Streamlit UI around vehicle setup, chat, approvals, and history

---

## 2. Tech Stack — What Powers Each Layer

### 2.1 Reasoning Layer

| Component | Template | Revive |
|---|---|---|
| LLM orchestration | `do-it/05_build_app/llm_agent.py` | `do-it/05_build_app/revive_llm_agent.py` |
| Tool dispatch | `do-it/05_build_app/agent_tools.py` | `do-it/05_build_app/revive_tools.py` |
| Configuration | `do-it/.env.example` | same file with added external API keys |

### 2.2 Data Layer

| Component | Template | Revive |
|---|---|---|
| Vector DB | `do-it/05_build_app/qdrant_tasks.py` | `do-it/05_build_app/revive_qdrant.py` |
| Embeddings | Vayu MaaS embedding endpoint | same endpoint, EV provider embeddings |
| Semantic search | task search | provider search with brand, location, urgency filters |

### 2.3 Trace and Audit Layer

| Component | Template | Revive |
|---|---|---|
| Run audit | `agent_runs` | unchanged |
| Step audit | `agent_steps` | unchanged |
| HITL queue | `pending_actions` | reused for booking approvals |
| New tables | none | `pricing_history`, `bookings` |

### 2.4 Interface Layer

| Component | Template | Revive |
|---|---|---|
| Web app | Streamlit app | same file, EV-focused UI |
| Chat UX | `st.chat_message`, `st.chat_input` | same chat pattern with tool cards |
| Session state | `st.session_state` | extended for battery and vehicle context |

### 2.5 Deployment Layer

| Component | Template | Revive |
|---|---|---|
| Docker | `do-it/05_build_app/Dockerfile` | unchanged |
| Dependencies | `do-it/requirements.txt` | updated with `requests` |

### 2.6 External APIs

| API | Purpose | Tool |
|---|---|---|
| Google Maps / OpenRouteService | route geometry, distance, traffic | `estimate_range` |
| OpenWeatherMap / WeatherAPI | weather impact | `estimate_range` |
| Open Charge Map | charger lookup and connector matching | `find_chargers_on_route` |

New `.env` keys:
- `GOOGLE_MAPS_API_KEY`
- `OPENROUTESERVICE_API_KEY`
- `WEATHER_API_KEY`
- `OPENCHARGEMAP_API_KEY`

---

## 3. Revive Tool Set

Revvive replaces the template’s task tools with eight EV-specific tools:

- `estimate_range`
- `find_chargers_on_route`
- `triage_issue`
- `safety_check`
- `search_providers`
- `get_provider_details`
- `estimate_fair_price`
- `queue_booking`

### Human-in-the-loop booking approval

Bookings are queued in `pending_actions` with `action_type='booking'` and reviewed in the Streamlit approvals UI.

---

## 4. Active Revive Files

| Area | File |
|---|---|
| Agent orchestration | `do-it/05_build_app/revive_llm_agent.py` |
| EV tool definitions | `do-it/05_build_app/revive_tools.py` |
| Provider search | `do-it/05_build_app/revive_qdrant.py` |
| Postgres extensions | `do-it/05_build_app/revive_postgres.py` |
| External APIs | `do-it/05_build_app/external_services.py` |
| UI | `do-it/05_build_app/app.py` |
| Schema docs | `do-it/04_starter_kit/db/schema.sql` |
| Env config | `do-it/.env.example` |
| Docker | `do-it/05_build_app/Dockerfile` |

### Legacy template files still present

- `do-it/05_build_app/agent_tools.py`
- `do-it/05_build_app/qdrant_tasks.py`
- `do-it/05_build_app/llm_agent.py`
- `do-it/05_build_app/postgres_db.py`
'''

Path('Revvive_Project_Description.md').write_text(content, encoding='utf-8')
print('updated')
