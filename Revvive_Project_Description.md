# Revvive — Complete Project Description (Built on the Vayu Do-It Template)

## 1. Project Overview

Revvive is a unified agentic AI system that eliminates the two core anxieties of electric vehicle ownership in India: range uncertainty ("Will I make it there?") and after-sales repair inaccessibility ("Who fixes this when it breaks?"). It consolidates both problem domains into a single conversational AI agent sharing one interface, one reasoning loop, one tool-calling engine, and one human-approval mechanism.

Revvive is built directly on top of the **Vayu AI Studio Do-It Hackathon template** — a pre-wired scaffold that already provides an OpenAI-compatible LLM agent loop, Qdrant vector storage, PostgreSQL trace logging, a human-in-the-loop approval workflow, and a Streamlit UI with Docker deployment. The template implements a generic task-management agent; Revvive replaces that domain with EV-specific tools, data, and logic while preserving and extending the underlying agentic architecture.

### What the Template Already Provides (Unchanged Infrastructure)

The existing `do-it` repo is a complete, deployable agentic AI project. Revvive inherits all of this foundational infrastructure:

- **`llm_agent.py`** — The agent planning loop. Uses the OpenAI-compatible chat completions API (pointed at Vayu Model as a Service) to run a tool-calling loop: the LLM receives the user's message, decides which tool to call, receives the tool's output, decides the next action, and repeats until the task is complete or an approval gate is reached. Revvive keeps this loop exactly as-is — only the system prompt and the registered tools change.

- **`postgres_db.py`** — PostgreSQL connection management, table creation (`agent_runs`, `agent_steps`, `pending_actions`), and APIs for logging every run, every tool call, and every pending approval. Revvive inherits all three tables and their logging APIs unchanged. New tables are added on top (provider pricing history, booking records).

- **`qdrant_tasks.py`** — Qdrant client setup, collection management, CRUD operations, and semantic search. The template uses this for task storage; Revvive replaces the task collection with an EV service provider collection, but the client setup, connection logic, and search patterns carry over directly.

- **`agent_tools.py`** — The OpenAI-style tool definition and dispatch pattern. The template defines tools like `list_tasks`, `search_tasks`, `add_task`, `update_task_status`, and `queue_task_delete`. Revvive replaces these with EV-specific tools (`estimate_range`, `find_chargers_on_route`, `triage_issue`, `safety_check`, `search_providers`, `get_provider_details`, `estimate_fair_price`, `queue_booking`) but follows the identical definition and dispatch pattern.

- **`app.py`** — The Streamlit application with tabbed UI, `.env` loading, cached resource initialization, and the chat interface for the agent. Revvive restructures the tabs from Tasks/Agent/Approvals to a Revvive-specific layout but inherits the Streamlit patterns, session state management, and environment handling.

- **`Dockerfile`** and deployment pipeline — Python 3.11 slim image, dependency installation from `requirements.txt`, Streamlit server on port 8501, Docker push to Vayu Hackathon Container Registry, deployment on Vayu Realtime Inference. Revvive uses this pipeline with no changes except adding new dependencies to `requirements.txt`.

- **`.env` / `.env.example`** — Centralized environment configuration for `QDRANT_URL`, `QDRANT_API_KEY`, `DATABASE_URL`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`. Revvive adds new variables (map API keys, weather API keys) but inherits the existing configuration pattern.

- **`db/schema.sql`** — DDL for the PostgreSQL schema. Revvive extends this with additional tables while keeping the existing `agent_runs`, `agent_steps`, and `pending_actions` tables.

### What Revvive Changes (Domain-Specific Layer)

Everything that makes Revvive an EV product rather than a task manager lives in the domain layer built on top of the template:

- **New system prompt** in `llm_agent.py` — replaces the task-management persona with Revvive's EV assistant persona, including intent classification rules (range vs. breakdown), safety-check logic, and response formatting.
- **New tool definitions** in `agent_tools.py` — eight EV-specific tools replace the five task-management tools.
- **New Qdrant collection** (`ev_providers` instead of `tasks`) with EV-specific embedding content and metadata schema.
- **New Streamlit UI layout** in `app.py` — EV-specific pages, cards, and interaction flows replace the task/agent/approvals tabs.
- **New external API integrations** — mapping, traffic, weather, and charger network APIs that the template doesn't use.
- **Extended PostgreSQL schema** — new tables for booking records and pricing history, on top of the existing agent trace tables.

---

## 2. Tech Stack — What Powers Each Layer

### 2.1 Reasoning Layer

| Component | Technology | Template File | What Revvive Changes |
|-----------|-----------|---------------|---------------------|
| LLM orchestration | Vayu Model as a Service (OpenAI-compatible API) | `llm_agent.py` | System prompt and registered tool list only; the planning loop, tool-call parsing, iteration logic, and final-answer detection are unchanged |
| API configuration | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL` from `.env` | `.env.example` | No change; same env vars point to the same Vayu MaaS endpoint |
| Tool dispatch | OpenAI function-calling format with JSON tool definitions | `agent_tools.py` | Tool definitions replaced entirely; dispatch pattern (name → function mapping) unchanged |

