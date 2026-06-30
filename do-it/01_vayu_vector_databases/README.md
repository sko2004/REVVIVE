# Step 1 — Vayu Vector DB (Qdrant)

**Do-It** › **Vayu Vector DB** · `01_vayu_vector_databases/`

| | |
|---|---|
| **Previous** | [← Step 0 — Vayu AI Studio Workspace](../00_vayu_workspace/) |
| **Next** | [Step 2 — Vayu Managed PostgreSQL →](../02_vayu_postgres/) |

Set up the **Vayu Vector DB (Qdrant)** to store task payloads for the Do-It agent.

---

## Open Vector DB

Go to [Vayu Vector DB](https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list).

---

## Quick Start

1. **Provision Vayu Vector DB (Qdrant):** In AI Studio, click **Create Vector Database** and select the **Qdrant** engine under **Vector Type** (see the [Creating Qdrant Vector DB guide](https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant/#creating-qdrant)).
2. **Wait for Ready:** Submit the deployment and wait until the status shows **Ready**.
3. **Collect access details:** Note your **`QDRANT_URL`** and **`QDRANT_API_KEY`** from the console.
4. **Set environment variables:** Copy `.env.example` to `.env` at the **do-it** repo root and fill in your values (used by `04_starter_kit/` and `05_build_app/`):

   ```bash
   cd do-it
   cp .env.example .env
   # Edit .env — set QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
   ```

5. **Local development (optional):** For local testing, use on-disk Qdrant with the `QDRANT_PATH` variable instead of the hosted service.

---

## Resources

| Resource | URL |
|----------|-----|
| Provision Vayu Vector DB | https://ipcloud.tatacommunications.com/aistudio/#/experiment/vectordatabase-list |
| Docs (Milvus) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/milvus |
| Docs (Qdrant) | https://ipcloud.tatacommunications.com/docs/docs/user-docs/vayu-ai-studio/vector-db/qdrant |

---

## Navigation

| | |
|---|---|
| **Previous** | [← Step 0 — Vayu AI Studio Workspace](../00_vayu_workspace/) |
| **Next** | [Step 2 — Vayu Managed PostgreSQL →](../02_vayu_postgres/) |
| **Overview** | [Do-It overview](../README.md) |
