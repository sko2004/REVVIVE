# REVVIVE

## Project Overview

Revvive is a unified agentic AI system built for Indian electric vehicle owners. It removes the two core anxieties of EV ownership:

- **Range uncertainty** — "Will I make it there?"
- **Repair inaccessibility** — "Who fixes this when it breaks?"

Revvive consolidates both problem domains into a single conversational AI agent sharing one interface, one reasoning loop, one tool-calling engine, and one human-approval mechanism.

Revvive is built directly on top of the **Vayu AI Studio Do-It Hackathon template**. That template already provides a deployable agent scaffold with:

- an OpenAI-compatible LLM agent planning loop
- Qdrant vector storage
- PostgreSQL trace logging
- a human-in-the-loop approval workflow
- a Streamlit UI with Docker deployment

Revvive replaces the template's generic task-management domain with EV-specific tools, data, and logic while preserving and extending the underlying agentic architecture.

---

## What the Template Already Provides (Unchanged Infrastructure)

The existing `do-it` repo is a complete, deployable agentic AI project. Revvive inherits all of this foundational infrastructure:

- **`llm_agent.py`** — the agent planning loop. Uses the OpenAI-compatible chat completions API (targeting Vayu Model as a Service) to run a tool-calling loop. Revvive keeps this loop exactly as-is; only the system prompt and the registered tools change.
- **`postgres_db.py`** — PostgreSQL connection management, table creation (`agent_runs`, `agent_steps`, `pending_actions`), and APIs for logging every run, every tool call, and every pending approval. Revvive inherits these tables and APIs unchanged. New tables are added on top.
- **`qdrant_tasks.py`** — Qdrant client setup, collection management, CRUD operations, and semantic search. The template uses this for task storage; Revvive replaces the task collection with an EV service provider collection, but the client setup and search patterns carry over directly.
- **`agent_tools.py`** — the OpenAI-style tool definition and dispatch pattern. The template defines task-management tools. Revvive replaces them with EV-specific tools while following the identical definition and dispatch pattern.
- **`app.py`** — the Streamlit application with tabbed UI, `.env` loading, cached resource initialization, and the chat interface. Revvive restructures the tabs from Tasks/Agent/Approvals to a Revive-specific layout but inherits Streamlit patterns, session state management, and environment handling.
- **`Dockerfile`** and deployment pipeline — Python 3.11 slim image, dependency installation from `requirements.txt`, Streamlit server on port 8501, Docker push and container deployment. Revvive uses the same pipeline with new dependencies added to `requirements.txt`.
- **`.env` / `.env.example`** — centralized environment configuration for `QDRANT_URL`, `QDRANT_API_KEY`, `DATABASE_URL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`. Revvive adds new variables for map and weather APIs but inherits the configuration pattern.
- **`db/schema.sql`** — DDL for the PostgreSQL schema. Revvive extends this with additional tables while keeping the existing audit and approval tables.

---

## What Revvive Changes (Domain-Specific Layer)

Everything that makes Revvive an EV product rather than a task manager lives in the domain layer built on top of the template:

- **New system prompt** in `llm_agent.py` — replaces the task-management persona with Revvive's EV assistant persona, including intent classification (range vs. breakdown), safety-check logic, and response formatting.
- **New tool definitions** in `agent_tools.py` — eight EV-specific tools replace the five template task tools.
- **New Qdrant collection** (`ev_providers` instead of `tasks`) with EV-specific embedding content and metadata schema.
- **New Streamlit UI layout** in `app.py` — EV-specific pages, cards, and interaction flows replace the task/agent/approvals tabs.
- **New external API integrations** — mapping, traffic, weather, and charger network APIs that the template does not use.
- **Extended PostgreSQL schema** — new tables for booking records and pricing history, on top of the existing agent trace tables.

---

## Tech Stack

### Reasoning Layer

| Component | Technology | Template File | What Revvive Changes |
| --- | --- | --- | --- |
| LLM orchestration | Vayu MaaS (OpenAI-compatible) | `llm_agent.py` | System prompt and registered tool list only; loop logic unchanged |
| API configuration | `.env` variables | `.env.example` | Same variables plus new map/weather keys |
| Tool dispatch | OpenAI function-calling | `agent_tools.py` | EV-specific tools replace task tools |

### Data Layer

| Component | Technology | Template File | What Revvive Changes |
| --- | --- | --- | --- |
| Vector store | Qdrant | `qdrant_tasks.py` | Collection changes from `tasks` to `ev_providers`; payload changes to provider metadata |
| Semantic search | Qdrant + embeddings | `qdrant_tasks.py` | Query content and filters changed for EV provider matching |
| Embeddings | Vayu MaaS embedding endpoint | `qdrant_tasks.py` | Same API, new provider profile input |