### 2.2 Data Layer

| Component | Technology | Template File | What Revvive Changes |
|-----------|-----------|---------------|---------------------|
| Vector store | Vayu Vector DB (Qdrant) | `qdrant_tasks.py` | Collection changes from `tasks` to `ev_providers`; embedding content changes from task descriptions to provider capability profiles; metadata payload changes from task status/priority to brand certifications, subsystem specialisations, location, emergency availability |
| Client setup | `qdrant-client` Python library, `QDRANT_URL` and `QDRANT_API_KEY` from `.env` | `qdrant_tasks.py` | No change to connection logic |
| Semantic search | Qdrant search with vector similarity + payload filtering | `qdrant_tasks.py` | Query content changes (triage output instead of task keywords); filters change (brand, radius, urgency instead of status) |
| Embedding generation | Vayu MaaS embedding endpoint (OpenAI-compatible) | `qdrant_tasks.py` | Same embedding API; input text changes from task descriptions to provider profiles |

### 2.3 Trace and Audit Layer

| Component | Technology | Template File | What Revvive Changes |
|-----------|-----------|---------------|---------------------|
| Run logging | `agent_runs` table in Vayu Managed PostgreSQL | `postgres_db.py` | No change; every Revvive agent run is logged with the same schema |
| Step logging | `agent_steps` table | `postgres_db.py` | No change; every tool call (estimate_range, triage_issue, etc.) is logged with input params, output, and latency |
| Approval queue | `pending_actions` table | `postgres_db.py` | Template uses this for task-delete approvals; Revvive repurposes it for booking approvals. Booking details (provider_id, issue_summary, estimated_cost, urgency) are stored inside the existing `action_detail` JSONB column with `action_type='booking'` — no schema change needed |
| Connection management | `psycopg`, connection retry logic, URL caching | `postgres_db.py` | No change |
| New: Pricing history | New `pricing_history` table | New addition to `db/schema.sql` | Stores historical repair costs by issue type, subsystem, vehicle category, and region for fair-price estimation |
| New: Booking records | New `bookings` table | New addition to `db/schema.sql` | Stores completed booking records with full triage output, provider match, cost estimate, and outcome |

### 2.4 Interface Layer

| Component | Technology | Template File | What Revvive Changes |
|-----------|-----------|---------------|---------------------|
| Web framework | Streamlit | `app.py` | Framework unchanged; UI layout restructured for EV domain |
| Chat interface | `st.chat_message`, `st.chat_input` | `app.py` (Agent tab) | Inherited directly; this becomes Revvive's primary interaction surface |
| Session state | `st.session_state` | `app.py` | Extended with vehicle profile, battery state, and location context |
| Environment loading | `python-dotenv`, `.env` | `app.py` | Inherited; new API keys added |
| Cached resources | `@st.cache_resource` for Qdrant/Postgres bootstrap | `app.py` | Same pattern; initializes EV provider collection instead of task collection |

### 2.5 Deployment Layer

| Component | Technology | Template File | What Revvive Changes |
|-----------|-----------|---------------|---------------------|
| Container image | Python 3.11 slim, Dockerfile | `05_build_app/Dockerfile` | No structural change; new dependencies added to `requirements.txt` |
| Registry | Vayu Hackathon Container Registry | `06_deploy/README.md` | No change |
| Serving | Vayu Realtime Inference, port 8501 | `06_deploy/README.md` | No change |
| Ignore rules | `.dockerignore`, `.gitignore` | Root and `05_build_app/` | No change |

### 2.6 New External APIs (Not in Template)

