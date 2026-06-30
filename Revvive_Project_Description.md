# Revvive - Complete Project Description (Built on the Vayu Do-It Template)

## 1. Project Overview

Revvive is a unified agentic AI system that eliminates the two core anxieties of electric vehicle ownership in India: range uncertainty ("Will I make it there?") and after-sales repair inaccessibility ("Who fixes this when it breaks?"). It consolidates both problem domains into a single conversational AI agent sharing one interface, one reasoning loop, one tool-calling engine, and one human-approval mechanism.

Revvive is built directly on top of the **Vayu AI Studio Do-It Hackathon template** - a pre-wired scaffold that already provides an OpenAI-compatible LLM agent loop, Qdrant vector storage, PostgreSQL trace logging, a human-in-the-loop approval workflow, and a Streamlit UI with Docker deployment. The template implements a generic task-management agent; Revive replaces that domain with EV-specific tools, data, and logic while preserving and extending the underlying agentic architecture.

### What the Template Already Provides (Unchanged Infrastructure)

The existing `do-it` repo is a complete, deployable agentic AI project. Revvive inherits all of this foundational infrastructure:

- **`llm_agent.py`** - the agent planning loop. Uses the OpenAI-compatible chat completions API (pointed at Vayu Model as a Service) to run a tool-calling loop: the LLM receives the user's message, decides which tool to call, receives the tool output, decides the next action, and repeats until completion or approval. Revvive keeps this loop unchanged; only the system prompt and the registered tools change.
- **`postgres_db.py`** - PostgreSQL connection management, table creation (`agent_runs`, `agent_steps`, `pending_actions`), and APIs for logging every run, every tool call, and every pending approval. Revvive inherits these unchanged and builds new tables on top.
- **`qdrant_tasks.py`** - Qdrant client setup, collection management, CRUD, and semantic search. Revvive reuses the connection and search architecture, replacing the template task collection with an EV provider collection.
- **`agent_tools.py`** - OpenAI-style tool definitions and dispatch. The template defines task-management tools; Revive swaps in EV-specific tools using the same function-calling pattern.
- **`app.py`** - the Streamlit application with tabbed UI, `.env` loading, cached resource initialization, and the chat interface. Revvive reuses the Streamlit architecture and session state handling while replacing the domain flows.
- **`Dockerfile`** and deployment pipeline - Python 3.11 slim image, dependency installation from `requirements.txt`, Streamlit on port 8501, Docker push and deployment. Revvive uses the same pipeline with additional dependencies.
- **`.env` / `.env.example`** - centralized runtime configuration. Revvive preserves the existing pattern and adds new API keys for maps, weather, and charger services.
- **`db/schema.sql`** - PostgreSQL DDL. Revvive extends the schema with new data tables while keeping the audit and approval tables.

### What Revive Changes (Domain-Specific Layer)

Everything that makes Revive an EV product rather than a task manager lives in the domain layer built on top of the template:

- **New system prompt** in `llm_agent.py` - replaces the task-management persona with Revive's EV assistant persona, including intent classification, safety logic, and response rules.
- **New tool definitions** in `agent_tools.py` - eight EV-specific tools replace the five task-management tools.
- **New Qdrant collection** (`ev_providers`) - EV service provider data instead of task records.
- **New Streamlit UI layout** in `app.py` - EV-specific onboarding, assist, approvals, and history flows.
- **New external API integrations** - mapping, traffic, weather, and charger network APIs.
- **Extended PostgreSQL schema** - new tables for bookings and pricing history.

---

## 2. Tech Stack - What Powers Each Layer

### 2.1 Reasoning Layer

| Component | Technology | Template File | What Revive Changes |
| --- | --- | --- | --- |
| LLM orchestration | Vayu Model as a Service (OpenAI-compatible API) | `llm_agent.py` | Same loop; new system prompt and tool list |
| API configuration | `.env` variables | `.env.example` | Same env pattern; added map/weather keys |
| Tool dispatch | OpenAI function-calling | `agent_tools.py` | Same dispatch pattern; new EV tools |

### 2.2 Data Layer

| Component | Technology | Template File | What Revive Changes |
| --- | --- | --- | --- |
| Vector store | Qdrant | `qdrant_tasks.py` | Use `ev_providers` instead of `tasks`; provider metadata schema |
| Client setup | `qdrant-client` | `qdrant_tasks.py` | Same connection logic |
| Semantic search | Qdrant query + filters | `qdrant_tasks.py` | Search by provider specialty, brand, urgency |
| Embeddings | Vayu MaaS embeddings | `qdrant_tasks.py` | Same API; provider profile input |

### 2.3 Trace and Audit Layer

| Component | Technology | Template File | What Revive Changes |
| --- | --- | --- | --- |
| Run logging | PostgreSQL table | `postgres_db.py` | No change |
| Step logging | PostgreSQL table | `postgres_db.py` | No change |
| Approval queue | `pending_actions` | `postgres_db.py` | Repurposed for booking approvals |
| Pricing history | PostgreSQL table | new schema extension | Added |
| Bookings | PostgreSQL table | new schema extension | Added |

### 2.4 Interface Layer

| Component | Technology | Template File | What Revive Changes |
| --- | --- | --- | --- |
| Web framework | Streamlit | `app.py` | Same framework; EV UI layout |
| Chat interface | `st.chat_message`, `st.chat_input` | `app.py` | Same pattern; primary user surface |
| Session state | `st.session_state` | `app.py` | Extended with vehicle context |
| Cached resources | `@st.cache_resource` | `app.py` | Same bootstrap pattern |