### Trace and Audit Layer

| Component | Technology | Template File | What Revvive Changes |
| --- | --- | --- | --- |
| Run logging | PostgreSQL | `postgres_db.py` | Unchanged |
| Step logging | PostgreSQL | `postgres_db.py` | Unchanged |
| Approval queue | PostgreSQL | `postgres_db.py` | Repurposed from task deletion approvals to booking approvals |
| Pricing & bookings | PostgreSQL | new extensions | Added `pricing_history` and `bookings` tables |

### Interface Layer

| Component | Technology | Template File | What Revvive Changes |
| --- | --- | --- | --- |
| UI framework | Streamlit | `app.py` | Layout restructured for EV use cases |
| Chat interface | Streamlit chat | `app.py` | Inherited as primary interaction surface |
| Session state | Streamlit | `app.py` | Extended with vehicle profile and location context |
| Cached resources | Streamlit cache | `app.py` | Same pattern for Qdrant/Postgres bootstrap |

### Deployment Layer

| Component | Technology | Template File | What Revvive Changes |
| --- | --- | --- | --- |
| Container image | Docker + Python 3.11 slim | `do-it/05_build_app/Dockerfile` | No structural change, new deps in `requirements.txt` |
| Serving | Streamlit port 8501 | `do-it/05_build_app/Dockerfile` | No change |

---

## Tool Definitions

Revvive replaces the template task tools with eight EV-specific tools.

### Template Tools Removed

| Tool | Purpose |
| --- | --- |
| `list_tasks` | list tasks from Qdrant |
| `search_tasks` | semantic search over task descriptions |
| `add_task` | add a task to Qdrant |
| `update_task_status` | mark task done / reopen |
| `queue_task_delete` | queue task deletion for approval |

### Revvive Tools Added

#### `estimate_range`

- Computes whether a destination is reachable on current battery charge.
- Inputs: `origin`, `destination`, `current_battery_percent`, `vehicle_make`, `vehicle_model`, `battery_capacity_kwh`, `battery_health_factor`.
- Logic: route geometry, traffic, weather, energy model, available energy, and verdict generation.
- Output: verdict, predicted arrival charge percent, confidence band, consumption breakdown, route/weather details.

#### `find_chargers_on_route`

- Finds compatible, reachable chargers when range is tight.
- Inputs: `current_location`, `destination`, `current_battery_percent`, `vehicle_make`, `vehicle_model`, `connector_type`.
- Logic: charger API, compatibility filtering, reachability checks, charge-duration estimates, suppression logic.
- Output: charger list, guidance string, and suppression message when charging is not needed.

#### `triage_issue`

- Classifies owner fault descriptions into structured diagnostics.
- Inputs: `owner_description`, `vehicle_make`, `vehicle_model`.
- Logic: LLM structured JSON output for subsystem, symptom category, severity, and explanation.
- Output: triage JSON.

#### `safety_check`

- Evaluates triage output for high-risk conditions.
- Inputs: `triage_output`, `owner_description`.
- Logic: LLM safety analysis for smoke, burning smell, swelling, sparking, thermal runaway, exposed high-voltage faults.
- Output: `is_safe`, `risk_level`, `hazard_description`, `safety_advisory`, `urgency_override`.

#### `search_providers`

- Searches the EV provider Qdrant collection by issue type, brand, and geography.
- Inputs: `subsystem`, `symptom_category`, `vehicle_brand`, `owner_location`, `radius_km`, `urgency`.
- Logic: semantic query embedding, payload filters, emergency availability for urgent cases.
- Output: ranked provider matches.

#### `get_provider_details`

- Retrieves a provider's full profile from Qdrant.
- Inputs: `provider_id`.
- Output: provider metadata and contact details.

#### `estimate_fair_price`

- Estimates repair cost range for the diagnosed issue.
- Inputs: `subsystem`, `symptom_category`, `severity`, `vehicle_make`, `vehicle_model`, `vehicle_category`, `region`.
- Logic: PostgreSQL pricing history lookup, or LLM fallback if no data exists.
- Output: `cost_min`, `cost_max`, breakdown, data source, disclaimer.

#### `queue_booking`

- Queues a proposed service booking for human approval.
- Inputs: `provider_id`, `provider_name`, `issue_summary`, `triage_json`, `estimated_cost_min`, `estimated_cost_max`, `urgency`, `owner_notes`.
- Logic: write pending approval record to `pending_actions` and return a booking payload.
- Output: `pending_action_id`, confirmation message, booking summary.