| API | Purpose | Used By Tool |
|-----|---------|-------------|
| Google Maps Directions API / OpenRouteService | Route geometry, distance segments, elevation profile | `estimate_range` |
| Google Maps Traffic Layer / TomTom Traffic API | Real-time congestion per route segment | `estimate_range` |
| OpenWeatherMap / WeatherAPI | Temperature, wind, precipitation along route | `estimate_range` |
| Open Charge Map API / proprietary charger network APIs | Charger locations, connector types, power ratings, availability | `find_chargers_on_route` |

These are added to `requirements.txt` (e.g., `requests`, `googlemaps`) and configured via new `.env` variables (`GOOGLE_MAPS_API_KEY`, `WEATHER_API_KEY`).

---

## 3. Complete Tool Definitions — What Replaces the Template Tools

The template's `agent_tools.py` defines five task-management tools. Revvive replaces them with eight EV-specific tools, following the identical OpenAI function-calling definition format:

### Template Tools (Removed)

| Template Tool | What It Did |
|--------------|-------------|
| `list_tasks` | Listed all tasks from Qdrant |
| `search_tasks` | Semantic search over task descriptions in Qdrant |
| `add_task` | Added a new task to Qdrant |
| `update_task_status` | Changed task status (done/reopen) |
| `queue_task_delete` | Queued a task deletion for human approval via `pending_actions` |

### Revvive Tools (Added)

#### Tool 1: `estimate_range`

**Purpose:** Computes whether a destination is reachable on the current charge, returning a verdict with confidence band.

**Inputs:** origin (lat/lng or address), destination (lat/lng or address), current_battery_percent, vehicle_make, vehicle_model, battery_capacity_kwh (degraded).

**Internal logic:**
1. Calls Google Maps Directions API → gets route geometry, segment distances, elevation profile.
2. Calls Traffic API → gets real-time speed/congestion per segment.
3. Calls Weather API → gets temperature, wind, precipitation along the route.
4. Runs a physics-informed energy model: for each route segment, computes energy consumption based on distance, elevation delta, speed profile (from traffic), weather drag, vehicle weight, motor efficiency, and regenerative braking on downhills.
5. Sums segment consumption → total energy needed.
6. Compares against available energy (current_battery_percent × degraded_capacity).
7. Returns: verdict (Comfortable / Tight / Not Advisable), predicted_arrival_charge_percent, confidence_band (best-case / worst-case), consumption_breakdown (terrain, traffic, weather, base).

**Tech used:** Google Maps API, Traffic API, Weather API, internal Python energy model, Vayu MaaS LLM (for natural-language verdict composition).

**Template parallel:** This replaces `list_tasks` and `search_tasks` — it's the primary "read" operation for the range domain.

---

#### Tool 2: `find_chargers_on_route`

**Purpose:** Finds reachable, compatible charging stations when range is tight or battery is low.

**Inputs:** current_location (lat/lng), destination (lat/lng or "home"), current_battery_percent, vehicle_make, vehicle_model, connector_type.

**Internal logic:**
1. Calls charger network API → gets charger locations, connector types, power ratings, availability within a corridor around the route or within range of the current location.
2. Filters for connector compatibility with the owner's vehicle.
3. For each candidate, runs a mini `estimate_range` check → can the vehicle reach this charger on current charge?
4. Filters out unreachable chargers.
5. For reachable chargers, computes charge_duration_minutes (how long to charge to reach a target — either the destination or 80%).
6. Applies suppression logic: if the owner can comfortably reach a known destination (home, office) without charging, returns a "no stop needed" message instead.
7. Returns: list of reachable chargers with name, location, distance, connector, power_rating, charge_minutes_needed, and a "charge X minutes to travel Y km" guidance string.

**Tech used:** Open Charge Map API / charger network APIs, Google Maps API (for distance), internal energy model, Vayu MaaS LLM (for suppression reasoning and natural-language output).

**Template parallel:** This is a conditional extension of `estimate_range` — it's triggered autonomously by the agent when the range verdict is Tight or Not Advisable, demonstrating agentic branching.

---

#### Tool 3: `triage_issue`

**Purpose:** Classifies a plain-language fault description into a structured diagnosis.

**Inputs:** owner_description (free text), vehicle_make, vehicle_model.

**Internal logic:**
1. The Vayu MaaS LLM receives the owner's description with a structured-output prompt demanding a JSON response conforming to a predefined schema.
2. The LLM classifies: subsystem (Battery/BMS, Motor/Drivetrain, Controller/Power Electronics, Charging Circuit, Brakes, Suspension, Electrical, Software/Dashboard), symptom_category (standardised label), severity (Low / Medium / High / Critical), and explanation (plain-language description for the owner).
3. Returns the structured JSON object for downstream consumption by safety_check and search_providers.