### 2.5 Deployment Layer

| Component | Technology | Template File | What Revive Changes |
| --- | --- | --- | --- |
| Container image | Python 3.11 slim | `05_build_app/Dockerfile` | Same pipeline; new deps in `requirements.txt` |
| Serving | Streamlit port 8501 | `06_deploy/README.md` | Same |

### 2.6 New External APIs (Not in Template)

| API | Purpose | Used By |
| --- | --- | --- |
| Google Maps Directions API / OpenRouteService | Route geometry, elevation, distances | `estimate_range` |
| Traffic API | Real-time congestion | `estimate_range` |
| Weather API | temperature, wind, precipitation | `estimate_range` |
| Charger network API / Open Charge Map | charger location, availability | `find_chargers_on_route` |

---

## 3. Complete Tool Definitions - What Replaces the Template Tools

### Template Tools Removed

| Tool | Purpose |
| --- | --- |
| `list_tasks` | list tasks in Qdrant |
| `search_tasks` | semantic search over tasks |
| `add_task` | add a task |
| `update_task_status` | mark a task done / reopen |
| `queue_task_delete` | queue task deletion approval |

### Revive Tools Added

#### `estimate_range`

- Purpose: determine whether a route is reachable on current charge.
- Inputs: origin, destination, current_battery_percent, vehicle_make, vehicle_model, battery_capacity_kwh, battery_health_factor.
- Logic: route + traffic + weather + energy model.
- Output: verdict, predicted arrival %, confidence band, breakdown.

#### `find_chargers_on_route`

- Purpose: find reachable compatible chargers when range is tight.
- Inputs: current_location, destination, current_battery_percent, vehicle_make, vehicle_model, connector_type.
- Logic: charger API, compatibility filter, reachability check, charge-duration guidance.
- Output: reachable chargers or suppression guidance.

#### `triage_issue`

- Purpose: classify a fault description into a structured diagnosis.
- Inputs: owner_description, vehicle_make, vehicle_model.
- Logic: LLM structured JSON output.

#### `safety_check`

- Purpose: evaluate safety risk from the triage output.
- Inputs: triage_output, owner_description.
- Logic: LLM safety assessment.
- Output: is_safe, risk_level, hazard_description, safety_advisory, urgency_override.

#### `search_providers`

- Purpose: find EV service providers matching the issue and location.
- Inputs: subsystem, symptom_category, vehicle_brand, owner_location, radius_km, urgency.
- Logic: semantic Qdrant search with filters.

#### `get_provider_details`

- Purpose: fetch a provider's full profile from Qdrant.
- Inputs: provider_id.

#### `estimate_fair_price`

- Purpose: estimate repair cost range for the diagnosed issue.
- Inputs: subsystem, symptom_category, severity, vehicle_make, vehicle_model, vehicle_category, region.
- Logic: pricing history lookup or LLM fallback.

#### `queue_booking`

- Purpose: queue a proposed service booking for human approval.
- Inputs: provider_id, provider_name, issue_summary, triage_json, estimated_cost_min, estimated_cost_max, urgency, owner_notes.
- Logic: create a pending approval record.

---

## 4. Qdrant Collection Schema - What Replaces `tasks`

### Template Collection: `tasks`

- Vector: task description embedding
- Payload: title, description, status, priority, created_at

### Revive Collection: `ev_providers`

- Vector: provider capability profile embedding
- Payload:
  - name
  - address
  - location { lat, lng }
  - phone
  - brand_certifications
  - subsystem_specialisations
  - equipment
  - rating
  - review_count
  - emergency_available
  - hours
  - pricing_tier
  - service_history_summary
  - connector_types
  - description

---

## 5. PostgreSQL Schema - What's Inherited and What's Added

### Inherited

- `agent_runs`
- `agent_steps`
- `pending_actions`

### Added by Revive

- `pricing_history`
- `bookings`

---

## 6. Application Structure

### Template UI

- Tasks tab
- Agent tab
- Approvals tab

### Revive UI

- Home / Setup
- Assist / Chat
- Approvals
- History

---

## 7. End-to-End Flows

### Range Query

- User asks a range question.
- `estimate_range` runs.
- If needed, `find_chargers_on_route` runs.
- UI renders range and charger recommendations.

### Breakdown

- User reports a fault.
- `triage_issue` -> `safety_check` -> `search_providers` -> `get_provider_details` -> `estimate_fair_price` -> `queue_booking`.
- Approval is required before completion.

### Safety Alert

- `safety_check` flags danger.
- Urgent provider search runs.
- UI shows an urgent safety warning.

---

## 8. Run Instructions

### Local

```powershell
cd do-it
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# update do-it\.env with Qdrant, Postgres, and Vayu MaaS values
cd 05_build_app
streamlit run app.py
```

### Docker

```powershell
cd do-it
docker build -f 05_build_app/Dockerfile -t revive-app:latest .
docker run -p 8501:8501 revive-app:latest
```

### Required Environment Variables

- `DATABASE_URL`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `CHAT_MODEL`
- `GOOGLE_MAPS_API_KEY`
- `WEATHER_API_KEY`
- `CHARGER_API_KEY`

---

## 9. Roadmap

- **MVP:** unified range + repair booking assistant built on Vayu Do-It.
- **Trust:** battery health data and repair pricing history.
- **Predictive:** telematics and live diagnostics.

The competitive moat is the failure-mode and energy-consumption dataset generated by every run in `agent_runs` and `agent_steps`.