---

## Qdrant Collection Schema

### Template Collection: `tasks`

- Vector: task description embedding
- Payload: title, description, status, priority, created_at

### Revvive Collection: `ev_providers`

- Vector: provider capability profile embedding
- Payload includes:
  - `name`
  - `address`
  - `location`
  - `phone`
  - `brand_certifications`
  - `subsystem_specialisations`
  - `equipment`
  - `rating`
  - `review_count`
  - `emergency_available`
  - `hours`
  - `pricing_tier`
  - `service_history_summary`
  - `connector_types`
  - `description`

The collection setup and vector search patterns are inherited from the template; only the domain schema and query filters change.

---

## PostgreSQL Schema

### Inherited Tables

- `agent_runs`
- `agent_steps`
- `pending_actions`

These tables are used unchanged for run auditing and approvals.

### Revvive Additions

- `pricing_history` — stores historical repair cost ranges by subsystem, symptom category, vehicle category, and region.
- `bookings` — stores completed bookings with triage data, provider match, cost estimate, and status.

---

## Application Structure

### Pages and UI

Revvive reuses the template's Streamlit architecture but replaces task-centric UI with EV-centric flows:

- **Home / Vehicle Setup** — captures vehicle profile and battery context.
- **Chat / Assist** — primary conversational interface for range and repair workflows.
- **Approvals** — human-in-the-loop review for queued booking approvals.
- **History** — audit view of past runs, tool traces, and bookings.

### Cards and Response Types

- Range verdict cards
- Charger recommendation cards
- Triage diagnostics cards
- Safety alert cards
- Provider recommendation cards
- Fair-price estimate cards
- Booking approval cards

---

## End-to-End Flows

### Range Query Flow

1. User asks a range question.
2. Agent calls `estimate_range`.
3. If result is `Tight` or `Not Advisable`, it triggers `find_chargers_on_route`.
4. App renders range and charger recommendation cards.

### Breakdown Flow

1. User reports a fault.
2. Agent calls `triage_issue`.
3. Agent calls `safety_check`.
4. Agent searches providers via `search_providers` and `get_provider_details`.
5. Agent estimates cost with `estimate_fair_price`.
6. Agent queues bookings with `queue_booking`.
7. User approves or rejects the booking before completion.

### Safety Alert Flow

1. `safety_check` returns `is_safe=false`.
2. Agent escalates urgency and filters provider search for emergency availability.
3. App displays an urgent safety alert card.

---

## How to Run the Project

### Local Development

```powershell
cd do-it
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit do-it\.env with your Qdrant, Postgres, and Vayu MaaS values.
cd 05_build_app
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### Docker Build and Run

From the `do-it` root:

```powershell
cd do-it
docker build -f 05_build_app/Dockerfile -t revive-app:latest .
```

Run locally:

```powershell
docker run -p 8501:8501 revive-app:latest
```

If pushing to a registry:

```powershell
docker build -f 05_build_app/Dockerfile -t <REGISTRY_HOST>/revive-app:latest .
docker push <REGISTRY_HOST>/revive-app:latest
```

### Required Environment Variables

- `DATABASE_URL` — Postgres connection string
- `QDRANT_URL` — Qdrant endpoint
- `QDRANT_API_KEY` — Qdrant auth key
- `OPENAI_API_KEY` — Vayu MaaS model API key
- `OPENAI_BASE_URL` — Vayu MaaS base URL
- `CHAT_MODEL` — chat model identifier
- `COLLECTION_NAME` — optional Qdrant collection name (defaults to `ev_providers`)
- `GOOGLE_MAPS_API_KEY` — route and maps data (if used)
- `WEATHER_API_KEY` — weather data (if used)
- `CHARGER_API_KEY` — charger network API key (if used)

---

## Notes

- The root project README documents the overall architecture and how Revvive extends the Vayu Do-It template.
- The Streamlit app entrypoint is `do-it/05_build_app/app.py`.
- Additional build-app-specific documentation is available in `do-it/05_build_app/README.md`.

---

## Future Roadmap

- **MVP (Today):** unified range confidence + repair booking assistant, built on the Vayu Do-It template.
- **Trust stage:** collect EV failure data, battery health indicators, and repair pricing history to build a market moat.
- **Predictive stage:** add telematics and live battery diagnostics to move from reactive support to predictive maintenance.

The core data asset is the failure-mode and energy-consumption dataset generated by every agent run and tool call in `agent_runs` and `agent_steps`.