**Tech used:** Vayu Model as a Service (LLM) with structured JSON output enforcement. Pure model reasoning — no external API calls.

**Template parallel:** This replaces `add_task` — it's the primary "write/classify" operation that initiates the breakdown workflow.

---

#### Tool 4: `safety_check`

**Purpose:** Evaluates the triage output for high-risk conditions and returns a safe/unsafe flag that controls the agent's branching behaviour.

**Inputs:** triage_output (the JSON from `triage_issue`), owner_description (original text, re-examined for safety keywords).

**Internal logic:**
1. The LLM evaluates the triage output and original description against high-risk indicators: smoke, burning smell, battery swelling/deformation, sparking, leaking fluid, thermal runaway symptoms, exposed high-voltage components.
2. Returns: is_safe (boolean), risk_level (none / elevated / critical), hazard_description (what was detected), safety_advisory (instructions for the owner: "Do not ride", "Do not charge", "Move away from vehicle"), urgency_override (if unsafe, forces urgency to Critical regardless of triage severity).

**Tech used:** Vayu Model as a Service (LLM). Pure model reasoning.

**Template parallel:** No direct template equivalent. This is the conditional branching mechanism — the agent's planner evaluates the safety_check output and changes its execution plan (normal → urgent), which is the core demonstration of genuine agency.

**Connection to agent loop:** After `safety_check` returns, the agent's planning loop in `llm_agent.py` processes the result. If `is_safe=false`, the system prompt instructs the LLM to switch to the urgent path: the next `search_providers` call includes an `emergency_available=true` filter, the booking is marked urgent, and the response includes the safety warning. This branching happens within the existing tool-calling loop — no code change to `llm_agent.py` is needed; the behaviour is controlled entirely through the system prompt and tool outputs.

---

#### Tool 5: `search_providers`

**Purpose:** Searches the Qdrant vector store of EV-capable service providers, filtered by issue type, brand, and proximity.

**Inputs:** subsystem (from triage), symptom_category (from triage), vehicle_brand, owner_location (lat/lng), radius_km, urgency (routine / urgent — controls whether emergency_available filter is applied).

**Internal logic:**
1. Constructs a semantic query from the subsystem + symptom_category (e.g., "Battery BMS warning light abnormal voltage").
2. Generates an embedding via the Vayu MaaS embedding endpoint (same endpoint the template uses for task embeddings).
3. Queries Qdrant with the embedding vector + payload filters: `brand_certifications` must include the owner's brand, location must be within `radius_km`, and if urgency is "urgent", `emergency_available` must be true.
4. Returns top 3–5 ranked matches with provider_id, name, distance, match_score.

**Tech used:** Vayu Vector DB (Qdrant), Vayu MaaS embedding endpoint, `qdrant-client` library. This directly parallels how the template's `search_tasks` works — same client, same search pattern, different collection and filters.

**Template parallel:** Directly replaces `search_tasks`. The Qdrant search pattern is inherited; only the collection name, embedding content, and filter fields change.

---

#### Tool 6: `get_provider_details`

**Purpose:** Retrieves full profile details for a specific provider (called after `search_providers` returns ranked IDs).

**Inputs:** provider_id.

**Internal logic:**
1. Fetches the full Qdrant point by ID from the `ev_providers` collection.
2. Returns the complete metadata payload: name, address, phone, brand_certifications (list), subsystem_specialisations (list), equipment (list), ratings, hours, emergency_available, service_history_summary, pricing_tier.

**Tech used:** Qdrant point retrieval (by ID). Direct parallel to how the template retrieves individual task records.

**Template parallel:** Equivalent to a targeted `list_tasks` with ID filter.

---

#### Tool 7: `estimate_fair_price`

**Purpose:** Generates an independent expected cost range for the diagnosed issue.

**Inputs:** subsystem, symptom_category, severity, vehicle_make, vehicle_model, vehicle_category (two-wheeler / car), region.

**Internal logic:**
1. Queries the `pricing_history` table in PostgreSQL for historical cost data matching the issue type, vehicle category, and region.
2. If historical data exists, computes min/max from the data with confidence notes.
3. If no historical data, falls back to the LLM's training knowledge for a best-effort estimate.
4. Returns: cost_min, cost_max, breakdown (parts_estimate, labour_estimate where available), data_source ("historical data" or "model estimate"), disclaimer.

