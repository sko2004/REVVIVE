# Step 2 — Vayu Managed PostgreSQL

**Do-It** › **Vayu Managed PostgreSQL** · `02_vayu_postgres/`

| | |
|---|---|
| **Previous** | [← Step 1 — Vayu Vector DB](../01_vayu_vector_databases/) |
| **Next** | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |

Set up a **Vayu Managed PostgreSQL** database to store agent traces, tool runs, and manage human-in-the-loop (HITL) approval events.

---

## Open PostgreSQL

Go to [Vayu PostgreSQL](https://ipcloud.tatacommunications.com/cloud/console/vks/#/ms/list/postgres).

Click **Create a New PostgreSQL Instance** to start the deployment wizard.

---

## Quick Start

1. **Provision PostgreSQL in Vayu**

   - Log in to the [Vayu PostgreSQL console](https://ipcloud.tatacommunications.com/cloud/console/vks/#/ms/list/postgres).
   - Click **Create a New PostgreSQL Instance** and follow the wizard prompts.
   - **Wait for Ready:** Submit the deployment and wait until the status shows **Ready**.
   - Save the connection details (host, port, database, username, password) provided by the console.

2. **Configure database connection**

   Set the `DATABASE_URL` in your `do-it/.env` file **(mandatory; the repo does not provide a local DB)**:

   ```bash
   cd do-it
   cp .env.example .env
   # Edit .env to contain:
   # DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
   ```

   - Add `?sslmode=require` at the end of the connection string if the provider requires SSL/TLS (e.g. `postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`).

   **URL-encode special characters in your password (and username, if needed).**

   `postgres_db.py` reads `DATABASE_URL` as a single connection string, validates it with Python's `urlparse`, and passes it directly to `psycopg.connect()`. Characters such as `@`, `:`, `/`, `%`, `#`, `?`, `&`, `+`, or spaces in the password are interpreted as URL syntax unless they are percent-encoded — which often causes *password authentication failed* errors even when the password from the console is correct.

   | Character in password | Encoded |
   |-----------------------|---------|
   | `@` | `%40` |
   | `:` | `%3A` |
   | `/` | `%2F` |
   | `#` | `%23` |
   | `%` | `%25` |
   | `?` | `%3F` |
   | `&` | `%26` |
   | `+` | `%2B` |
   | space | `%20` |

   **Example:** if the console gives password `MyP@ss:word#1`, use:

   ```text
   DATABASE_URL=postgresql://myuser:MyP%40ss%3Aword%231@db-host.example.com:5432/mydb
   ```

   **Encode and build the full URL with Python** (run in your workspace terminal — replace the placeholder values with your Vayu console credentials):

   ```bash
   python3 -c "from urllib.parse import quote; user='myuser'; password='MyP@ss:word#1'; host='db-host.example.com'; port=5432; dbname='mydb'; print(f'postgresql://{quote(user, safe=\"\")}:{quote(password, safe=\"\")}@{host}:{port}/{dbname}')"
   ```

   Example output:

   ```text
   postgresql://myuser:MyP%40ss%3Aword%231@db-host.example.com:5432/mydb
   ```

   Copy the printed line into `do-it/.env` as `DATABASE_URL=...`. Do not wrap the value in extra quotes unless your shell or deploy UI requires it.

3. **Database schema initialization**

   On application start, the code auto-creates core tables via `postgres_db.ensure_tables()`:

   - `agent_runs`
   - `agent_steps`
   - `pending_actions` (for HITL)

4. **Manual schema setup (optional)**

   If you wish to initialize or reset the schema manually:

   ```bash
   psql "$DATABASE_URL" -f 04_starter_kit/db/schema.sql
   ```

5. **Continue**

   Once the database is ready and `.env` is configured, proceed to [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/).

**Troubleshooting tip:** Use the *actual* database host/port from the Vayu PostgreSQL console. Do not use `localhost` unless you are running a database locally, which is not typical for managed services.

---

## Resources

| Resource | Link |
|----------|------|
| Provision PostgreSQL | [Vayu PostgreSQL console](https://ipcloud.tatacommunications.com/cloud/console/vks/#/ms/list/postgres) |

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 1 — Vayu Vector DB](../01_vayu_vector_databases/) |
| **Next** | [Step 3 — Vayu Model as a Service →](../03_vayu_model_as_a_service/) |
| **Overview** | [Do-It overview](../README.md) |