**Tech used:** Vayu Managed PostgreSQL (query `pricing_history` table), Vayu Model as a Service (LLM fallback and natural-language formatting). Uses the same `postgres_db.py` connection and query patterns from the template.

**Template parallel:** No direct equivalent, but uses the same PostgreSQL infrastructure as the template's trace logging.

---

#### Tool 8: `queue_booking`

**Purpose:** Queues a proposed booking for human approval, halting the agent's execution.

**Inputs:** provider_id, provider_name, issue_summary, triage_json, estimated_cost_min, estimated_cost_max, urgency, owner_notes.

**Internal logic:**
1. Writes a record to the `pending_actions` table in PostgreSQL (the same table the template uses for `queue_task_delete`). The record includes all booking details and status="pending".
2. Returns a confirmation message: "Booking queued for your approval. Please approve or reject."
3. The agent's tool-calling loop in `llm_agent.py` treats this as a terminal action for the current turn — it generates a final response showing the Booking Approval Card and waits.

**Tech used:** Vayu Managed PostgreSQL (`pending_actions` table), same `postgres_db.py` APIs the template uses for `queue_task_delete`.

**Template parallel:** Directly replaces `queue_task_delete`. Same table, same approval pattern, same human-in-the-loop gate — different domain action (booking a provider instead of deleting a task).

---

## 4. Qdrant Collection Schema — What Replaces `tasks`

### Template Collection: `tasks`

```
Collection: tasks
Vector: embedding of task description text
Payload: { title, description, status, priority, created_at }
```

### Revvive Collection: `ev_providers`

```
Collection: ev_providers
Vector: embedding of provider capability profile text
  (e.g., "Certified Ather service centre specialising in battery pack 
   diagnostics, BMS repairs, and motor controller replacements. 
   Equipped with high-voltage safety gear and Ather-specific 
   diagnostic tools. Located in Koramangala, Bengaluru.")

Payload: {
  name: string,
  address: string,
  location: { lat: float, lng: float },
  phone: string,
  brand_certifications: [string],       // ["Ather", "Ola", "TVS"]
  subsystem_specialisations: [string],  // ["Battery/BMS", "Motor", "Controller"]
  equipment: [string],                  // ["HV safety kit", "Ather diagnostics"]
  rating: float,
  review_count: int,
  emergency_available: bool,
  hours: string,
  pricing_tier: string,                 // "budget" / "mid" / "premium"
  service_history_summary: string
}
```

The Qdrant client setup, connection logic, and collection creation flow from `qdrant_tasks.py` are reused. The file is renamed/refactored to `qdrant_providers.py` with the same patterns adapted for the new schema.

---

## 5. PostgreSQL Schema — What's Inherited and What's Added

### Inherited from Template (No Changes)

```sql
-- From db/schema.sql (template)

CREATE TABLE IF NOT EXISTS agent_runs (
    id            TEXT PRIMARY KEY,
    started_at    TIMESTAMPTZ DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    status        TEXT DEFAULT 'running',
    summary       TEXT
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id            SERIAL PRIMARY KEY,
    run_id        TEXT REFERENCES agent_runs(id),
    step_number   INT,
    tool_name     TEXT,
    tool_input    JSONB,
    tool_output   JSONB,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pending_actions (
    id            TEXT PRIMARY KEY,
    run_id        TEXT REFERENCES agent_runs(id),
    action_type   TEXT,
    action_detail JSONB,
    status        TEXT DEFAULT 'pending',
    created_at    TIMESTAMPTZ DEFAULT now(),
    decided_at    TIMESTAMPTZ
);
```

Every Revvive agent run logs to `agent_runs`. Every tool call (`estimate_range`, `triage_issue`, `safety_check`, `search_providers`, etc.) logs to `agent_steps` with full input/output JSON. Booking approvals use `pending_actions` with `action_type='booking'` and `action_detail` containing the full booking payload.

### Added by Revvive

```sql
CREATE TABLE IF NOT EXISTS pricing_history (
    id              SERIAL PRIMARY KEY,
    subsystem       TEXT NOT NULL,
    symptom_category TEXT,
    vehicle_category TEXT,       -- 'two_wheeler' / 'car'
    region          TEXT,
    cost_min        NUMERIC,
    cost_max        NUMERIC,
    sample_size     INT,
    last_updated    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bookings (
    id              TEXT PRIMARY KEY,
    run_id          TEXT REFERENCES agent_runs(id),
    owner_id        TEXT,
    provider_id     TEXT,
    provider_name   TEXT,
    issue_summary   TEXT,
    triage_json     JSONB,
    estimated_cost_min NUMERIC,
    estimated_cost_max NUMERIC,
    urgency         TEXT,
    status          TEXT DEFAULT 'confirmed',
    booked_at       TIMESTAMPTZ DEFAULT now()
);
```

---

## 6. Application Structure — Pages, UI, and How They Connect

### 6.1 Template UI (What's Being Replaced)

The template's `app.py` has three Streamlit tabs:

- **Tasks tab** — direct Qdrant CRUD: add, list, search, mark done, delete tasks.
- **Agent tab** — chat interface where the user talks to the LLM agent, which calls task tools and shows the trace.
- **Approvals tab** — human-in-the-loop interface for approving/rejecting queued task deletions.

### 6.2 Revvive UI (What Replaces It)

Revvive restructures the app into a single-page conversational interface with contextual cards and a secondary approvals/history view. The Streamlit patterns (session state, cached resources, chat elements) are inherited.

#### Page 1: Home / Vehicle Setup (Replaces Tasks Tab)

**Purpose:** Entry point. Captures the owner's vehicle context so all subsequent queries are vehicle-aware.

**UI Elements:**
- Vehicle profile: make, model, year (via `st.selectbox`).
- Current battery percentage (via `st.number_input` or `st.slider`).
- Location: auto-detect or manual entry (via `st.text_input` with geocoding).
- "Start chatting" button → navigates to the Chat page.

**Session state stored:** `vehicle_make`, `vehicle_model`, `battery_percent`, `battery_capacity_kwh`, `owner_location`, `connector_type`.

**Tech:** Streamlit form elements, `st.session_state`. Same `.env` loading and cached resource initialization from the template.

**Connects to:** Chat page. All session state is read by the agent's tools as implicit context.

---

#### Page 2: Chat / Agent Interface (Evolved from Agent Tab)

**Purpose:** The primary interaction surface. The owner types in plain language; the agent classifies intent, calls tools, and renders results as structured cards inline in the chat.

**UI Elements:**
- Scrollable chat history (`st.chat_message` for user and assistant turns).
- Agent responses contain structured output cards rendered via `st.markdown` with HTML/CSS or `st.components.v1.html`.
- Persistent input bar at the bottom (`st.chat_input`).
- Optional trace toggle (inherited from the template's Agent tab) — shows which tools are being called in real time.

**Tech:** Same chat loop from the template's Agent tab. `llm_agent.py` runs the tool-calling loop; `agent_tools.py` dispatches to the new EV tools; `postgres_db.py` logs every step.

**Inline cards rendered within chat responses:**

**Range Verdict Card** — appears after `estimate_range` returns. Shows origin, destination, distance, verdict badge (green/amber/red), confidence band, predicted arrival charge, and consumption breakdown (terrain, traffic, weather, base). If Tight/Not Advisable, a Charger Card appears directly below.

**Charger Card** — appears after `find_chargers_on_route` returns. Shows charger name, location, distance, connector type, compatibility indicator, charge-duration guidance ("Charge 25 min to add 18 km"), and a map pin. Includes suppression note if the owner can reach home without charging.

**Triage Card** — appears after `triage_issue` returns. Shows the owner's original description, classified subsystem, symptom category, severity badge (colour-coded), and plain-language explanation.

**Safety Alert Card** — appears after `safety_check` returns unsafe. Red warning banner, hazard description, safety advisory ("Do not ride, do not charge"), urgency reclassification to Critical. Only rendered when the safety check fires; invisible on the normal path.

**Provider Card** — appears after `search_providers` + `get_provider_details` return. Shows provider name, address, distance, brand compatibility badges, specialisation tags, rating, and a "Why this provider" explanation generated by the LLM.

**Fair Price Card** — appears after `estimate_fair_price` returns. Shows diagnosed issue, expected cost range (₹min – ₹max), parts vs. labour breakdown where available, and a disclaimer.

**Booking Approval Card** — appears after `queue_booking` writes to `pending_actions`. Shows the complete proposed booking (provider, issue, cost estimate, urgency). Two buttons: Approve / Reject. Agent execution halts here. On Approve, the booking is confirmed and a service brief is generated. On Reject, the agent asks "Would you like a different provider?" and loops back to `search_providers`.

**Connects to:** All tools via `llm_agent.py`. On booking approval, generates the Service Brief and optionally navigates to the History page.

---

#### Page 3: Approvals (Evolved from Approvals Tab)

**Purpose:** Dedicated view for managing pending booking approvals, especially useful if the owner navigates away from the chat before approving.

**UI Elements:**
- List of pending bookings from `pending_actions` where `action_type='booking'` and `status='pending'`.
- Each entry shows provider name, issue summary, estimated cost, urgency.
- Approve / Reject buttons per entry.

**Tech:** Same Streamlit + PostgreSQL pattern from the template's Approvals tab. Queries `pending_actions` table, renders with `st.button`, updates status on click.

**Template parallel:** This is the template's Approvals tab with `action_type` changed from `'delete'` to `'booking'`. The code pattern is nearly identical.

**Connects to:** On approval, updates `pending_actions` status, creates a `bookings` record, and generates the service brief.

---

#### Page 4: History / Audit (New)

**Purpose:** Review past interactions, diagnoses, bookings, and full agent traces.

**UI Elements:**
- List of past agent runs from `agent_runs`, sorted by date.
- Each run shows: timestamp, intent type, summary, outcome.
- Expandable detail view: full tool-call trace from `agent_steps` (tool name, input, output, timestamp per step).
- Past bookings from `bookings` table with status.

**Tech:** PostgreSQL queries against `agent_runs`, `agent_steps`, `bookings`. Streamlit rendering with `st.expander` for trace details.

**Template parallel:** The template's Agent tab shows the trace for the current run; this extends it to historical runs.

---

## 7. End-to-End Flows — How Everything Connects

### Flow A: Range Query

```
Home Page (vehicle context set in session state)
  → Chat Page: owner types "Can I reach Whitefield and back?"
  → llm_agent.py: LLM classifies intent as RANGE
  → agent_tools.py: dispatches to estimate_range
      → Google Maps API → route + elevation
      → Traffic API → congestion per segment
      → Weather API → conditions
      → Energy model → segment-by-segment consumption
      → Returns verdict object
  → postgres_db.py: logs tool call to agent_steps
  → Chat renders Range Verdict Card
  → IF verdict is Tight/Not Advisable:
      → LLM autonomously calls find_chargers_on_route
      → agent_tools.py: dispatches to find_chargers_on_route
          → Charger API → nearby chargers
          → Energy model → reachability filter
          → Returns charger recommendations
      → postgres_db.py: logs tool call
      → Chat renders Charger Card below Range Verdict Card
  → agent_runs logged with summary
```

### Flow B: Breakdown (Normal Path)

```
Chat Page: owner types "Motor is making grinding noise"
  → llm_agent.py: LLM classifies intent as BREAKDOWN
  → Step 1: triage_issue
      → LLM structured output → subsystem, symptom, severity JSON
      → Chat renders Triage Card
  → Step 2: safety_check
      → LLM evaluates → is_safe: true
      → No Safety Alert Card rendered
  → Step 3: search_providers
      → qdrant_providers.py: semantic search in ev_providers collection
      → Filters: brand match, radius, subsystem match
      → Returns ranked provider IDs
  → Step 4: get_provider_details
      → Qdrant point retrieval by ID
      → Chat renders Provider Card
  → Step 5: estimate_fair_price
      → PostgreSQL pricing_history query + LLM
      → Chat renders Fair Price Card
  → Step 6: queue_booking
      → postgres_db.py: writes to pending_actions (action_type='booking')
      → Chat renders Booking Approval Card → AGENT HALTS
  → Owner clicks Approve on card (or via Approvals page)
      → pending_actions updated to 'approved'
      → bookings record created
      → Service brief generated from agent_steps trace
      → Chat renders confirmation with service brief
  → All steps logged in agent_steps; run completed in agent_runs
```

### Flow C: Breakdown (Safety Alert Path)

```
Chat Page: owner types "Burning smell and battery looks swollen"
  → Step 1: triage_issue → severity: Critical
      → Chat renders Triage Card (red badge)
  → Step 2: safety_check → is_safe: false, hazard: thermal runaway risk
      → Chat renders Safety Alert Card (red banner, "Do not ride")
  → AGENT BRANCHES: LLM system prompt detects unsafe flag
      → Modifies search_providers call: adds emergency_available=true filter
  → Step 3: search_providers (urgent mode)
      → Qdrant query with emergency filter
      → Chat renders Provider Card (marked URGENT)
  → Step 4: estimate_fair_price (urgent context)
      → Chat renders Fair Price Card
  → Step 5: queue_booking (marked urgent)
      → Chat renders Booking Approval Card (urgent styling) → HALTS
  → Owner approves → urgent service brief includes safety warnings
```

### Flow D: Charger Assist (Proactive Suppression)

```
Chat: "I'm at 12%, can I get home? I'm 5 km away"
  → estimate_range: 12% charge, 5 km, flat terrain
      → Verdict: COMFORTABLE (arrival charge ~6%)
      → Range Verdict Card (green)
      → Suppression: "You can reach home. No charging stop needed."
      → find_chargers_on_route NOT triggered
```

---

## 8. File-by-File Change Map

| File | Template Function | Revvive Change |
|------|------------------|----------------|
| `.env.example` | Qdrant, Postgres, MaaS config | Add: `GOOGLE_MAPS_API_KEY`, `WEATHER_API_KEY`, `CHARGER_API_KEY` |
| `requirements.txt` | qdrant-client, streamlit, openai, psycopg, python-dotenv | Add: `requests`, `googlemaps`, `geopy`, `folium` (or equivalent) |
| `db/schema.sql` | agent_runs, agent_steps, pending_actions | Add: `pricing_history`, `bookings` tables |
| `agent_tools.py` | 5 task tools (list, search, add, update, queue_delete) | Replace with 8 EV tools (estimate_range, find_chargers_on_route, triage_issue, safety_check, search_providers, get_provider_details, estimate_fair_price, queue_booking) |
| `qdrant_tasks.py` → `qdrant_providers.py` | Task collection CRUD + search | Provider collection CRUD + semantic search with EV-specific payload schema |
| `llm_agent.py` | Agent loop with task-management system prompt | System prompt replaced with Revvive EV assistant persona; tool list updated; loop logic unchanged |
| `postgres_db.py` | Table creation, run/step logging, pending action management | Add: `pricing_history` and `bookings` table creation; add query functions for pricing lookups; existing logging APIs unchanged |
| `app.py` | 3 tabs: Tasks, Agent, Approvals | Restructured: Home/Setup, Chat (with inline cards), Approvals (for bookings), History/Audit |
| `Dockerfile` | Python 3.11, install deps, run streamlit | No structural change; picks up new requirements.txt |

---

## 9. Agentic Properties — Mapped to Template Mechanisms

| Agentic Property | How the Template Enables It | How Revvive Demonstrates It |
|-----------------|---------------------------|---------------------------|
| Autonomous path selection | `llm_agent.py` tool-calling loop lets the LLM choose which tool to call | LLM decides range vs. breakdown path based on user input — no toggle |
| Multi-step tool orchestration | Loop iterates until LLM signals completion | Breakdown chains 6+ sequential tool calls, each output feeding the next |
| Conditional branching | LLM can choose different tools based on prior tool outputs | Safety check result changes the search_providers filter and response tone |
| Human-in-the-loop gate | `pending_actions` table + Approvals tab | queue_booking halts execution; owner approval resumes it |
| Full auditability | `agent_runs` + `agent_steps` tables | Every EV tool call logged with input/output; entire decision chain reconstructable |

---

## 10. Roadmap Beyond the Hackathon

**Layer 1 — Today (Hackathon MVP):** The unified range-confidence and triage-and-routing agent, built on the Vayu Do-It template. Battery state is user-reported. Provider data is seeded in Qdrant. Triage and safety are pure LLM reasoning. All infrastructure (Qdrant, Postgres, MaaS, Streamlit, Docker) is production-ready via the template.

**Layer 2 — Trust (Near-term):** India-specific battery health certificate. Accumulated charge-discharge and degradation data enables verified battery condition reports, unlocking the broken second-hand EV market where buyers currently cannot assess battery health.

**Layer 3 — Predictive (Medium-term):** OBD-II and telematics-connected predictive diagnostics. Live battery telemetry replaces manual entry. Early degradation detection warns owners before breakdowns occur, shifting Revvive from reactive to predictive.

The connective tissue across all three layers is the **failure-mode and energy-consumption dataset for Indian EVs** — built from every interaction logged in `agent_runs` and `agent_steps`. This dataset is the compounding competitive moat that no player currently owns.
